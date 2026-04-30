import streamlit as st
from supabase import create_client, Client
import datetime
import pandas as pd

# --- 1. CONFIGURATIE & THEMA ---
st.set_page_config(page_title="DGW Wanica Portaal", page_icon="📝", layout="wide")

st.markdown("""
    <style>
    .tijd-knop {
        display: inline-block;
        padding: 10px;
        margin: 5px;
        border-radius: 5px;
        text-align: center;
        font-weight: bold;
        width: 80px;
    }
    .vrij { background-color: #e8f5e9; border: 2px solid #2e7d32; color: #2e7d32; }
    .bezet { background-color: #ffebee; border: 2px solid #c62828; color: #c62828; text-decoration: line-through; }
    .selected { background-color: #2e7d32; color: white; border: 2px solid #1b5e20; }
    </style>
    """, unsafe_allow_html=True)

# --- 2. DATABASE VERBINDING ---
try:
    URL = st.secrets["SUPABASE_URL"]
    KEY = st.secrets["SUPABASE_KEY"]
    supabase: Client = create_client(URL, KEY)
except Exception:
    st.error("Systeemfout: Databaseverbinding mislukt!")
    st.stop()

# --- 3. LOGICA VOOR BESCHIKBAARHEID ---
def get_tijd_status(datum):
    # Genereer alle blokken tussen 07:30 en 14:00
    start = datetime.datetime.strptime("07:30", "%H:%M")
    eind = datetime.datetime.strptime("14:00", "%H:%M")
    alle_tijden = []
    while start <= eind:
        alle_tijden.append(start.strftime("%H:%M"))
        start += datetime.timedelta(minutes=15)
    
    # Haal bezette tijden op uit Supabase
    res = supabase.table("aanvragen").select("afspraak_tijd").eq("afspraak_datum", str(datum)).execute()
    bezette_tijden = [r['afspraak_tijd'] for r in res.data] if res.data else []
    
    return alle_tijden, bezette_tijden

# --- 4. INTERFACE ---
st.title("📝 Dienst Grondzaken Wanica")

menu = st.sidebar.radio("Navigatie", ["Cliënt Registratie", "Medewerker Portaal"])

if menu == "Cliënt Registratie":
    st.subheader("Nieuwe Afspraak Inplannen")
    
    with st.expander("Persoonlijke Gegevens", expanded=True):
        col1, col2 = st.columns(2)
        vnaam = col1.text_input("Voornaam *")
        anaam = col1.text_input("Achternaam *")
        id_nr = col1.text_input("ID-Nummer *")
        tel = col2.text_input("Telefoonnummer *")
        email = col2.text_input("E-mailadres")
        lad_nr = col2.text_input("LAD Nummer")
        bericht = st.text_area("Omschrijving klacht/verzoek *")

    st.write("---")
    st.subheader("📅 Kies Datum & Tijd")
    datum = st.date_input("Selecteer een datum", min_value=datetime.date.today())

    # Controle op Maandag (0) of Woensdag (2)
    if datum.weekday() not in [0, 2]:
        st.error("Afspraken zijn enkel mogelijk op Maandag en Woensdag.")
    else:
        alle_tijden, bezette_tijden = get_tijd_status(datum)
        
        st.write("**Beschikbaarheidsoverzicht:**")
        st.caption("🟢 Groen = Vrij | 🔴 Rood = Bezet")
        
        # Visuele weergave van tijden
        cols = st.columns(6)
        gekozen_tijd = None
        
        for i, t in enumerate(alle_tijden):
            is_bezet = t in bezette_tijden
            kleur_class = "bezet" if is_bezet else "vrij"
            label = "BEZET" if is_bezet else "VRIJ"
            
            with cols[i % 6]:
                st.markdown(f'<div class="tijd-knop {kleur_class}">{t}<br><small>{label}</small></div>', unsafe_allow_html=True)

        st.write("")
        # Selectie voor de daadwerkelijke boeking
        vrije_opties = [t for t in alle_tijden if t not in bezette_tijden]
        if vrije_opties:
            geselecteerde_tijd = st.selectbox("Bevestig uw tijdstip *", vrije_opties)
            
            if st.button("Afspraak Definitief Bevestigen"):
                if vnaam and anaam and id_nr and bericht:
                    data = {
                        "voornaam": vnaam, "achternaam": anaam, "id_nummer": id_nr,
                        "telefoon": tel, "email": email, "lad_nummer": lad_nr,
                        "bericht": bericht, "afspraak_datum": str(datum),
                        "afspraak_tijd": geselecteerde_tijd, "status": "In behandeling"
                    }
                    supabase.table("aanvragen").insert(data).execute()
                    st.success(f"✅ Uw afspraak voor {datum} om {geselecteerde_tijd}u is vastgelegd.")
                else:
                    st.warning("Vul a.u.b. alle verplichte velden in.")
        else:
            st.error("Geen vrije plekken meer op deze dag.")

elif menu == "Medewerker Portaal":
    st.subheader("Dossierbeheer")
    # Mogelijkheid voor baliemedewerkers om DC nummers te corrigeren
    res = supabase.table("aanvragen").select("*").execute()
    if res.data:
        df = pd.DataFrame(res.data)
        st.dataframe(df)
        
        with st.expander("Wijzig DC-nummer of Status"):
            sel_id = st.selectbox("Dossier ID", df['id'].tolist())
            nieuw_dc = st.text_input("DC Nummer")
            nieuwe_status = st.selectbox("Status", ["In behandeling", "Bevestigd", "Afgehandeld", "Afgewezen"])
            if st.button("Update Dossier"):
                supabase.table("aanvragen").update({"dc_nummer": nieuw_dc, "status": nieuwe_status}).eq("id", sel_id).execute()
                st.success("Bijgewerkt!")
                st.rerun()

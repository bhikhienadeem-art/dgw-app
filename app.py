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
        width: 85px;
    }
    .vrij { background-color: #e8f5e9; border: 2px solid #2e7d32; color: #2e7d32; }
    .bezet { background-color: #ffebee; border: 2px solid #c62828; color: #c62828; text-decoration: line-through; }
    .stButton>button { background-color: #2e7d32; color: white; border-radius: 5px; width: 100%; }
    </style>
    """, unsafe_allow_html=True)

# --- 2. DATABASE VERBINDING ---
try:
    URL = st.secrets["SUPABASE_URL"]
    KEY = st.secrets["SUPABASE_KEY"]
    supabase: Client = create_client(URL, KEY)
except Exception:
    st.error("Systeemfout: Controleer uw Database Secrets!")
    st.stop()

# --- 3. LOGICA VOOR BESCHIKBAARHEID ---
def get_tijd_status(datum):
    # Genereer tijden: 07:30 tot 14:00 (15 min interval)
    start = datetime.datetime.strptime("07:30", "%H:%M")
    eind = datetime.datetime.strptime("14:00", "%H:%M")
    alle_tijden = []
    while start <= eind:
        alle_tijden.append(start.strftime("%H:%M"))
        start += datetime.timedelta(minutes=15)
    
    # CORRECTIE: Tabelnaam moet 'aanvragen' zijn (was 'aanvagen')
    res = supabase.table("aanvragen").select("afspraak_tijd").eq("afspraak_datum", str(datum)).execute()
    bezette_tijden = [r['afspraak_tijd'] for r in res.data] if res.data else []
    return alle_tijden, bezette_tijden

# --- 4. INTERFACE ---
st.title("📝 Dienst Grondzaken Wanica (DGW)")

menu = st.sidebar.radio("Navigatie", ["Cliënt Registratie", "Medewerker Portaal"])

if menu == "Cliënt Registratie":
    st.subheader("Nieuwe Aanvraag")
    
    col1, col2 = st.columns(2)
    with col1:
        vnaam = st.text_input("Voornaam *")
        anaam = st.text_input("Achternaam *")
        id_nr = st.text_input("ID-Nummer *")
        woonadres = st.text_input("Woonadres *") # Woonadres
    with col2:
        tel = st.text_input("Telefoonnummer *")
        email = st.text_input("E-mailadres")
        lad_nr = st.text_input("LAD Nummer")
    
    bericht = st.text_area("Omschrijving klacht/verzoek *")

    st.write("---")
    st.subheader("📁 Documenten Uploaden")
    st.info("Upload uw ID-kaart, grondpapieren of andere bewijsstukken.")
    uploaded_files = st.file_uploader("Documenten (PDF, JPG, PNG)", accept_multiple_files=True) # Upload

    st.write("---")
    st.subheader("📅 Plan uw afspraak")
    datum = st.date_input("Kies een datum", min_value=datetime.date.today())

    # Alleen Maandag (0) en Woensdag (2)
    if datum.weekday() not in [0, 2]:
        st.error("U kunt alleen een afspraak maken op Maandag of Woensdag.")
    else:
        alle_tijden, bezette_tijden = get_tijd_status(datum)
        
        st.write("**Directe beschikbaarheid:** (Groen = Vrij, Rood = Bezet)")
        cols = st.columns(6)
        for i, t in enumerate(alle_tijden):
            is_bezet = t in bezette_tijden
            kleur_class = "bezet" if is_bezet else "vrij"
            label = "BEZET" if is_bezet else "VRIJ"
            with cols[i % 6]:
                st.markdown(f'<div class="tijd-knop {kleur_class}">{t}<br><small>{label}</small></div>', unsafe_allow_html=True)

        st.write("")
        vrije_opties = [t for t in alle_tijden if t not in bezette_tijden]
        
        if vrije_opties:
            geselecteerde_tijd = st.selectbox("Selecteer uw tijdstip *", vrije_opties)
            
            if st.button("Aanvraag indienen"): # Knoptekst
                if vnaam and anaam and id_nr and woonadres and bericht:
                    data = {
                        "voornaam": vnaam, "achternaam": anaam, "id_nummer": id_nr,
                        "woonadres": woonadres, "telefoon": tel, "email": email, 
                        "lad_nummer": lad_nr, "bericht": bericht, "afspraak_datum": str(datum),
                        "afspraak_tijd": geselecteerde_tijd, "status": "In behandeling"
                    }
                    supabase.table("aanvragen").insert(data).execute()
                    st.success(f"✅ Uw aanvraag voor {datum} om {geselecteerde_tijd}u is succesvol ingediend!")
                else:
                    st.warning("Vul alle verplichte velden (*) in.")
        else:
            st.error("Deze dag is helaas volgeboekt.")

elif menu == "Medewerker Portaal":
    st.subheader("Overzicht & Dossierbeheer")
    res = supabase.table("aanvragen").select("*").execute()
    if res.data:
        df = pd.DataFrame(res.data)
        st.dataframe(df) # Mogelijkheid tot correctie van DC-nummers

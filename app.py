import streamlit as st
from supabase import create_client, Client
import datetime
import pandas as pd

# --- 1. CONFIGURATIE ---
st.set_page_config(page_title="DGW Wanica Portaal", page_icon="📝", layout="wide")

# Groen/wit thema behouden
st.markdown("""
    <style>
    .stButton>button { background-color: #2e7d32; color: white; border-radius: 5px; }
    .highlight-box { padding: 15px; border-radius: 10px; border: 2px solid #2e7d32; background-color: #f1f8e9; }
    </style>
    """, unsafe_allow_html=True)

# --- 2. DATABASE ---
URL = st.secrets["SUPABASE_URL"]
KEY = st.secrets["SUPABASE_KEY"]
supabase: Client = create_client(URL, KEY)

# --- 3. LOGICA VOOR TIJDEN ---
def get_tijdsblokken(datum_str):
    start = datetime.datetime.strptime("07:30", "%H:%M")
    eind = datetime.datetime.strptime("14:00", "%H:%M")
    tijden = []
    while start <= eind:
        tijden.append(start.strftime("%H:%M"))
        start += datetime.timedelta(minutes=15)
    
    # Check bezetting in database
    res = supabase.table("aanvragen").select("afspraak_tijd").eq("afspraak_datum", datum_str).execute()
    bezette_tijden = [r['afspraak_tijd'] for r in res.data] if res.data else []
    return [t for t in tijden if t not in bezette_tijden]

# --- 4. INTERFACE ---
st.title("📝 Dienst Grondzaken Wanica (DGW)")

menu = st.sidebar.radio("Navigatie", ["Cliënt Registratie", "Medewerker Portaal"])

if menu == "Cliënt Registratie":
    st.subheader("Plan uw afspraak")
    st.info("Afspraken zijn enkel mogelijk op maandag en woensdag (07:30u - 14:00u).")

    with st.form("simpel_form"):
        col1, col2 = st.columns(2)
        with col1:
            vnaam = st.text_input("Voornaam *")
            anaam = st.text_input("Achternaam *")
            id_nr = st.text_input("ID-Nummer *")
        with col2:
            tel = st.text_input("Telefoonnummer *")
            lad_nr = st.text_input("LAD Nummer")
            email = st.text_input("E-mailadres")

        bericht = st.text_area("Omschrijving klacht/verzoek *")
        
        st.write("---")
        # DE SIMPELE OPLOSSING: Geen automatische dag-check, maar een bewuste keuze
        st.markdown("**Stap 1: Kies uw gewenste dag**")
        gekozen_datum = st.date_input("Selecteer een datum (Zorg dat dit een Maandag of Woensdag is)")
        
        # We laten de gebruiker de tijd pas kiezen NA de datum selectie
        beschikbare_tijden = get_tijdsblokken(str(gekozen_datum))
        gekozen_tijd = st.selectbox("Stap 2: Kies een beschikbaar tijdstip", beschikbare_tijden)
        
        submit = st.form_submit_button("Afspraak Bevestigen")

    if submit:
        # Handmatige controle bij indiening (als extra veiligheid)
        # 0=Maandag, 2=Woensdag in de standaard Python telling
        if gekozen_datum.weekday() not in [0, 2]:
            st.error("U heeft een dag gekozen die geen Maandag of Woensdag is. Pas de datum aan.")
        elif vnaam and anaam and id_nr and bericht:
            data = {
                "voornaam": vnaam, "achternaam": anaam, "id_nummer": id_nr,
                "telefoon": tel, "lad_nummer": lad_nr, "email": email,
                "bericht": bericht, "afspraak_datum": str(gekozen_datum), 
                "afspraak_tijd": gekozen_tijd, "status": "In behandeling"
            }
            supabase.table("aanvragen").insert(data).execute()
            st.success(f"✅ Afspraak succesvol gepland op {gekozen_datum} om {gekozen_tijd}u.")
        else:
            st.warning("Vul a.u.b. alle verplichte velden in.")

elif menu == "Medewerker Portaal":
    st.subheader("Beheer Dossiers")
    # Hier kunnen baliemedewerkers DC nummers invoeren en corrigeren
    res = supabase.table("aanvragen").select("*").execute()
    if res.data:
        df = pd.DataFrame(res.data)
        st.write("Overzicht aanvragen:")
        st.dataframe(df)
        
        with st.expander("Wijzig DC-nummer of Status"):
            sel_id = st.selectbox("Selecteer Dossier ID", df['id'].tolist())
            nieuw_dc = st.text_input("Voer (nieuw) DC-nummer in")
            nieuwe_status = st.selectbox("Status", ["In behandeling", "Bevestigd", "Afgehandeld", "Afgewezen"])
            if st.button("Bijwerken"):
                supabase.table("aanvragen").update({"dc_nummer": nieuw_dc, "status": nieuwe_status}).eq("id", sel_id).execute()
                st.success("Dossier succesvol bijgewerkt.")
                st.rerun()

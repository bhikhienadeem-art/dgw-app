import streamlit as st
from supabase import create_client, Client
import datetime
import pandas as pd

# --- 1. CONFIGURATIE & THEMA ---
st.set_page_config(page_title="DGW Wanica Portaal", page_icon="📝", layout="wide")

st.markdown("""
    <style>
    .stButton>button { background-color: #2e7d32; color: white; border-radius: 5px; width: 100%; }
    .stTextInput>div>div>input { border-color: #2e7d32; }
    .main { background-color: #ffffff; }
    .highlight-box { 
        padding: 15px; border-radius: 10px; border: 2px solid #2e7d32; 
        background-color: #f1f8e9; margin-bottom: 20px; 
    }
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

# --- 3. HELPER FUNCTIES ---
def get_beschikbare_tijden(datum):
    # Tijden van 07:30 tot 14:00 met 15 min interval
    start = datetime.datetime.strptime("07:30", "%H:%M")
    eind = datetime.datetime.strptime("14:00", "%H:%M")
    tijden = []
    while start <= eind:
        tijden.append(start.strftime("%H:%M"))
        start += datetime.timedelta(minutes=15)
    
    # Controleer bezette tijden in de database
    res = supabase.table("aanvragen").select("afspraak_tijd").eq("afspraak_datum", str(datum)).execute()
    bezette_tijden = [r['afspraak_tijd'] for r in res.data] if res.data else []
    
    # Geef alleen de tijden terug die nog niet bezet zijn
    return [t for t in tijden if t not in bezette_tijden]

# --- 4. INTERFACE & NAVIGATIE ---
st.sidebar.title("DGW Wanica Menu")
keuze = st.sidebar.radio("Navigatie:", ["Cliënt Registratie", "Medewerker Portaal"])

if keuze == "Cliënt Registratie":
    st.title("📝 Registratie Dienst Grondzaken Wanica")
    st.info("Afspraken: Maandag & Woensdag | 07:30u - 14:00u")

    with st.container():
        col1, col2 = st.columns(2)
        with col1:
            vnaam = st.text_input("Voornaam *")
            anaam = st.text_input("Achternaam *")
            id_nr = st.text_input("ID-Nummer *")
        with col2:
            tel = st.text_input("Telefoonnummer *")
            email = st.text_input("E-mailadres")
            lad_nr = st.text_input("LAD Nummer") #

        bericht = st.text_area("Omschrijving klacht/verzoek *")
        
        st.write("---")
        st.subheader("📅 Plan uw afspraak")
        
        # Gebruiker kiest eerst de datum
        datum = st.date_input("Kies een datum", min_value=datetime.date.today())
        
        # Controleer de dag (0=Maandag, 2=Woensdag)
        if datum.weekday() not in [0, 2]:
            st.error("U kunt alleen een afspraak maken op Maandag of Woensdag.")
        else:
            # Tijden worden hier direct geladen en getoond voor de bevestiging
            opties = get_beschikbare_tijden(datum)
            
            if opties:
                tijd = st.selectbox("Beschikbare tijden (direct zichtbaar) *", opties)
                
                if st.button("Afspraak Bevestigen"):
                    if vnaam and anaam and id_nr and bericht:
                        data = {
                            "voornaam": vnaam, "achternaam": anaam, "id_nummer": id_nr,
                            "telefoon": tel, "email": email, "lad_nummer": lad_nr,
                            "bericht": bericht, "afspraak_datum": str(datum),
                            "afspraak_tijd": tijd, "status": "In behandeling"
                        }
                        supabase.table("aanvragen").insert(data).execute()
                        st.success(f"✅ Afspraak bevestigd op {datum} om {tijd}u.")
                    else:
                        st.warning("Vul a.u.b. alle verplichte velden (*) in.")
            else:
                st.error("Helaas, deze dag is volledig volgeboekt.")

elif keuze == "Medewerker Portaal":
    st.subheader("Beheer Dossiers")
    # Baliemedewerkers kunnen hier DC-nummers invoeren en wijzigen
    res = supabase.table("aanvragen").select("*").execute()
    if res.data:
        df = pd.DataFrame(res.data)
        st.dataframe(df)
        
        with st.expander("📝 DC Nummer of Status corrigeren"):
            sel_id = st.selectbox("Selecteer Dossier ID", df['id'].tolist())
            row = df[df['id'] == sel_id].iloc[0]
            
            # Mogelijkheid om fouten te corrigeren
            nieuw_dc = st.text_input("DC Nummer", value=str(row.get('dc_nummer', '')))
            nieuwe_status = st.selectbox("Status", ["In behandeling", "Bevestigd", "Afgehandeld", "Afgewezen"])
            
            if st.button("Wijziging Opslaan"):
                supabase.table("aanvragen").update({"dc_nummer": nieuw_dc, "status": nieuwe_status}).eq("id", sel_id).execute()
                st.success("Dossier bijgewerkt!")
                st.rerun()

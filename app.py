import streamlit as st
from supabase import create_client, Client
import datetime
import pandas as pd

# --- 1. CONFIGURATIE & THEMA ---
st.set_page_config(page_title="DGW Wanica Portaal", page_icon="📝", layout="wide")

st.markdown("""
    <style>
    .stButton>button { background-color: #2e7d32 !important; color: white !important; }
    h1, h2, h3 { color: #1b5e20; }
    </style>
    """, unsafe_allow_html=True)

# --- 2. DATABASE VERBINDING ---
try:
    URL = st.secrets["SUPABASE_URL"]
    KEY = st.secrets["SUPABASE_KEY"]
    supabase: Client = create_client(URL, KEY)
except:
    st.error("Systeemfout: Controleer uw Streamlit Secrets!")
    st.stop()

# --- 3. HELPER FUNCTIES ---
def get_beschikbare_tijden(datum):
    start = datetime.datetime.strptime("07:00", "%H:%M")
    eind = datetime.datetime.strptime("15:00", "%H:%M")
    tijden = []
    while start <= eind:
        tijden.append(start.strftime("%H:%M"))
        start += datetime.timedelta(minutes=15)
    
    res = supabase.table("aanvragen").select("afspraak_tijd").eq("afspraak_datum", str(datum)).execute()
    bezette_tijden = [r['afspraak_tijd'] for r in res.data] if res.data else []
    return tijden, bezette_tijden

# --- 4. NAVIGATIE ---
if "logged_in" not in st.session_state:
    st.session_state["logged_in"] = False

st.sidebar.title("DGW Menu")
keuze = st.sidebar.radio("Ga naar:", ["Cliënt Registratie", "Medewerker Portaal"])

# --- 5. CLIËNT REGISTRATIE ---
if keuze == "Cliënt Registratie":
    st.title("📝 Dienst Grondzaken Wanica - Registratie")
    with st.form("registratie"):
        col1, col2 = st.columns(2)
        with col1:
            vnaam = st.text_input("Voornaam *")
            id_nr = st.text_input("ID-Nummer *")
        with col2:
            anaam = st.text_input("Achternaam *")
            email = st.text_input("E-mail *")
        
        datum = st.date_input("Afspraakdatum (Ma/Wo)", min_value=datetime.date.today())
        alle_tijden, bezet = get_beschikbare_tijden(datum)
        tijd = st.selectbox("Tijdslot (15 min)", alle_tijden)
        
        if tijd in bezet:
            st.error(f"🔴 {tijd} is al bezet.")
        else:
            st.success(f"🟢 {tijd} is beschikbaar.")

        uploaded_file = st.file_uploader("Upload Documenten", type=['pdf', 'jpg', 'png'])
        submit = st.form_submit_button("Aanvraag Verzenden")

    if submit and vnaam:
        if datum.weekday() in [0, 2]: # Maandag=0, Woensdag=2
            doc_url = ""
            if uploaded_file:
                path = f"docs/{vnaam}_{datetime.datetime.now().timestamp()}.pdf"
                supabase.storage.from_("documenten").upload(path, uploaded_file.getvalue())
                doc_url = supabase.storage.from_("documenten").get_public_url(path)

            data = {"voornaam": vnaam, "achternaam": anaam, "email": email, "afspraak_datum": str(datum), "afspraak_tijd": tijd, "status": "In behandeling", "document_url": doc_url}
            supabase.table("aanvragen").insert(data).execute()
            st.success("Aanvraag succesvol verzonden!")
        else:
            st.error("Afspraken kunnen alleen op maandag of woensdag gemaakt worden.")

# --- 6. MEDEWERKER PORTAAL ---
elif keuze == "Medewerker Portaal":
    if not st.session_state["logged_in"]:
        st.title("🔐 Login Medewerker")
        u = st.text_input("Gebruikersnaam").strip()
        p = st.text_input("Wachtwoord", type="password").strip()
        
        if st.button("Inloggen"):
            # Hardcoded fix voor image_ff243f.png
            if u == "ICT Wanica" and p == "l3lyd@rp":
                st.session_state["logged_in"] = True
                st.rerun()
            else:
                st.error("Inloggen mislukt. Controleer uw gegevens.")
    else:
        st.sidebar.button("Uitloggen", on_click=lambda: st.session_state.update({"logged_in": False}))
        tabs = st.tabs(["📋 Beheer & Verwijderen", "📅 Kalender Overzicht"])
        
        with tabs[0]: # BEHEER & VERWIJDEREN
            res = supabase.table("aanvragen").select("*").execute()
            if res.data:
                df = pd.DataFrame(res.data)
                st.subheader("Dossiers Beheren")
                sel_id = st.selectbox("Selecteer Dossier ID", df['id'].tolist())
                
                col_edit, col_del = st.columns(2)
                with col_edit:
                    new_status = st.selectbox("Wijzig Status", ["Bevestigd", "Geannuleerd", "In behandeling"])
                    if st.button("Status Bijwerken"):
                        supabase.table("aanvragen").update({"status": new_status}).eq("id", sel_id).execute()
                        st.success("Status succesvol bijgewerkt!")
                        st.rerun()
                
                with col_del:
                    st.write("### Verwijderen")
                    if st.button("❌ Dossier Definitief Wissen"):
                        supabase.table("aanvragen").delete().eq("id", sel_id).execute()
                        st.warning(f"Dossier {sel_id} is verwijderd.")
                        st.rerun()
                st.dataframe(df)

        with tabs[1]: # KALENDER
            st.subheader("📅 Geplande Afspraken")
            res_cal = supabase.table("aanvragen").select("voornaam, achternaam, afspraak_datum, afspraak_tijd, status").execute()
            if res_cal.data:
                df_cal = pd.DataFrame(res_cal.data).sort_values(by=['afspraak_datum', 'afspraak_tijd'])
                st.table(df_cal)
            else:
                st.info("Geen afspraken gevonden.")

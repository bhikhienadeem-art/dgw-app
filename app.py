import streamlit as st
from supabase import create_client, Client
import smtplib
from email.mime.text import MIMEText
from email.mime.multipart import MIMEMultipart
import datetime
import pandas as pd

# --- 1. CONFIGURATIE & STYLING ---
st.set_page_config(page_title="DGW Wanica Portaal", page_icon="📝", layout="wide")

st.markdown("""
    <style>
    .main { background-color: #ffffff; }
    .stButton>button { background-color: #2e7d32 !important; color: white !important; border-radius: 5px; }
    h1, h2, h3 { color: #1b5e20; }
    .stAlert { border-radius: 10px; }
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
    # Genereer tijden van 07:00 tot 15:00 met 15 min interval
    start = datetime.datetime.strptime("07:00", "%H:%M")
    eind = datetime.datetime.strptime("15:00", "%H:%M")
    tijden = []
    while start <= eind:
        tijden.append(start.strftime("%H:%M"))
        start += datetime.timedelta(minutes=15)
    
    # Check bezette tijden in database
    res = supabase.table("aanvragen").select("afspraak_tijd").eq("afspraak_datum", str(datum)).execute()
    bezette_tijden = [r['afspraak_tijd'] for r in res.data] if res.data else []
    return tijden, bezette_tijden

# --- 4. NAVIGATIE ---
if "logged_in" not in st.session_state:
    st.session_state["logged_in"] = False
    st.session_state["user_rol"] = None

st.sidebar.title("DGW Menu")
keuze = st.sidebar.radio("Ga naar:", ["Cliënt Registratie", "Medewerker Portaal"])

# --- 5. CLIËNT REGISTRATIE (Met Document Upload & 15min Check) ---
if keuze == "Cliënt Registratie":
    st.title("📝 Registratie Dienst Grondzaken Wanica")
    with st.form("registratie_form", clear_on_submit=True):
        col1, col2 = st.columns(2)
        with col1:
            vnaam = st.text_input("Voornaam *")
            id_nr = st.text_input("ID-Nummer *")
            tel = st.text_input("Telefoon *")
        with col2:
            anaam = st.text_input("Achternaam *")
            lad_nr = st.text_input("LAD Nummer *")
            email = st.text_input("E-mail *")
        
        datum = st.date_input("Kies datum (Ma/Wo)", min_value=datetime.date.today())
        
        # Tijdsloten met statusindicator
        alle_tijden, bezet = get_beschikbare_tijden(datum)
        tijd = st.selectbox("Kies tijdstip (15 min intervallen)", alle_tijden)
        
        if tijd in bezet:
            st.error(f"🔴 {tijd} is al bezet op deze dag.")
        else:
            st.success(f"🟢 {tijd} is beschikbaar op {datum}.")

        uploaded_file = st.file_uploader("Upload documenten (PDF/Afbeelding)", type=['pdf', 'jpg', 'png'])
        submit = st.form_submit_button("Aanvraag Verzenden")

    if submit and vnaam and email:
        if datum.weekday() in [0, 2] and tijd not in bezet:
            doc_url = ""
            if uploaded_file:
                # Zorg dat de bucket 'documenten' in Supabase op 'Public' staat!
                filename = f"{vnaam}_{datetime.datetime.now().strftime('%Y%m%d_%H%M%S')}.pdf"
                supabase.storage.from_("documenten").upload(filename, uploaded_file.getvalue())
                doc_url = supabase.storage.from_("documenten").get_public_url(filename)

            form_data = {
                "voornaam": vnaam, "achternaam": anaam, "email": email, "id_nummer": id_nr,
                "lad_nummer": lad_nr, "telefoon": tel, "afspraak_datum": str(datum),
                "afspraak_tijd": tijd, "status": "In behandeling", "document_url": doc_url
            }
            supabase.table("aanvragen").insert(form_data).execute()
            st.success("✅ Uw aanvraag is succesvol verzonden!")
        else:
            st.error("⚠️ Afspraken kunnen alleen op Maandag of Woensdag.")

# --- 6. MEDEWERKER PORTAAL (Gefixte Inlog & Beheer) ---
elif keuze == "Medewerker Portaal":
    if not st.session_state["logged_in"]:
        st.title("🔐 Login Medewerker")
        with st.form("login_form"):
            # .strip() verwijdert onzichtbare spaties bij het typen
            user_input = st.text_input("Gebruikersnaam").strip()
            pass_input = st.text_input("Wachtwoord", type="password").strip()
            if st.form_submit_button("Inloggen"):
                # .ilike is niet hoofdlettergevoelig
                res = supabase.table("medewerkers").select("*").ilike("gebruikersnaam", user_input).execute()
                
                if res.data and res.data[0]['wachtwoord'] == pass_input:
                    st.session_state["logged_in"] = True
                    st.session_state["user_rol"] = res.data[0]['rol']
                    st.rerun()
                else:
                    st.error("Onjuiste inloggegevens.")
    else:
        st.sidebar.button("Uitloggen", on_click=lambda: st.session_state.update({"logged_in": False}))
        
        tabs = st.tabs(["📋 Beheer & Correcties", "📅 Kalender", "⚙️ Admin"])
        
        with tabs[0]: # BEHEER & CORRECTIE FUNCTIES
            res = supabase.table("aanvragen").select("*").execute()
            if res.data:
                df = pd.DataFrame(res.data)
                st.subheader("Dossier Wijzigen")
                st.info("Hier kunnen medewerkers gegevens zoals LAD-nummers corrigeren.")
                
                sel_id = st.selectbox("Selecteer Dossier ID", df['id'].tolist())
                dossier = df[df['id'] == sel_id].iloc[0]
                
                c1, c2 = st.columns(2)
                with c1:
                    edit_lad = st.text_input("LAD Nummer corrigeren", value=dossier['lad_nummer'])
                with c2:
                    edit_status = st.selectbox("Status aanpassen", ["In behandeling", "Bevestigd", "Geannuleerd"], 
                                               index=["In behandeling", "Bevestigd", "Geannuleerd"].index(dossier['status']))
                
                if st.button("Wijzigingen Opslaan"):
                    supabase.table("aanvragen").update({"lad_nummer": edit_lad, "status": edit_status}).eq("id", sel_id).execute()
                    st.success("Dossier succesvol bijgewerkt!")
                    st.rerun()
                
                st.dataframe(df)

        if st.session_state["user_rol"] == "Admin":
            with tabs[2]: # ADMIN TAB
                st.header("Admin Instellingen")
                new_user = st.text_input("Nieuwe Gebruikersnaam")
                new_pass = st.text_input("Wachtwoord")
                if st.button("Account Aanmaken"):
                    supabase.table("medewerkers").insert({"gebruikersnaam": new_user, "wachtwoord": new_pass, "rol": "Medewerker"}).execute()
                    st.success(f"Account voor {new_user} aangemaakt!")

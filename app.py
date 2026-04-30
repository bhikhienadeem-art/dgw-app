import streamlit as st
from supabase import create_client, Client
import smtplib
from email.mime.text import MIMEText
from email.mime.multipart import MIMEMultipart
import datetime
import pandas as pd

# --- 1. CONFIGURATIE & STYLING (Groen/Wit thema) ---
st.set_page_config(page_title="DGW Wanica Portaal", page_icon="📝", layout="wide")

st.markdown("""
    <style>
    .main { background-color: #ffffff; }
    .stButton>button { background-color: #2e7d32 !important; color: white !important; border-radius: 5px; width: 100%; }
    h1, h2, h3 { color: #1b5e20; }
    .stAlert { border-radius: 10px; }
    </style>
    """, unsafe_allow_html=True)

# --- 2. DATABASE VERBINDING ---
try:
    URL = st.secrets["SUPABASE_URL"]
    KEY = st.secrets["SUPABASE_KEY"]
    supabase: Client = create_client(URL, KEY)
except Exception as e:
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

def stuur_mail(ontvanger, onderwerp, bericht):
    try:
        GMAIL_USER = st.secrets["GMAIL_USER"]
        GMAIL_PASSWORD = st.secrets["GMAIL_PASSWORD"]
        msg = MIMEMultipart()
        msg['From'] = f"DGW Wanica <{GMAIL_USER}>"
        msg['To'] = ontvanger
        msg['Subject'] = onderwerp
        msg.attach(MIMEText(bericht, 'plain'))
        server = smtplib.SMTP('smtp.gmail.com', 587)
        server.starttls()
        server.login(GMAIL_USER, GMAIL_PASSWORD)
        server.sendmail(GMAIL_USER, ontvanger, msg.as_string())
        server.quit()
        return True
    except: return False

# --- 4. NAVIGATIE & SESSIEBEHEER ---
if "logged_in" not in st.session_state:
    st.session_state["logged_in"] = False
    st.session_state["user_rol"] = None
    st.session_state["user_naam"] = None

st.sidebar.title("DGW Menu")
keuze = st.sidebar.radio("Ga naar:", ["Cliënt Registratie", "Medewerker Portaal"])

# --- 5. CLIËNT REGISTRATIE ---
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
        
        # Tijdsloten met 15 min interval en beschikbaarheidscheck
        alle_tijden, bezet = get_beschikbare_tijden(datum)
        tijd = st.selectbox("Kies tijdstip (15 min)", alle_tijden)
        
        if tijd in bezet:
            st.error(f"🔴 {tijd} is al bezet. Kies een andere tijd.")
        else:
            st.success(f"🟢 {tijd} is beschikbaar op {datum}.")

        uploaded_file = st.file_uploader("Upload Documenten (PDF/Afbeelding)", type=['pdf', 'jpg', 'png'])
        submit = st.form_submit_button("Aanvraag Verzenden")

    if submit:
        # Check op Maandag (0) of Woensdag (2)
        if datum.weekday() in [0, 2] and tijd not in bezet:
            doc_url = ""
            if uploaded_file:
                path = f"docs/{vnaam}_{datetime.datetime.now().timestamp()}_{uploaded_file.name}"
                supabase.storage.from_("documenten").upload(path, uploaded_file.getvalue())
                doc_url = supabase.storage.from_("documenten").get_public_url(path)

            data = {
                "voornaam": vnaam, "achternaam": anaam, "email": email, "id_nummer": id_nr,
                "lad_nummer": lad_nr, "telefoon": tel, "afspraak_datum": str(datum),
                "afspraak_tijd": tijd, "status": "In behandeling", "document_url": doc_url
            }
            supabase.table("aanvragen").insert(data).execute()
            st.success("✅ Uw aanvraag is succesvol verzonden!")
        else:
            st.error("⚠️ Afspraken alleen op Maandag/Woensdag of tijd is al bezet.")

# --- 6. MEDEWERKER PORTAAL (Gefixte Inlog & Beheer) ---
elif keuze == "Medewerker Portaal":
    if not st.session_state["logged_in"]:
        st.title("🔐 Login Medewerker")
        with st.form("login"):
            u_input = st.text_input("Gebruikersnaam").strip()
            p_input = st.text_input("Wachtwoord", type="password").strip()
            if st.form_submit_button("Inloggen"):
                # Haal gebruiker op ongeacht hoofdletters
                res = supabase.table("medewerkers").select("*").ilike("gebruikersnaam", u_input).execute()
                
                if res.data and res.data[0]['wachtwoord'] == p_input:
                    st.session_state["logged_in"] = True
                    st.session_state["user_rol"] = res.data[0]['rol']
                    st.session_state["user_naam"] = res.data[0]['gebruikersnaam']
                    st.rerun()
                else:
                    st.error("Onjuiste gegevens. Let op spaties of hoofdletters.")
    else:
        st.sidebar.info(f"Gebruiker: {st.session_state['user_naam']}")
        if st.sidebar.button("Uitloggen"):
            st.session_state["logged_in"] = False
            st.rerun()
        
        tabs = st.tabs(["📋 Aanvragen Beheren", "📅 Kalender", "⚙️ Admin"])
        
        with tabs[0]: # BEHEER (Inclusief correctie van fouten)
            res = supabase.table("aanvragen").select("*").execute()
            if res.data:
                df = pd.DataFrame(res.data)
                st.subheader("Overzicht & Correcties")
                st.write("Medewerkers kunnen hier gegevens wijzigen bij fouten.")
                
                sel_id = st.selectbox("Selecteer Dossier ID voor wijziging", df['id'].tolist())
                dossier = df[df['id'] == sel_id].iloc[0]
                
                col_a, col_b = st.columns(2)
                with col_a:
                    new_vnaam = st.text_input("Voornaam", value=dossier['voornaam'])
                    new_status = st.selectbox("Status", ["In behandeling", "Bevestigd", "Geannuleerd"], index=["In behandeling", "Bevestigd", "Geannuleerd"].index(dossier['status']))
                with col_b:
                    new_lad = st.text_input("LAD Nummer", value=dossier['lad_nummer'])
                
                if st.button("Wijzigingen Opslaan"):
                    update_data = {"voornaam": new_vnaam, "lad_nummer": new_lad, "status": new_status}
                    supabase.table("aanvragen").update(update_data).eq("id", sel_id).execute()
                    if new_status != dossier['status']:
                        stuur_mail(dossier['email'], "Update DGW Wanica", f"Uw status is gewijzigd naar: {new_status}")
                    st.success("Gegevens succesvol gecorrigeerd!")
                    st.rerun()
                
                st.dataframe(df)

        if st.session_state["user_rol"] == "Admin":
            with tabs[2]: # ADMIN INSTELLINGEN
                st.header("⚙️ Beheer Medewerkers")
                with st.form("add_user"):
                    nu = st.text_input("Nieuwe Gebruikersnaam")
                    np = st.text_input("Wachtwoord")
                    nr = st.selectbox("Rol", ["Medewerker", "Admin"])
                    if st.form_submit_button("Account Aanmaken"):
                        supabase.table("medewerkers").insert({"gebruikersnaam": nu, "wachtwoord": np, "rol": nr}).execute()
                        st.success(f"Medewerker {nu} toegevoegd!")

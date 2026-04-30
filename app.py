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
    
    # Check bezette tijden
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

# --- 4. NAVIGATIE ---
if "logged_in" not in st.session_state:
    st.session_state["logged_in"] = False
    st.session_state["user_rol"] = None

st.sidebar.title("DGW Menu")
keuze = st.sidebar.radio("Ga naar:", ["Cliënt Registratie", "Medewerker Portaal"])

# --- 5. CLIËNT REGISTRATIE (Inclusief Upload & 15min Check) ---
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
        
        # Tijdsloten met status
        alle_tijden, bezet = get_beschikbare_tijden(datum)
        tijd = st.selectbox("Kies tijdstip (15 min)", alle_tijden)
        
        if tijd in bezet:
            st.error(f"🔴 {tijd} is al bezet. Kies een andere tijd.")
        else:
            st.success(f"🟢 {tijd} is beschikbaar.")

        uploaded_file = st.file_uploader("Upload Documenten (PDF/Afbeelding)", type=['pdf', 'jpg', 'png'])
        submit = st.form_submit_button("Aanvraag Verzenden")

    if submit:
        if datum.weekday() in [0, 2] and tijd not in bezet:
            doc_url = ""
            if uploaded_file:
                path = f"{vnaam}_{datetime.datetime.now().timestamp()}.pdf"
                supabase.storage.from_("documenten").upload(path, uploaded_file.getvalue())
                doc_url = supabase.storage.from_("documenten").get_public_url(path)

            data = {
                "voornaam": vnaam, "achternaam": anaam, "email": email, "id_nummer": id_nr,
                "lad_nummer": lad_nr, "telefoon": tel, "afspraak_datum": str(datum),
                "afspraak_tijd": tijd, "status": "In behandeling", "document_url": doc_url
            }
            supabase.table("aanvragen").insert(data).execute()
            st.balloons()
            st.success("Uw aanvraag is succesvol verzonden!")
        else:
            st.error("Controleer de dag (Ma/Wo) en of de tijd nog vrij is.")

# --- 6. MEDEWERKER PORTAAL (De Fix voor inloggen) ---
elif keuze == "Medewerker Portaal":
    if not st.session_state["logged_in"]:
        st.title("🔐 Login")
        with st.form("login"):
            u = st.text_input("Gebruikersnaam")
            p = st.text_input("Wachtwoord", type="password")
            if st.form_submit_button("Inloggen"):
                # We gebruiken .ilike voor de naam en .eq voor het wachtwoord
                res = supabase.table("medewerkers").select("*").ilike("gebruikersnaam", u.strip()).execute()
                
                if res.data and res.data[0]['wachtwoord'] == p.strip():
                    st.session_state["logged_in"] = True
                    st.session_state["user_rol"] = res.data[0]['rol']
                    st.rerun()
                else:
                    st.error("Onjuiste gegevens")
    else:
        st.sidebar.button("Uitloggen", on_click=lambda: st.session_state.update({"logged_in": False}))
        
        tabs = st.tabs(["📋 Beheer", "📅 Kalender", "⚙️ Admin"])
        
        with tabs[0]: # BEHEER (Inclusief DC-nummer correctie)
            res = supabase.table("aanvragen").select("*").execute()
            if res.data:
                df = pd.DataFrame(res.data)
                st.dataframe(df)
                
                st.subheader("Dossier Wijzigen")
                sel_id = st.selectbox("Selecteer ID", df['id'].tolist())
                new_status = st.selectbox("Status", ["Bevestigd", "Geannuleerd", "In behandeling"])
                # Hier kunnen ze ook DC nummers of andere velden corrigeren
                if st.button("Update Dossier"):
                    supabase.table("aanvragen").update({"status": new_status}).eq("id", sel_id).execute()
                    st.success("Dossier bijgewerkt!")
                    st.rerun()

        if st.session_state["user_rol"] == "Admin":
            with tabs[2]: # ADMIN
                st.header("Admin Paneel")
                with st.form("add_user"):
                    nu = st.text_input("Nieuwe Gebruikersnaam")
                    np = st.text_input("Wachtwoord")
                    nr = st.selectbox("Rol", ["Medewerker", "Admin"])
                    if st.form_submit_button("Medewerker Toevoegen"):
                        supabase.table("medewerkers").insert({"gebruikersnaam": nu, "wachtwoord": np, "rol": nr}).execute()
                        st.success("Toegevoegd!")

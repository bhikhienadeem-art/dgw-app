import streamlit as st
from supabase import create_client, Client
import smtplib
from email.mime.text import MIMEText
from email.mime.multipart import MIMEMultipart

# 1. Pagina Configuratie & Styling (Groen/Wit)
st.set_page_config(page_title="Dienst Grondzaken Wanica", page_icon="📝", layout="wide")

st.markdown("""
    <style>
    .main { background-color: #ffffff; }
    .stButton>button { background-color: #2e7d32; color: white; }
    .sidebar .sidebar-content { background-color: #f1f8e9; }
    h1, h2, h3 { color: #1b5e20; }
    </style>
    """, unsafe_allow_value=True)

# 2. Database Verbinding
try:
    URL = st.secrets["SUPABASE_URL"]
    KEY = st.secrets["SUPABASE_KEY"]
    supabase: Client = create_client(URL, KEY)
except:
    st.error("Configuratie fout. Controleer je Streamlit Secrets.")
    st.stop()

# 3. E-mail Functie
def stuur_mail(data):
    GMAIL_USER = st.secrets["GMAIL_USER"]
    GMAIL_PASSWORD = st.secrets["GMAIL_PASSWORD"]
    MEDEWERKER = "wanicacentrum.gz@gmail.com"
    
    try:
        msg = MIMEMultipart()
        msg['From'] = GMAIL_USER
        msg['To'] = f"{data['email']}, {MEDEWERKER}"
        msg['Subject'] = f"Nieuwe Registratie: {data['voornaam']} {data['achternaam']}"
        
        inhoud = f"Nieuwe aanvraag ontvangen:\n\nNaam: {data['voornaam']} {data['achternaam']}\nID: {data['id_nummer']}\nLAD: {data['lad_nummer']}\nTelefoon: {data['telefoon']}\nAdres: {data['woonadres']}\n\nBericht: {data['bericht']}\nAfspraak: {data['datum']} om {data['tijd']}"
        msg.attach(MIMEText(inhoud, 'plain'))
        
        server = smtplib.SMTP('smtp.gmail.com', 587)
        server.starttls()
        server.login(GMAIL_USER, GMAIL_PASSWORD)
        server.sendmail(GMAIL_USER, [data['email'], MEDEWERKER], msg.as_string())
        server.quit()
        return True
    except:
        return False

# 4. Zijmenu (DGW Menu)
st.sidebar.title("DGW Menu")
keuze = st.sidebar.radio("Ga naar:", ["Cliënt Registratie", "Medewerker Login"])

if keuze == "Cliënt Registratie":
    st.title("📝 Portaal: Dienst Grondzaken Wanica")
    st.subheader("Registratieformulier")

    with st.form("registratie_form", clear_on_submit=True):
        col1, col2 = st.columns(2)
        with col1:
            vnaam = st.text_input("Voornaam *")
            id_nr = st.text_input("ID-Nummer *")
            tel = st.text_input("Telefoonnummer *")
        with col2:
            anaam = st.text_input("Achternaam *")
            lad_nr = st.text_input("LAD Nummer *")
            email = st.text_input("E-mailadres *")
        
        adres = st.text_input("Woonadres *")
        bericht = st.text_area("Omschrijving van uw klacht of aanvraag *")
        
        st.write("Upload relevante documenten")
        upload = st.file_uploader("Kies bestand", type=['pdf', 'png', 'jpg'], help="Max 200MB per file")
        
        st.write("---")
        col_d, col_t = st.columns(2)
        with col_d:
            # Afspraken alleen op maandag en woensdag (zoals gevraagd in je eerdere instructies)
            datum = st.date_input("Kies een datum voor afspraak")
        with col_t:
            tijd = st.selectbox("Tijd", ["07:00", "07:15", "07:30", "07:45", "08:00"])

        submit = st.form_submit_button("Verzenden")

    if submit:
        if vnaam and anaam and email and id_nr:
            form_data = {
                "voornaam": vnaam, "achternaam": anaam, "id_nummer": id_nr,
                "lad_nummer": lad_nr, "telefoon": tel, "woonadres": adres,
                "email": email, "bericht": bericht, "datum": str(datum), "tijd": tijd
            }
            try:
                supabase.table("aanvragen").insert(form_data).execute()
                if stuur_mail(form_data):
                    st.success("✅ Uw aanvraag is succesvol verzonden naar de database en de inbox van de medewerker.")
            except Exception as e:
                st.error(f"Fout: {e}")
        else:
            st.warning("Vul a.u.b. alle verplichte velden in.")

elif keuze == "Medewerker Login":
    st.title("🔐 Medewerker Login")
    user = st.text_input("Gebruikersnaam")
    pw = st.text_input("Wachtwoord", type="password")
    if st.button("Login"):
        st.info("Systeem administratie module is momenteel in onderhoud.")

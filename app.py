import streamlit as st
from supabase import create_client, Client
import smtplib
from email.mime.text import MIMEText
from email.mime.multipart import MIMEMultipart
import datetime

# 1. Pagina Configuratie & Styling (Groen/Wit)
st.set_page_config(page_title="Dienst Grondzaken Wanica", page_icon="📝", layout="wide")

# Correctie: unsafe_allow_html=True (zoals te zien in image_8c0797.png)
st.markdown("""
    <style>
    .main { background-color: #ffffff; }
    .stButton>button { background-color: #2e7d32; color: white; border-radius: 5px; }
    .sidebar .sidebar-content { background-color: #f1f8e9; }
    h1, h2, h3 { color: #1b5e20; font-family: 'Arial'; }
    </style>
    """, unsafe_allow_html=True)

# 2. Database Verbinding met Secrets
try:
    URL = st.secrets["SUPABASE_URL"]
    KEY = st.secrets["SUPABASE_KEY"]
    supabase: Client = create_client(URL, KEY)
except Exception as e:
    st.error("Configuratie fout. Controleer je Streamlit Secrets.")
    st.stop()

# 3. E-mail Functie (Gmail)
def stuur_mail(data):
    try:
        GMAIL_USER = st.secrets["GMAIL_USER"]
        GMAIL_PASSWORD = st.secrets["GMAIL_PASSWORD"]
        MEDEWERKER = "wanicacentrum.gz@gmail.com"
        
        msg = MIMEMultipart()
        msg['From'] = GMAIL_USER
        msg['To'] = f"{data['email']}, {MEDEWERKER}"
        msg['Subject'] = f"Nieuwe Registratie: {data['voornaam']} {data['achternaam']}"
        
        inhoud = f"""
        Nieuwe aanvraag ontvangen via het DGW Portaal:

        Naam: {data['voornaam']} {data['achternaam']}
        ID-Nummer: {data['id_nummer']}
        LAD-Nummer: {data['lad_nummer']}
        Telefoon: {data['telefoon']}
        Woonadres: {data['woonadres']}
        E-mail: {data['email']}

        Bericht/Klacht:
        {data['bericht']}

        Afspraak gepland op: {data['datum']} om {data['tijd']}
        """
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
st.sidebar.markdown("<h2 style='color: #2e7d32;'>DGW Menu</h2>", unsafe_allow_html=True)
keuze = st.sidebar.radio("Ga naar:", ["Cliënt Registratie", "Medewerker Login"])

if keuze == "Cliënt Registratie":
    st.markdown("# 📝 Portaal: Dienst Grondzaken Wanica")
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
        
        st.write("---")
        st.write("**Afspraak inplannen (Maandag of Woensdag)**")
        col_d, col_t = st.columns(2)
        with col_d:
            datum = st.date_input("Kies een datum", min_value=datetime.date.today())
        with col_t:
            tijd = st.selectbox("Tijd", ["07:00", "07:30", "08:00", "08:30", "09:00"])

        # Upload functie zoals in image_a7722d.png
        st.write("---")
        upload = st.file_uploader("Upload relevante documenten (ID, perceelkaart, etc.)", type=['pdf', 'png', 'jpg'])
        
        submit = st.form_submit_button("Verzenden")

    if submit:
        # Check op verplichte velden
        if vnaam and anaam and email and id_nr and bericht:
            # Controle op Maandag (0) of Woensdag (2)
            if datum.weekday() in [0, 2]:
                form_data = {
                    "voornaam": vnaam, "achternaam": anaam, "id_nummer": id_nr,
                    "lad_nummer": lad_nr, "telefoon": tel, "woonadres": adres,
                    "email": email, "bericht": bericht, "datum": str(datum), "tijd": tijd
                }
                try:
                    # Opslaan in Supabase
                    supabase.table("aanvragen").insert(form_data).execute()
                    # Mail versturen
                    stuur_mail(form_data)
                    st.success(f"✅ Bedankt {vnaam}! Uw aanvraag is opgeslagen en verzonden naar de medewerker.")
                except Exception as e:
                    st.error(f"Database fout: {e}")
            else:
                st.error("⚠️ Afspraken kunnen alleen op Maandag of Woensdag worden gemaakt.")
        else:
            st.warning("Vul a.u.b. alle velden met een * in.")

elif keuze == "Medewerker Login":
    st.title("🔐 Medewerker Login")
    user = st.text_input("Gebruikersnaam")
    pw = st.text_input("Wachtwoord", type="password")
    if st.button("Inloggen"):
        st.info("Beveiligde omgeving wordt geladen...")

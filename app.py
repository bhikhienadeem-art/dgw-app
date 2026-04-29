import streamlit as st
from supabase import create_client
import smtplib
from email.mime.text import MIMEText
from email.mime.multipart import MIMEMultipart

# --- 1. CONFIGURATIE & BEVEILIGING ---
# We halen de gegevens nu veilig uit de 'Secrets' kluis
try:
    url = st.secrets["SUPABASE_URL"]
    key = st.secrets["SUPABASE_KEY"]
    GMAIL_USER = st.secrets["GMAIL_USER"]
    GMAIL_PASSWORD = st.secrets["GMAIL_PASSWORD"]
    supabase = create_client(url, key)
except Exception as e:
    st.error("Configuratie fout: Controleer je Streamlit Secrets.")
    st.stop()

# --- 2. PAGINA INSTELLINGEN ---
st.set_page_config(page_title="DGW Portaal", page_icon="📝", layout="wide")

# --- 3. SIDEBAR (DGW Menu) ---
with st.sidebar:
    st.header("DGW Menu")
    st.write("Ga naar:")
    page = st.radio("", ["Cliënt Registratie", "Medewerker Login"])

# --- 4. FUNCTIE VOOR EMAIL ---
def send_confirmation(to_email, naam):
    try:
        subject = "Bevestiging Registratie - Dienst Grondzaken Wanica"
        body = f"Beste {naam},\n\nUw registratie bij het portaal van Dienst Grondzaken Wanica is succesvol ontvangen.\n\nMet vriendelijke groet,\nCommissariaat Wanica"
        
        msg = MIMEMultipart()
        msg['From'] = GMAIL_USER
        msg['To'] = to_email
        msg['Subject'] = subject
        msg.attach(MIMEText(body, 'plain'))
        
        server = smtplib.SMTP('smtp.gmail.com', 587)
        server.starttls()
        server.login(GMAIL_USER, GMAIL_PASSWORD)
        server.send_message(msg)
        server.quit()
    except:
        pass

# --- 5. HOOFDPAGINA: CLIËNT REGISTRATIE ---
if page == "Cliënt Registratie":
    st.title("📝 Portaal: Dienst Grondzaken Wanica")
    st.subheader("Registratieformulier")

    with st.form("registratie_form"):
        # Gebruik kolommen zoals in je screenshot
        col1, col2 = st.columns(2)
        with col1:
            voornaam = st.text_input("Voornaam *")
            id_nummer = st.text_input("ID-Nummer *")
            telefoon = st.text_input("Telefoonnummer *")
        with col2:
            achternaam = st.text_input("Achternaam *")
            lad_nummer = st.text_input("LAD Nummer *")
            email = st.text_input("E-mailadres *")
            
        woonadres = st.text_input("Woonadres *")
        bericht = st.text_area("Omschrijving van uw klacht of aanvraag *")
        
        st.write("Upload relevante documenten")
        uploaded_file = st.file_uploader("", type=['pdf', 'jpg', 'png'])
        
        afspraak_datum = st.date_input("Kies een datum voor afspraak")
        
        submit = st.form_submit_button("Verzenden")

    if submit:
        if voornaam and achternaam and email:
            # Data opslaan in Supabase
            data = {
                "voornaam": voornaam, 
                "achternaam": achternaam, 
                "email": email, 
                "id_nummer": id_nummer,
                "bericht": bericht
            }
            try:
                supabase.table("aanvragen").insert(data).execute()
                send_confirmation(email, voornaam)
                st.success("✅ Uw registratie is succesvol ingediend!")
            except Exception as e:
                st.error(f"Fout: {e}")
        else:
            st.error("Vul a.u.b. alle verplichte velden in.")

# --- 6. MEDEWERKER LOGIN ---
elif page == "Medewerker Login":
    st.title("🔐 Medewerker Login")
    st.text_input("Gebruikersnaam")
    st.text_input("Wachtwoord", type="password")
    st.button("Login")

import streamlit as st
from supabase import create_client
import smtplib
from email.mime.text import MIMEText
from email.mime.multipart import MIMEMultipart

# 1. Beveiligde Verbinding met de Database (Supabase)
# Haalt URL en KEY op uit de Streamlit Secrets kluis
url = st.secrets["SUPABASE_URL"]
key = st.secrets["SUPABASE_KEY"]
supabase = create_client(url, key)

# 2. Beveiligde Email Instellingen (Gmail)
# Haalt e-mail en app-wachtwoord op uit de kluis
GMAIL_USER = st.secrets["GMAIL_USER"]
GMAIL_PASSWORD = st.secrets["GMAIL_PASSWORD"]

def send_email(to_email, subject, body):
    try:
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
        return True
    except Exception as e:
        st.error(f"Fout bij versturen mail: {e}")
        return False

# --- UI START ---
st.set_page_config(page_title="Dienst Grondzaken Wanica", page_icon="📝")

st.title("🏛️ Burgerportaal Dienst Grondzaken Wanica")
st.subheader("Dien hier uw aanvraag of klacht in")

with st.form("aanvraag_form", clear_on_submit=True):
    naam = st.text_input("Volledige Naam")
    email = st.text_input("Uw E-mailadres")
    onderwerp = st.selectbox("Type aanvraag", ["Bereidverklaring", "Toewijzing", "Klacht", "Informatieverzoek"])
    bericht = st.text_area("Omschrijving van uw verzoek")
    
    submit = st.form_submit_button("Verzenden")

if submit:
    if naam and email and bericht:
        # Gegevens opslaan in Supabase
        data = {
            "naam": naam,
            "email": email,
            "onderwerp": onderwerp,
            "bericht": bericht
        }
        
        try:
            supabase.table("aanvragen").insert(data).execute()
            
            # Bevestigingsmail sturen
            mail_onderwerp = f"Bevestiging ontvangst: {onderwerp}"
            mail_body = f"Geachte heer/mevrouw {naam},\n\nBedankt voor uw bericht. We hebben uw verzoek over '{onderwerp}' ontvangen en nemen dit zo snel mogelijk in behandeling.\n\nMet vriendelijke groet,\nCommissariaat Wanica Centrum"
            
            if send_email(email, mail_onderwerp, mail_body):
                st.success("Uw aanvraag is succesvol ingediend! Er is een bevestiging gestuurd naar uw e-mail.")
            else:
                st.warning("Aanvraag opgeslagen, maar kon geen e-mail sturen.")
                
        except Exception as e:
            st.error(f"Er is iets misgegaan bij het opslaan: {e}")
    else:
        st.error("Vul a.u.b. alle velden in.")

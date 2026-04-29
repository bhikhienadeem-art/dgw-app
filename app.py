import streamlit as st
from supabase import create_client, Client
import smtplib
from email.mime.text import MIMEText
from email.mime.multipart import MIMEMultipart

# 1. Database verbinding met de juiste namen (Hoofdletters!)
# Dit lost de foutmelding in image_96de39.png op
try:
    url: str = st.secrets["SUPABASE_URL"]
    key: str = st.secrets["SUPABASE_KEY"]
    supabase: Client = create_client(url, key)
except Exception as e:
    st.error(f"Configuratie fout: {e}")
    st.stop()

# 2. E-mail configuratie
GMAIL_USER = st.secrets["GMAIL_USER"]
GMAIL_PASSWORD = st.secrets["GMAIL_PASSWORD"]
MEDEWERKER_EMAIL = "wanicacentrum.gz@gmail.com" 

def send_email(burger_email, voornaam, achternaam, id_nummer, datum, tijd, bericht):
    try:
        msg = MIMEMultipart()
        msg['From'] = GMAIL_USER
        # De mail gaat naar de burger EN de medewerker inbox
        msg['To'] = f"{burger_email}, {MEDEWERKER_EMAIL}"
        msg['Subject'] = f"Nieuwe Afspraak Aanvraag: {voornaam} {achternaam}"

        body = f"""
        Nieuwe aanvraag via het portaal:

        GEGEVENS:
        Naam: {voornaam} {achternaam}
        ID-Nummer: {id_nummer}
        Datum: {datum}
        Tijdstip: {tijd}
        
        BERICHT:
        {bericht}

        Contact burger: {burger_email}
        """
        msg.attach(MIMEText(body, 'plain'))

        server = smtplib.SMTP('smtp.gmail.com', 587)
        server.starttls()
        server.login(GMAIL_USER, GMAIL_PASSWORD)
        
        ontvangers = [burger_email, MEDEWERKER_EMAIL]
        server.sendmail(GMAIL_USER, ontvangers, msg.as_string())
        server.quit()
        return True
    except Exception as e:
        st.error(f"E-mail fout: {e}")
        return False

# 3. Streamlit Interface
st.set_page_config(page_title="Commissariaat Wanica Centrum", page_icon="🏛️")
st.title("🏛️ Commissariaat Wanica Centrum")
st.subheader("Afspraak & Klachten Portaal")

with st.form("afspraak_form", clear_on_submit=True):
    col1, col2 = st.columns(2)
    with col1:
        voornaam = st.text_input("Voornaam *")
        id_nummer = st.text_input("ID-Nummer *")
    with col2:
        achternaam = st.text_input("Achternaam *")
        email_burger = st.text_input("Uw E-mailadres *")
    
    bericht = st.text_area("Omschrijving van uw klacht of aanvraag *")
    
    st.write("---")
    datum = st.date_input("Kies een datum")
    tijd = st.selectbox("Tijd", ["07:00", "07:15", "07:30", "07:45", "08:00"])

    submit = st.form_submit_button("Verzenden")

if submit:
    if not (voornaam and achternaam and email_burger and id_nummer and bericht):
        st.warning("Vul alstublieft alle velden in.")
    else:
        data = {
            "voornaam": voornaam,
            "achternaam": achternaam,
            "email": email_burger,
            "id_nummer": id_nummer,
            "bericht": bericht,
            "afspraak_datum": str(datum),
            "afspraak_tijd": tijd
        }
        
        try:
            # Opslaan in de database
            supabase.table("aanvragen").insert(data).execute()
            
            # Mail versturen (itmr ghtd zimi hsan wordt gebruikt via de secrets)
            if send_email(email_burger, voornaam, achternaam, id_nummer, datum, tijd, bericht):
                st.success(f"✅ Succes! De aanvraag is verwerkt en naar de inbox van de medewerker gestuurd.")
        except Exception as e:
            st.error(f"Database fout: {e}")

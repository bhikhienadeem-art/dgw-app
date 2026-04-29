import streamlit as st
from supabase import create_client, Client
import smtplib
from email.mime.text import MIMEText
from email.mime.multipart import MIMEMultipart

# 1. Pagina configuratie (voor de look uit je screenshot)
st.set_page_config(page_title="Commissariaat Wanica Centrum", page_icon="🏛️")

# 2. Verbinding met de database (Supabase)
# We gebruiken hoofdletters zodat dit matcht met je Streamlit Secrets
try:
    URL = st.secrets["SUPABASE_URL"]
    KEY = st.secrets["SUPABASE_KEY"]
    supabase: Client = create_client(URL, KEY)
except Exception as e:
    st.error("Er is een probleem met de databaseverbinding. Controleer je Secrets.")
    st.stop()

# 3. E-mail Functie
def send_email(burger_email, voornaam, achternaam, id_nummer, datum, tijd, omschrijving):
    GMAIL_USER = st.secrets["GMAIL_USER"]
    GMAIL_PASSWORD = st.secrets["GMAIL_PASSWORD"]
    MEDEWERKER_EMAIL = "wanicacentrum.gz@gmail.com"

    try:
        msg = MIMEMultipart()
        msg['From'] = GMAIL_USER
        msg['To'] = f"{burger_email}, {MEDEWERKER_EMAIL}"
        msg['Subject'] = f"Nieuwe Aanvraag: {voornaam} {achternaam}"

        body = f"""
        Nieuwe afspraak/klacht binnengekomen:

        Naam: {voornaam} {achternaam}
        ID-Nummer: {id_nummer}
        Datum: {datum}
        Tijd: {tijd}

        Omschrijving:
        {omschrijving}

        Contact burger: {burger_email}
        """
        msg.attach(MIMEText(body, 'plain'))

        server = smtplib.SMTP('smtp.gmail.com', 587)
        server.starttls()
        server.login(GMAIL_USER, GMAIL_PASSWORD)
        server.sendmail(GMAIL_USER, [burger_email, MEDEWERKER_EMAIL], msg.as_string())
        server.quit()
        return True
    except Exception as e:
        st.error(f"E-mail kon niet worden verzonden: {e}")
        return False

# 4. De Interface (Precies zoals in je screenshot)
st.markdown("# 🏛️ Commissariaat Wanica Centrum")
st.markdown("### Afspraak & Klachten Portaal")

with st.form("main_form", clear_on_submit=True):
    col1, col2 = st.columns(2)
    with col1:
        vnaam = st.text_input("Voornaam *")
        id_nr = st.text_input("ID-Nummer *")
    with col2:
        anaam = st.text_input("Achternaam *")
        email = st.text_input("Uw E-mailadres *")
    
    omschrijving = st.text_area("Omschrijving van uw klacht of aanvraag *")
    
    st.markdown("---")
    
    datum = st.date_input("Kies een datum")
    tijd = st.selectbox("Tijd", ["07:00", "07:15", "07:30", "07:45", "08:00", "08:15", "08:30"])

    submit_button = st.form_submit_button("Verzenden")

# 5. Logica bij verzenden
if submit_button:
    if not (vnaam and anaam and id_nr and email and omschrijving):
        st.warning("Vul alstublieft alle velden met een * in.")
    else:
        # Stap A: Opslaan in Supabase
        data = {
            "voornaam": vnaam,
            "achternaam": anaam,
            "id_nummer": id_nr,
            "email": email,
            "bericht": omschrijving,
            "afspraak_datum": str(datum),
            "afspraak_tijd": tijd
        }
        
        try:
            supabase.table("aanvragen").insert(data).execute()
            
            # Stap B: E-mail versturen
            if send_email(email, vnaam, anaam, id_nr, datum, tijd, omschrijving):
                st.success(f"✅ Uw aanvraag is succesvol verzonden, {vnaam}! Er is een kopie gestuurd naar de medewerker.")
            else:
                st.info("De gegevens zijn opgeslagen, maar de e-mailbevestiging is niet gelukt.")
        except Exception as e:
            st.error(f"Fout bij opslaan in database: {e}")

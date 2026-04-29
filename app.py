import streamlit as st
from supabase import create_client, Client
import smtplib
from email.mime.text import MIMEText
from email.mime.multipart import MIMEMultipart

# 1. Pagina-instellingen
st.set_page_config(page_title="Commissariaat Wanica Centrum", page_icon="🏛️", layout="centered")

# 2. Database verbinding (Supabase)
# Zorg dat deze namen EXACT zo in je Streamlit Secrets staan (Hoofdletters)
try:
    URL = st.secrets["SUPABASE_URL"]
    KEY = st.secrets["SUPABASE_KEY"]
    supabase: Client = create_client(URL, KEY)
except Exception as e:
    st.error("Configuratie fout: Controleer je Streamlit Secrets.")
    st.stop()

# 3. E-mail Functie (Gmail)
def send_notification(burger_email, vnaam, anaam, id_nr, lad_nr, tel, adres, bericht, datum, tijd):
    GMAIL_USER = st.secrets["GMAIL_USER"]
    GMAIL_PASSWORD = st.secrets["GMAIL_PASSWORD"]
    MEDEWERKER_EMAIL = "wanicacentrum.gz@gmail.com"

    try:
        msg = MIMEMultipart()
        msg['From'] = GMAIL_USER
        msg['To'] = f"{burger_email}, {MEDEWERKER_EMAIL}"
        msg['Subject'] = f"Nieuwe Aanvraag: {vnaam} {anaam}"

        body = f"""
        Er is een nieuwe aanvraag ingediend via het portaal.

        GEGEVENS VAN DE BURGER:
        -------------------------------------------
        Naam: {vnaam} {anaam}
        ID-Nummer: {id_nr}
        LAD-Nummer: {lad_nr}
        Telefoon: {tel}
        Woonadres: {adres}
        E-mail: {burger_email}

        AFSPRAAK DETAILS:
        -------------------------------------------
        Datum: {datum}
        Tijdstip: {tijd}
        Omschrijving: {bericht}

        Dit is een automatisch bericht van het Commissariaat Wanica Centrum.
        """
        msg.attach(MIMEText(body, 'plain'))

        server = smtplib.SMTP('smtp.gmail.com', 587)
        server.starttls()
        server.login(GMAIL_USER, GMAIL_PASSWORD)
        server.sendmail(GMAIL_USER, [burger_email, MEDEWERKER_EMAIL], msg.as_string())
        server.quit()
        return True
    except Exception as e:
        st.error(f"E-mail fout: {e}")
        return False

# 4. Gebruikersinterface (Visueel zoals in image_968821.png maar met ALLE velden)
st.markdown("# 🏛️ Commissariaat Wanica Centrum")
st.markdown("### Afspraak & Klachten Portaal")

with st.form("volledig_formulier", clear_on_submit=True):
    col1, col2 = st.columns(2)
    with col1:
        vnaam = st.text_input("Voornaam *")
        id_nr = st.text_input("ID-Nummer *")
        tel = st.text_input("Telefoonnummer *")
    with col2:
        anaam = st.text_input("Achternaam *")
        lad_nr = st.text_input("LAD Nummer (indien van toepassing)")
        email_burger = st.text_input("Uw E-mailadres *")
    
    adres = st.text_input("Woonadres *")
    omschrijving = st.text_area("Omschrijving van uw klacht of aanvraag *")
    
    st.markdown("---")
    
    c1, c2 = st.columns(2)
    with c1:
        datum = st.date_input("Kies een datum")
    with c2:
        tijd = st.selectbox("Beschikbare tijden", ["07:00", "07:15", "07:30", "07:45", "08:00", "08:15", "08:30"])

    submit = st.form_submit_button("Verzenden")

# 5. Verwerkingslogica
if submit:
    if not (vnaam and anaam and id_nr and email_burger and adres and omschrijving):
        st.warning("Vul alstublieft alle verplichte velden (*) in.")
    else:
        # Opslaan in database
        data = {
            "voornaam": vnaam,
            "achternaam": anaam,
            "id_nummer": id_nr,
            "lad_nummer": lad_nr,
            "telefoon": tel,
            "woonadres": adres,
            "email": email_burger,
            "bericht": omschrijving,
            "afspraak_datum": str(datum),
            "afspraak_tijd": tijd
        }
        
        try:
            supabase.table("aanvragen").insert(data).execute()
            
            # E-mail versturen met het app-wachtwoord uit image_96f81e.png
            if send_notification(email_burger, vnaam, anaam, id_nr, lad_nr, tel, adres, omschrijving, datum, tijd):
                st.success(f"✅ Bedankt {vnaam}! Uw aanvraag is succesvol verzonden naar de medewerker.")
        except Exception as e:
            st.error(f"Er is een fout opgetreden bij het opslaan: {e}")

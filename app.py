import streamlit as st
from supabase import create_client, Client
import smtplib
from email.mime.text import MIMEText
from email.mime.multipart import MIMEMultipart

# 1. Database verbinding (Supabase)
url: str = st.secrets["supabase_url"]
key: str = st.secrets["supabase_key"]
supabase: Client = create_client(url, key)

# 2. E-mail configuratie
GMAIL_USER = st.secrets["gmail_user"]
GMAIL_PASSWORD = st.secrets["gmail_password"]

# DIT IS HET ADRES VAN DE MEDEWERKER DIE DE MAIL IN DE INBOX MOET KRIJGEN
MEDEWERKER_EMAIL = "wanicacentrum.gz@gmail.com" 

def send_email(burger_email, voornaam, achternaam, id_nummer, datum, tijd, bericht):
    try:
        msg = MIMEMultipart()
        msg['From'] = GMAIL_USER
        # Toont beide e-mailadressen in de 'Aan' regel van de mail
        msg['To'] = f"{burger_email}, {MEDEWERKER_EMAIL}"
        msg['Subject'] = f"Nieuwe Afspraak Aanvraag: {voornaam} {achternaam}"

        body = f"""
        Geachte medewerker / heer/mevrouw {achternaam},

        Er is een nieuwe afspraak ingediend via het portaal.

        GEGEVENS VAN DE AANVRAAG:
        -------------------------------------------
        Naam burger: {voornaam} {achternaam}
        ID-Nummer: {id_nummer}
        Geplande datum: {datum}
        Tijdstip: {tijd}
        Omschrijving/Klacht: {bericht}
        -------------------------------------------
        Contactgegevens burger: {burger_email}

        Dit is een automatisch bericht vanuit het Commissariaat Wanica Centrum Portaal.
        """
        msg.attach(MIMEText(body, 'plain'))

        server = smtplib.SMTP('smtp.gmail.com', 587)
        server.starttls()
        server.login(GMAIL_USER, GMAIL_PASSWORD)
        
        # De 'ontvangers' lijst zorgt ervoor dat Gmail de mail naar beide adressen AFLEVERT
        ontvangers = [burger_email, MEDEWERKER_EMAIL]
        
        text = msg.as_string()
        server.sendmail(GMAIL_USER, ontvangers, text)
        server.quit()
        return True
    except Exception as e:
        st.error(f"E-mail verzendfout: {e}")
        return False

# 3. Streamlit Interface
st.title("🏛️ Commissariaat Wanica Centrum")
st.subheader("Afspraak & Klachten Portaal")

with st.form("afspraak_form", clear_on_submit=True):
    col1, col2 = st.columns(2)
    with col1:
        voornaam = st.text_input("Voornaam *")
        id_nummer = st.text_input("ID-Nummer *")
        telefoon = st.text_input("Telefoonnummer *")
    with col2:
        achternaam = st.text_input("Achternaam *")
        lad_nummer = st.text_input("LAD Nummer *")
        email_burger = st.text_input("Uw E-mailadres *")
    
    woonadres = st.text_input("Woonadres *")
    bericht = st.text_area("Omschrijving van uw klacht of aanvraag *")
    
    st.write("---")
    st.write("### Plan uw afspraak")
    
    c1, c2 = st.columns(2)
    with c1:
        datum = st.date_input("Kies een datum")
    with c2:
        tijd = st.selectbox("Beschikbare tijden", ["07:00", "07:15", "07:30", "07:45", "08:00"])

    submit = st.form_submit_button("Verzenden")

if submit:
    if not (voornaam and achternaam and email_burger and id_nummer and bericht):
        st.warning("Vul alstublieft alle verplichte velden in.")
    else:
        # Data voor de database
        data = {
            "voornaam": voornaam,
            "achternaam": achternaam,
            "email": email_burger,
            "id_nummer": id_nummer,
            "lad_nummer": lad_nummer,
            "telefoon": telefoon,
            "woonadres": woonadres,
            "bericht": bericht,
            "afspraak_datum": str(datum),
            "afspraak_tijd": tijd
        }
        
        try:
            # Opslaan in Supabase
            supabase.table("aanvragen").insert(data).execute()
            
            # Verstuur naar Inbox van medewerker én burger
            if send_email(email_burger, voornaam, achternaam, id_nummer, datum, tijd, bericht):
                st.success(f"✅ Succes! Uw aanvraag is verwerkt. De medewerker ({MEDEWERKER_EMAIL}) heeft een melding ontvangen in de inbox.")
            else:
                st.info("De gegevens zijn opgeslagen, maar de e-mail kon niet worden verzonden.")
        
        except Exception as e:
            st.error(f"Database fout: {e}")

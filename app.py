import streamlit as st
from supabase import create_client
import smtplib
from email.mime.text import MIMEText
from email.mime.multipart import MIMEMultipart
from datetime import datetime, time, timedelta

# --- 1. CONFIGURATIE & BEVEILIGING ---
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

# --- 3. SIDEBAR ---
with st.sidebar:
    st.header("DGW Menu")
    page = st.radio("Ga naar:", ["Cliënt Registratie", "Medewerker Login"])

# --- 4. HULPFUNCTIES VOOR AFSPRAKEN ---
def get_available_slots(datum_str):
    # Alle mogelijke slots van 07:00 tot 15:00
    all_slots = []
    start = datetime.combine(datetime.today(), time(7, 0))
    end = datetime.combine(datetime.today(), time(15, 0))
    while start < end:
        all_slots.append(start.strftime("%H:%M"))
        start += timedelta(minutes=15)
    
    # Haal bezette slots op uit Supabase voor deze specifieke datum
    try:
        response = supabase.table("aanvragen").select("afspraak_tijd").eq("afspraak_datum", datum_str).execute()
        occupied_slots = [record['afspraak_tijd'] for record in response.data]
        # Filter de bezette slots eruit
        available_slots = [slot for slot in all_slots if slot not in occupied_slots]
        return available_slots
    except:
        return all_slots

def send_confirmation(to_email, naam, datum, tijd):
    try:
        subject = "Bevestiging Afspraak - Dienst Grondzaken Wanica"
        body = f"Beste {naam},\n\nUw afspraak op {datum} om {tijd} uur is succesvol vastgelegd.\n\nMet vriendelijke groet,\nDienst Grondzaken Wanica"
        msg = MIMEMultipart(); msg['From'] = GMAIL_USER; msg['To'] = to_email; msg['Subject'] = subject
        msg.attach(MIMEText(body, 'plain'))
        server = smtplib.SMTP('smtp.gmail.com', 587); server.starttls()
        server.login(GMAIL_USER, GMAIL_PASSWORD); server.send_message(msg); server.quit()
    except: pass

# --- 5. CLIËNT REGISTRATIE ---
if page == "Cliënt Registratie":
    st.title("📝 Portaal: Dienst Grondzaken Wanica")
    st.subheader("Registratieformulier")

    with st.form("registratie_form"):
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
        
        st.write("---")
        st.write("### Plan uw afspraak (Maandag & Woensdag)")
        
        c1, c2 = st.columns(2)
        with c1:
            afspraak_datum = st.date_input("Kies een datum", min_value=datetime.today())
            datum_str = str(afspraak_datum)
        
        # Controle op dag van de week (0=Maandag, 2=Woensdag)
        dag_nr = afspraak_datum.weekday()
        
        with c2:
            if dag_nr in [0, 2]:
                beschikbare_tijden = get_available_slots(datum_str)
                if beschikbare_tijden:
                    gekozen_tijd = st.selectbox("Beschikbare tijden (15 min)", beschikbare_tijden)
                else:
                    st.error("Helaas, deze dag zit helemaal vol.")
                    gekozen_tijd = None
            else:
                st.warning("⚠️ Kies een maandag of woensdag.")
                gekozen_tijd = None

        submit = st.form_submit_button("Verzenden")

    if submit:
        if dag_nr not in [0, 2]:
            st.error("Selecteer een geldige dag (Maandag of Woensdag).")
        elif not gekozen_tijd:
            st.error("Kies een beschikbare tijd.")
        elif voornaam and achternaam and email:
            data = {
                "voornaam": voornaam, "achternaam": achternaam, "email": email, 
                "id_nummer": id_nummer, "bericht": bericht,
                "afspraak_datum": datum_str, "afspraak_tijd": gekozen_tijd
            }
            try:
                supabase.table("aanvragen").insert(data).execute()
                send_confirmation(email, voornaam, datum_str, gekozen_tijd)
                st.success(f"✅ Afspraak bevestigd op {datum_str} om {gekozen_tijd}!")
            except Exception as e:
                st.error(f"Fout bij opslaan: {e}")
        else:
            st.error("Vul alle verplichte velden in.")

elif page == "Medewerker Login":
    st.title("🔐 Medewerker Login")
    st.text_input("Gebruikersnaam")
    st.text_input("Wachtwoord", type="password")
    st.button("Login")

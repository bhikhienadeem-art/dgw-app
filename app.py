import streamlit as st
from supabase import create_client, Client
import smtplib
from email.mime.text import MIMEText
from email.mime.multipart import MIMEMultipart
import datetime
import pandas as pd

# 1. Pagina Configuratie & Styling (Groen/Wit)
st.set_page_config(page_title="Dienst Grondzaken Wanica", page_icon="📝", layout="wide")

st.markdown("""
    <style>
    .main { background-color: #ffffff; }
    .stButton>button { background-color: #2e7d32; color: white; border-radius: 5px; width: 100%; }
    .sidebar .sidebar-content { background-color: #f1f8e9; }
    h1, h2, h3 { color: #1b5e20; font-family: 'Arial'; }
    </style>
    """, unsafe_allow_html=True)

# 2. Database Verbinding met Secrets
try:
    URL = st.secrets["SUPABASE_URL"]
    KEY = st.secrets["SUPABASE_KEY"]
    supabase: Client = create_client(URL, KEY)
except:
    st.error("Configuratie fout. Controleer je Streamlit Secrets.")
    st.stop()

# 3. E-mail Functie
def stuur_mail(data):
    try:
        GMAIL_USER = st.secrets["GMAIL_USER"]
        GMAIL_PASSWORD = st.secrets["GMAIL_PASSWORD"]
        MEDEWERKER = "wanicacentrum.gz@gmail.com"
        msg = MIMEMultipart()
        msg['From'] = GMAIL_USER
        msg['To'] = f"{data['email']}, {MEDEWERKER}"
        msg['Subject'] = f"Nieuwe Registratie: {data['voornaam']} {data['achternaam']}"
        inhoud = f"Naam: {data['voornaam']} {data['achternaam']}\nID: {data['id_nummer']}\nAfspraak: {data['afspraak_datum']} om {data['afspraak_tijd']}"
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
        col_d, col_t = st.columns(2)
        with col_d:
            datum = st.date_input("Kies een datum", min_value=datetime.date.today())
        with col_t:
            tijd = st.selectbox("Tijd", ["07:00", "07:15", "07:30", "07:45", "08:00"])
        submit = st.form_submit_button("Verzenden")

    if submit:
        if vnaam and anaam and email and id_nr:
            # Afspraken op Maandag of Woensdag
            if datum.weekday() in [0, 2]:
                form_data = {
                    "voornaam": vnaam, "achternaam": anaam, "id_nummer": id_nr,
                    "lad_nummer": lad_nr, "telefoon": tel, "woonadres": adres,
                    "email": email, "bericht": bericht, 
                    "afspraak_datum": str(datum), "afspraak_tijd": tijd
                }
                try:
                    supabase.table("aanvragen").insert(form_data).execute()
                    stuur_mail(form_data)
                    st.success(f"✅ Bedankt {vnaam}! Uw aanvraag is verwerkt.")
                except Exception as e:
                    st.error(f"Database fout: {e}")
            else:
                st.error("⚠️ Afspraken kunnen alleen op Maandag of Woensdag.")
        else:
            st.warning("Vul alle verplichte velden in.")

elif keuze == "Medewerker Login":
    st.markdown("# 🔐 Medewerker Login")
    user_input = st.text_input("Gebruikersnaam")
    pass_input = st.text_input("Wachtwoord", type="password")
    
    # Inlogcontrole
    if st.button("Inloggen"):
        if user_input == "ICT Wanica" and pass_input == "l3lyd@rp":
            st.session_state["ingelogd"] = True
            st.rerun()
        else:
            st.error("Onjuiste inloggegevens.")

    if st.session_state.get("ingelogd"):
        st.success("Welkom terug, ICT Wanica!")
        st.subheader("Overzicht Aanvragen")
        try:
            response = supabase.table("aanvragen").select("*").execute()
            if response.data:
                st.dataframe(pd.DataFrame(response.data), use_container_width=True)
        except Exception as e:
            st.error(f"Fout bij ophalen data: {e}")
        if st.button("Uitloggen"):
            st.session_state["ingelogd"] = False
            st.rerun()

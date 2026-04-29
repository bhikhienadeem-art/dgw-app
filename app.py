import streamlit as st
from supabase import create_client, Client
import smtplib
from email.mime.text import MIMEText
from email.mime.multipart import MIMEMultipart
import datetime
import pandas as pd

# 1. Pagina Configuratie & Styling (Groen/Wit)
st.set_page_config(page_title="DGW Wanica Portaal", page_icon="📝", layout="wide")

st.markdown("""
    <style>
    .main { background-color: #ffffff; }
    .stButton>button { background-color: #2e7d32 !important; color: white !important; border-radius: 5px; width: 100%; }
    .sidebar .sidebar-content { background-color: #f1f8e9; }
    h1, h2, h3 { color: #1b5e20; font-family: 'Arial'; }
    </style>
    """, unsafe_allow_html=True)

# 2. Database Verbinding
try:
    URL = st.secrets["SUPABASE_URL"]
    KEY = st.secrets["SUPABASE_KEY"]
    supabase: Client = create_client(URL, KEY)
except:
    st.error("Check uw Streamlit Secrets!")
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
        msg['Subject'] = f"Registratie DGW: {data['voornaam']} {data['achternaam']}"
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

# 4. Navigatie
st.sidebar.markdown("<h2 style='color: #2e7d32;'>DGW Menu</h2>", unsafe_allow_html=True)
keuze = st.sidebar.radio("Navigatie:", ["Cliënt Registratie", "Medewerker Portaal"])

if keuze == "Cliënt Registratie":
    st.title("📝 Registratie: Dienst Grondzaken Wanica")
    with st.form("aanvraag_form", clear_on_submit=True):
        c1, c2 = st.columns(2)
        with c1:
            vnaam = st.text_input("Voornaam")
            id_nr = st.text_input("ID-Nummer")
            tel = st.text_input("Telefoon")
        with c2:
            anaam = st.text_input("Achternaam")
            lad_nr = st.text_input("LAD Nummer")
            email = st.text_input("E-mail")
        adres = st.text_input("Woonadres")
        bericht = st.text_area("Bericht / Klacht")
        
        st.write("---")
        cd, ct = st.columns(2)
        with cd:
            datum = st.date_input("Kies datum", min_value=datetime.date.today())
        with ct:
            tijd = st.selectbox("Tijd", ["07:00", "07:30", "08:00", "08:30"])
        
        submit = st.form_submit_button("Gegevens Versturen")

    if submit:
        if vnaam and anaam and id_nr:
            if datum.weekday() in [0, 2]: # Maandag of Woensdag
                form_data = {
                    "voornaam": vnaam, "achternaam": anaam, "id_nummer": id_nr,
                    "lad_nummer": lad_nr, "telefoon": tel, "woonadres": adres,
                    "email": email, "bericht": bericht, 
                    "afspraak_datum": str(datum), "afspraak_tijd": tijd
                }
                try:
                    supabase.table("aanvragen").insert(form_data).execute()
                    stuur_mail(form_data)
                    st.success(f"Bedankt {vnaam}! Alles is correct opgeslagen.")
                except Exception as e:
                    st.error(f"Fout: {e}")
            else:
                st.error("Afspraken kunnen alleen op Maandag en Woensdag.")
        else:
            st.warning("Vul a.u.b. alle velden in.")

elif keuze == "Medewerker Portaal":
    st.title("🔐 Login Medewerker")
    
    # Inlog velden
    u = st.text_input("Gebruikersnaam").strip()
    p = st.text_input("Wachtwoord", type="password").strip()
    
    if st.button("Inloggen"):
        # Directe check op inloggegevens
        if u == "ICT Wanica" and p == "l3lyd@rp":
            st.session_state["logged_in"] = True
            st.success("Succesvol ingelogd!")
        else:
            st.error("Onjuiste inloggegevens.")

    # Toon data als ingelogd
    if st.session_state.get("logged_in"):
        st.write("---")
        st.subheader("Ingekomen Aanvragen")
        try:
            res = supabase.table("aanvragen").select("*").execute()
            if res.data:
                df = pd.DataFrame(res.data)
                st.dataframe(df, use_container_width=True)
        except Exception as e:
            st.error(f"Fout bij laden: {e}")
            
        if st.button("Uitloggen"):
            st.session_state["logged_in"] = False
            st.rerun()

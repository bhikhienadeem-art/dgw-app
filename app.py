import streamlit as st
from supabase import create_client, Client
import smtplib
from email.mime.text import MIMEText
from email.mime.multipart import MIMEMultipart
import datetime
import pandas as pd

# 1. Pagina Configuratie & Styling
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

# 3. E-mail Functies
def stuur_bevestigings_mail(data):
    """Mail naar klant bij eerste registratie"""
    try:
        GMAIL_USER = st.secrets["GMAIL_USER"]
        GMAIL_PASSWORD = st.secrets["GMAIL_PASSWORD"]
        msg = MIMEMultipart()
        msg['From'] = GMAIL_USER
        msg['To'] = data['email']
        msg['Subject'] = "Ontvangstbevestiging DGW Wanica"
        inhoud = f"Beste {data['voornaam']},\n\nUw aanvraag is ontvangen en is momenteel: In behandeling.\nAfspraak: {data['afspraak_datum']} om {data['afspraak_tijd']}."
        msg.attach(MIMEText(inhoud, 'plain'))
        server = smtplib.SMTP('smtp.gmail.com', 587)
        server.starttls()
        server.login(GMAIL_USER, GMAIL_PASSWORD)
        server.sendmail(GMAIL_USER, data['email'], msg.as_string())
        server.quit()
    except: pass

def stuur_status_update_mail(data):
    """Mail naar klant wanneer medewerker status of tijd wijzigt"""
    try:
        GMAIL_USER = st.secrets["GMAIL_USER"]
        GMAIL_PASSWORD = st.secrets["GMAIL_PASSWORD"]
        msg = MIMEMultipart()
        msg['From'] = GMAIL_USER
        msg['To'] = data['email']
        msg['Subject'] = f"Update uw aanvraag DGW: {data['status']}"
        inhoud = f"Beste {data['voornaam']},\n\nDe status van uw aanvraag is gewijzigd naar: {data['status']}.\nNieuwe afspraaktijd: {data['afspraak_datum']} om {data['afspraak_tijd']}."
        msg.attach(MIMEText(inhoud, 'plain'))
        server = smtplib.SMTP('smtp.gmail.com', 587)
        server.starttls()
        server.login(GMAIL_USER, GMAIL_PASSWORD)
        server.sendmail(GMAIL_USER, data['email'], msg.as_string())
        server.quit()
    except: pass

# 4. Navigatie & Login Status
if "logged_in" not in st.session_state:
    st.session_state["logged_in"] = False

st.sidebar.markdown("<h2 style='color: #2e7d32;'>DGW Menu</h2>", unsafe_allow_html=True)
keuze = st.sidebar.radio("Navigatie:", ["Cliënt Registratie", "Medewerker Portaal"])

# --- CLIENT REGISTRATIE ---
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
        cd, ct = st.columns(2)
        with cd:
            datum = st.date_input("Kies datum (Ma of Wo)", min_value=datetime.date.today())
        with ct:
            tijd = st.selectbox("Tijd", ["07:00", "07:30", "08:00", "08:30"])
        submit = st.form_submit_button("Verzenden")

    if submit:
        if vnaam and anaam and id_nr:
            if datum.weekday() in [0, 2]: # Maandag=0, Woensdag=2
                form_data = {
                    "voornaam": vnaam, "achternaam": anaam, "id_nummer": id_nr,
                    "lad_nummer": lad_nr, "telefoon": tel, "woonadres": adres,
                    "email": email, "bericht": bericht, 
                    "afspraak_datum": str(datum), "afspraak_tijd": tijd,
                    "status": "In behandeling"
                }
                try:
                    supabase.table("aanvragen").insert(form_data).execute()
                    stuur_bevestigings_mail(form_data)
                    st.success(f"Bedankt {vnaam}! Uw aanvraag is opgeslagen.")
                except Exception as e:
                    st.error(f"Fout: {e}")
            else:
                st.error("Afspraken zijn alleen mogelijk op Maandag en Woensdag.")

# --- MEDEWERKER PORTAAL ---
elif keuze == "Medewerker Portaal":
    if not st.session_state["logged_in"]:
        st.title("🔐 Login Medewerker")
        with st.form("login_form"):
            u = st.text_input("Gebruikersnaam")
            p = st.text_input("Wachtwoord", type="password")
            if st.form_submit_button("Inloggen"):
                if u.strip() == "ICT Wanica" and p.strip() == "l3lyd@rp":
                    st.session_state["logged_in"] = True
                    st.rerun()
                else:
                    st.error("Onjuiste inloggegevens.")
    else:
        st.title("📂 Beheerders Dashboard")
        tab1, tab2 = st.tabs(["📋 Aanvragen Beheren", "📅 Kalender Overzicht"])

        with tab1:
            try:
                res = supabase.table("aanvragen").select("*").execute()
                if res.data:
                    df = pd.DataFrame(res.data)
                    
                    st.subheader("Wijzig Status of Afspraak")
                    sel_id = st.selectbox("Selecteer ID van aanvraag:", df['id'].tolist())
                    row = df[df['id'] == sel_id].iloc[0]

                    col1, col2, col3 = st.columns(3)
                    with col1:
                        n_status = st.selectbox("Nieuwe Status", ["In behandeling", "Bevestigd", "Geannuleerd"], index=0)
                    with col2:
                        n_datum = st.date_input("Nieuwe Datum", value=pd.to_datetime(row['afspraak_datum']))
                    with col3:
                        n_tijd = st.selectbox("Nieuwe Tijd", ["07:00", "07:30", "08:00", "08:30"])

                    if st.button("Update & Mail Klant"):
                        up_data = {"status": n_status, "afspraak_datum": str(n_datum), "afspraak_tijd": n_tijd}
                        supabase.table("aanvragen").update(up_data).eq("id", sel_id).execute()
                        
                        # Mail data samenstellen
                        mail_info = {"email": row['email'], "voornaam": row['voornaam'], "status": n_status, "afspraak_datum": str(n_datum), "afspraak_tijd": n_tijd}
                        stuur_status_update_mail(mail_info)
                        st.success("Aanvraag bijgewerkt en mail verzonden!")
                        st.rerun()

                    st.write("---")
                    st.dataframe(df, use_container_width=True)
            except Exception as e:
                st.error(f"Fout: {e}")

        with tab2:
            st.subheader("📅 Geplande Afspraken")
            if not df.empty:
                # Toon alleen relevante info in de kalender-lijst
                cal_df = df[['afspraak_datum', 'afspraak_tijd', 'voornaam', 'achternaam', 'status']]
                cal_df = cal_df.sort_values(by=['afspraak_datum', 'afspraak_tijd'])
                st.table(cal_df)

        if st.sidebar.button("Uitloggen"):
            st.session_state["logged_in"] = False
            st.rerun()

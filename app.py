import streamlit as st
import sqlite3
import os
import hashlib
import pandas as pd
import base64
import smtplib
from email.mime.text import MIMEText
from email.mime.multipart import MIMEMultipart

# --- 1. CONFIGURATIE & INSTELLINGEN ---
st.set_page_config(
    page_title="Aanvraag Goedgedrag - Districtscommissariaat Wanica Centrum",
    page_icon="📜",
    layout="wide"
)

EMAIL_USER = "ggdaanvraag@gmail.com"
EMAIL_PASS = "fzne mpao hdqd lwcr"

# Initialize Database & Tables
def init_db():
    conn = sqlite3.connect('wanica.db')
    cursor = conn.cursor()
    cursor.execute('''
        CREATE TABLE IF NOT EXISTS applications (
            id INTEGER PRIMARY KEY AUTOINCREMENT,
            full_name TEXT,
            id_number TEXT,
            phone_number TEXT,
            email TEXT,
            uitreksel_file TEXT,
            pasfoto_file TEXT,
            id_kaart_file TEXT,
            bankbewijs_file TEXT,
            status TEXT DEFAULT 'In behandeling',
            created_at TIMESTAMP DEFAULT CURRENT_TIMESTAMP
        )
    ''')
    cursor.execute('''
        CREATE TABLE IF NOT EXISTS staff (
            id INTEGER PRIMARY KEY AUTOINCREMENT,
            username TEXT UNIQUE,
            password TEXT,
            created_at TIMESTAMP DEFAULT CURRENT_TIMESTAMP
        )
    ''')
    cursor.execute("INSERT OR IGNORE INTO staff (username, password) VALUES (?, ?)", ("admin", "admin@123"))
    conn.commit()
    conn.close()

init_db()

# Uploads Directory
UPLOAD_DIR = "uploads"
if not os.path.exists(UPLOAD_DIR):
    os.makedirs(UPLOAD_DIR)

def save_file(uploaded_file):
    if uploaded_file is not None:
        new_name = f"{hashlib.md5(uploaded_file.name.encode()).hexdigest()}_{uploaded_file.name}"
        path = os.path.join(UPLOAD_DIR, new_name)
        with open(path, "wb") as f:
            f.write(uploaded_file.getbuffer())
        return new_name
    return None

# --- 2. EMAIL FUNCTIE (SMTP) ---
def stuur_mail(ontvanger, onderwerp, inhoud):
    msg = MIMEMultipart()
    msg['From'] = f"Districtscommissariaat Wanica Centrum <{EMAIL_USER}>"
    msg['To'] = ontvanger
    msg['Subject'] = onderwerp
    
    html_inhoud = f"<html><body style='font-family: Arial; font-size: 14px; color: black;'>{inhoud.replace(chr(10), '<br>')}</body></html>"
    msg.attach(MIMEText(html_inhoud, 'html'))
    
    try:
        server = smtplib.SMTP('smtp.gmail.com', 587)
        server.starttls()
        server.login(EMAIL_USER, EMAIL_PASS.replace(" ", ""))
        server.send_message(msg)
        server.quit()
        return True
    except Exception as e: 
        print(f"Fout bij verzenden: {e}")
        return False

# --- 3. CUSTOM CSS ---
def add_custom_css():
    bg_image_path = "achtergrond.jpg"
    bg_css = ""
    if os.path.exists(bg_image_path):
        with open(bg_image_path, "rb") as f:
            encoded_bg = base64.b64encode(f.read()).decode()
        bg_css = f"""
            background: linear-gradient(rgba(0, 0, 0, 0.65), rgba(0, 0, 0, 0.65)), url("data:image/jpg;base64,{encoded_bg}") no-repeat center center fixed;
            background-size: cover;
        """

    st.markdown(f"""
    <style>
        @import url('https://fonts.googleapis.com/css2?family=Plus+Jakarta+Sans:wght@400;600;700;800&display=swap');

        html, body, [class*="css"], .stApp {{
            font-family: 'Plus Jakarta Sans', sans-serif !important;
            {bg_css}
        }}
        
        [data-testid="stSidebar"] {{
            background-color: #f8fafc !important;
            border-right: 2px solid #cbd5e1 !important;
        }}
        [data-testid="stSidebar"] p, [data-testid="stSidebar"] span, [data-testid="stSidebar"] label, [data-testid="stSidebar"] div {{
            color: #0f172a !important;
            font-weight: 700 !important;
        }}

        .custom-header {{
            background: linear-gradient(135deg, #1b5e20 0%, #2e7d32 100%);
            border-bottom: 6px solid #144517;
            padding: 28px 35px;
            border-radius: 16px;
            color: #ffffff;
            display: flex;
            justify-content: space-between;
            align-items: center;
            margin-bottom: 25px;
            box-shadow: 0 10px 30px rgba(0,0,0,0.45);
            flex-wrap: wrap;
            gap: 25px;
        }}
        .header-brand {{
            display: flex;
            align-items: center;
            gap: 24px;
        }}
        .header-title h1 {{
            margin: 0;
            font-size: 28px;
            color: #ffffff !important;
            font-weight: 800;
        }}
        .header-contact {{
            font-size: 16px;
            text-align: right;
            line-height: 1.8;
            background: rgba(255, 255, 255, 0.18);
            padding: 14px 22px;
            border-radius: 12px;
            color: #ffffff !important;
            border: 1.5px solid rgba(255, 255, 255, 0.35);
            font-weight: 600;
        }}

        div[data-testid="stForm"] {{
            background-color: #ffffff !important;
            padding: 40px !important;
            border-radius: 16px !important;
            box-shadow: 0 15px 40px rgba(0,0,0,0.5) !important;
            border: 1px solid #cbd5e1 !important;
        }}
        
        .section-header {{
            background-color: #e8f5e9;
            border-left: 6px solid #2e7d32;
            padding: 12px 18px;
            font-size: 16px;
            font-weight: 800;
            color: #1b5e20 !important;
            border-radius: 0 8px 8px 0;
            margin: 25px 0 18px 0;
        }}

        div[data-testid="stForm"] label, label, div[data-testid="stWidgetLabel"] p {{
            color: #0f172a !important;
            font-weight: 700 !important;
            font-size: 15px !important;
        }}

        .stTextInput input {{
            background-color: #ffffff !important;
            color: #0f172a !important;
            border: 2px solid #64748b !important;
            border-radius: 8px !important;
            padding: 12px 15px !important;
        }}

        [data-testid="stFileUploader"] {{
            background-color: #f8fafc !important;
            border: 2px dashed #cbd5e1 !important;
            border-radius: 12px !important;
            padding: 16px !important;
        }}

        div.stButton > button, div[data-testid="stFormSubmitButton"] > button {{
            background-color: #1b5e20 !important;
            color: #ffffff !important;
            font-weight: 800 !important;
            font-size: 18px !important;
            padding: 16px 30px !important;
            border-radius: 10px !important;
            border: none !important;
            width: 100% !important;
        }}
    </style>
    """, unsafe_allow_html=True)

add_custom_css()

# --- 4. HEADER ---
logo_path = "logo.png"
logo_html = ""

if os.path.exists(logo_path):
    with open(logo_path, "rb") as f:
        encoded_logo = base64.b64encode(f.read()).decode()
    logo_html = f'<img src="data:image/png;base64,{encoded_logo}" style="height: 135px; width: auto; background: #ffffff; padding: 8px; border-radius: 14px;">'

st.markdown(f"""
<div class="custom-header">
    <div class="header-brand">
        {logo_html}
        <div class="header-title">
            <h1>Districtscommissariaat Wanica Centrum</h1>
            <p style="margin: 6px 0 0 0; color: #e2e8f0;">Online Diensten Portaal</p>
        </div>
    </div>
    <div class="header-contact">
        📍 <b>Adres:</b> Tawajarieweg No. 20<br>
        📞 <b>Tel:</b> +597-366660 / +597-366929 / +597-366939
    </div>
</div>
""", unsafe_allow_html=True)

menu = st.sidebar.radio("Navigatie Menu", ["Aanvraag Indienen (Burgers)", "Medewerkers Login / Dashboard"])

# ---------------------------------------------------------
# BURGERS FORMULIER (VOLAUTOMATISCH)
# ---------------------------------------------------------
if menu == "Aanvraag Indienen (Burgers)":
    
    st.markdown("""
    <div style="background-color: rgba(255, 255, 255, 0.95); padding: 20px 25px; border-radius: 14px; margin-bottom: 25px; border-left: 6px solid #1b5e20;">
        <h3 style="color: #1b5e20; margin-top: 0; font-weight: 800; font-size: 18px;">Welkom bij het Online Aanvraagportaal</h3>
        <p style="color: #0f172a; font-size: 14.5px; margin-bottom: 0;">
            Via dit portaal kunt u eenvoudig uw <b>Verklaring Omtrent het Gedrag (Goedgedrag)</b> aanvragen. Vul het formulier in en upload de gevraagde documenten.
        </p>
    </div>
    """, unsafe_allow_html=True)

    with st.form("public_form", clear_on_submit=True):
        st.markdown('<div class="section-header">👤 Stap 1: Persoonsgegevens</div>', unsafe_allow_html=True)
        col1, col2 = st.columns(2)
        with col1:
            full_name = st.text_input("Volledige Naam *", placeholder="Voer uw voor- en achternaam in")
            id_number = st.text_input("ID / Paspoortnummer *", placeholder="Bijv. FD000784")
        with col2:
            phone_number = st.text_input("Telefoonnummer *", placeholder="Bijv. +597 8706661")
            email = st.text_input("E-mailadres *", placeholder="naam@domein.sr")

        st.markdown('<div class="section-header">📁 Stap 2: Benodigde Documenten Uploaden</div>', unsafe_allow_html=True)
        col3, col4 = st.columns(2)
        with col3:
            uitreksel = st.file_uploader("Uitreksel (PDF/Afbeelding) *", type=['pdf', 'jpg', 'jpeg', 'png'])
            pasfoto = st.file_uploader("Pasfoto *", type=['jpg', 'jpeg', 'png'])
        with col4:
            id_kaart = st.file_uploader("Kopie Geldig ID-kaart *", type=['pdf', 'jpg', 'jpeg', 'png'])
            bankbewijs = st.file_uploader("Bewijs van Bankovermaking *", type=['pdf', 'jpg', 'jpeg', 'png'])

        st.markdown("<br>", unsafe_allow_html=True)
        submitted = st.form_submit_button("🚀 Aanvraag Definitief Indienen")

        if submitted:
            if not (full_name and id_number and phone_number and email and uitreksel and pasfoto and id_kaart and bankbewijs):
                st.error("⚠️ Vul alstublieft alle verplichte velden in en upload alle 4 documenten.")
            else:
                # 1. Bestanden opslaan
                u_name = save_file(uitreksel)
                p_name = save_file(pasfoto)
                i_name = save_file(id_kaart)
                b_name = save_file(bankbewijs)

                # 2. Opslaan in database
                conn = sqlite3.connect('wanica.db')
                cursor = conn.cursor()
                cursor.execute('''
                    INSERT INTO applications (full_name, id_number, phone_number, email, uitreksel_file, pasfoto_file, id_kaart_file, bankbewijs_file)
                    VALUES (?, ?, ?, ?, ?, ?, ?, ?)
                ''', (full_name, id_number, phone_number, email, u_name, p_name, i_name, b_name))
                app_id = cursor.lastrowid
                conn.commit()
                conn.close()

                # 3A. E-mail naar de BURGER (Bevestiging)
                burger_onderwerp = "Bevestiging Aanvraag Verklaring Omtrent het Gedrag - Wanica Centrum"
                burger_inhoud = f"""
                Beste {full_name},<br><br>
                Hartelijk dank voor uw aanvraag voor een <b>Verklaring Omtrent het Gedrag (Goedgedrag)</b> bij het Districtscommissariaat Wanica Centrum.<br><br>
                Wij hebben uw aanvraag (Dossier #{app_id}) en uw documenten in goede orde ontvangen en in behandeling genomen.<br>
                Zodra uw aanvraag is beoordeeld, nemen wij contact met u op via dit e-mailadres of via uw telefoonnummer ({phone_number}).<br><br>
                Met vriendelijke groet,<br>
                <b>Districtscommissariaat Wanica Centrum</b><br>
                Adres: Tawajarieweg No. 20 | Tel: +597-366660
                """

                # 3B. E-mail naar de MEDEWERKER (Notificatie)
                medewerker_onderwerp = f"🚨 Nieuwe Goedgedrag Aanvraag #{app_id} - {full_name}"
                medewerker_inhoud = f"""
                <h3>Er is een nieuwe Goedgedrag aanvraag binnengekomen:</h3>
                <br>
                <b>GEGEVENS APPLICANT:</b><br>
                - <b>Aanvraag ID:</b> #{app_id}<br>
                - <b>Volledige Naam:</b> {full_name}<br>
                - <b>ID-nummer:</b> {id_number}<br>
                - <b>Telefoonnummer:</b> {phone_number}<br>
                - <b>E-mailadres:</b> {email}<br>
                <br>
                <b>GEÜPLOADE BESTANDEN:</b><br>
                - Uitreksel: {u_name}<br>
                - Pasfoto: {p_name}<br>
                - ID-kaart: {i_name}<br>
                - Bankbewijs: {b_name}<br>
                <br>
                <i>Log in op het Medewerkersdashboard om de documenten te bekijken/downloaden en de status bij te werken.</i>
                """

                with st.spinner("Aanvraag opslaan en automatische e-mails verzenden..."):
                    # Verstuur naar de burger
                    stuur_mail(email, burger_onderwerp, burger_inhoud)
                    # Verstuur naar de medewerker
                    stuur_mail(EMAIL_USER, medewerker_onderwerp, medewerker_inhoud)

                st.session_state['last_submission'] = {
                    "full_name": full_name,
                    "email": email,
                    "phone_number": phone_number,
                    "app_id": app_id
                }
                st.rerun()

    if 'last_submission' in st.session_state:
        sub = st.session_state['last_submission']
        st.success("✅ Uw aanvraag is succesvol ingediend!")
        
        st.markdown(f"""
        <div style="background-color: #ffffff; border: 3px solid #2e7d32; padding: 25px; border-radius: 14px; color: #0f172a; margin-top: 20px; box-shadow: 0 10px 30px rgba(0,0,0,0.3);">
            <h3 style="color: #1b5e20; margin-top: 0;">✉️ Aanvraag Geregistreerd & Bevestigingsmail Verzonden</h3>
            <p>Beste <b>{sub['full_name']}</b>,</p>
            <p>Hartelijk dank voor uw aanvraag voor een <b>Verklaring Omtrent het Gedrag (Goedgedrag)</b> bij het Districtscommissariaat Wanica Centrum (Dossier #{sub['app_id']}).</p>
            <p>Er is automatisch een bevestigingsmail verzonden naar uw inbox op <b>{sub['email']}</b>. Zodra uw aanvraag is beoordeeld, nemen wij contact met u op via dit e-mailadres of via uw telefoonnummer ({sub['phone_number']}).</p>
            <hr style="border: 0; border-top: 1px solid #cbd5e1; margin: 15px 0;">
            <p style="margin-bottom: 0; font-size: 14px; color: #475569;">
                <b>Districtscommissariaat Wanica Centrum</b><br>
                Adres: Tawajarieweg No. 20 | Tel: +597-366660 / +597-366929
            </p>
        </div>
        """, unsafe_allow_html=True)
        if st.button("Nieuwe aanvraag indienen"):
            del st.session_state['last_submission']
            st.rerun()

# ---------------------------------------------------------
# MEDEWERKERS DASHBOARD
# ---------------------------------------------------------
else:
    st.markdown("<h2 style='color: #ffffff; font-weight: 800;'>🔒 Medewerkers Portaal Dashboard</h2>", unsafe_allow_html=True)

    if 'logged_in' not in st.session_state:
        st.session_state['logged_in'] = False
        st.session_state['username'] = ""

    if not st.session_state['logged_in']:
        with st.form("login_form"):
            st.markdown('<div class="section-header">Inloggen met Beheerders- of Medewerkersaccount</div>', unsafe_allow_html=True)
            user_input = st.text_input("Gebruikersnaam", placeholder="Voer gebruikersnaam in")
            pwd_input = st.text_input("Wachtwoord", type="password", placeholder="Voer wachtwoord in")
            login_submitted = st.form_submit_button("🔑 Inloggen")
            
            if login_submitted:
                if user_input == "admin" and pwd_input == "admin@123":
                    st.session_state['logged_in'] = True
                    st.session_state['username'] = "admin"
                    st.rerun()
                else:
                    conn = sqlite3.connect('wanica.db')
                    cursor = conn.cursor()
                    cursor.execute("SELECT * FROM staff WHERE username = ? AND password = ?", (user_input, pwd_input))
                    staff_member = cursor.fetchone()
                    conn.close()
                    
                    if staff_member:
                        st.session_state['logged_in'] = True
                        st.session_state['username'] = user_input
                        st.rerun()
                    else:
                        st.error("❌ Ongeldige gebruikersnaam of wachtwoord.")
    else:
        col_user, col_logout = st.columns([4, 1])
        with col_user:
            st.markdown(f"<h3 style='color: #ffffff; margin-top: 10px;'>👋 Ingelogd als: <b>{st.session_state['username']}</b></h3>", unsafe_allow_html=True)
        with col_logout:
            if st.button("🚪 Uitloggen", use_container_width=True):
                st.session_state['logged_in'] = False
                st.session_state['username'] = ""
                st.rerun()

        st.divider()

        conn = sqlite3.connect('wanica.db')
        df = pd.read_sql_query("SELECT id, full_name, id_number, phone_number, email, status, created_at FROM applications ORDER BY id DESC", conn)
        conn.close()

        st.markdown("<h3 style='color: #ffffff;'>📋 Binnengekomen Aanvragen</h3>", unsafe_allow_html=True)
        if not df.empty:
            st.dataframe(df, use_container_width=True)
        else:
            st.info("Geen aanvragen gevonden.")

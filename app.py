import streamlit as st
from supabase import create_client, Client
import datetime
import pandas as pd
import smtplib
from email.mime.text import MIMEText
from email.mime.multipart import MIMEMultipart
from email.mime.application import MIMEApplication
import urllib.parse

# --- 1. CONFIGURATIE & STYLING ---
st.set_page_config(page_title="DGW Wanica Portaal", layout="wide")

try:
    st.sidebar.image("orgineel logo Centrum.png", use_container_width=True)
except:
    st.sidebar.warning("Logo bestand niet gevonden.")

st.markdown("""
    <style>
    .status-card { padding: 15px; border-radius: 10px; border-left: 5px solid #2e7d32; background-color: #f9f9f9; margin-bottom: 10px; border: 1px solid #ddd; }
    .stButton>button { background-color: #2e7d32 !important; color: white !important; }
    </style>
    """, unsafe_allow_html=True)

# Verbinding met Supabase
supabase = create_client(st.secrets["SUPABASE_URL"], st.secrets["SUPABASE_KEY"])

# --- PROFESSIONELE MAIL FUNCTIE ---
def stuur_mail(ontvanger, onderwerp, inhoud):
    try:
        msg = MIMEMultipart()
        msg['Subject'] = onderwerp
        msg['From'] = f"DGW Wanica <{st.secrets['EMAIL_USER']}>"
        msg['To'] = ontvanger
        
        body = f"""
Geachte cliënt,

{inhoud}

Mocht u nog vragen hebben, dan kunt u contact opnemen met ons kantoor.

Met vriendelijke groet,

Districtscommissariaat Wanica Centrum
Afdeling Grondzaken (DGW)
Lelydorp, Suriname
        """
        msg.attach(MIMEText(body, 'plain'))

        with smtplib.SMTP_SSL('smtp.gmail.com', 465) as server:
            server.login(st.secrets["EMAIL_USER"], st.secrets["EMAIL_PASS"])
            server.send_message(msg)
    except Exception as e:
        st.error(f"Mailfout: {e}")

# --- 2. LOGIN ---
if 'logged_in' not in st.session_state:
    st.session_state.logged_in, st.session_state.role, st.session_state.user = False, None, None

def login():
    st.sidebar.subheader("🔐 Inloggen")
    res = supabase.table("medewerkers").select("*").execute()
    user_list = [u['gebruikersnaam'] for u in res.data] if res.data else []
    selected_user = st.sidebar.selectbox("Gebruiker", ["--- Kies ---"] + user_list)
    password = st.sidebar.text_input("Wachtwoord", type="password")
    if st.sidebar.button("Inloggen"):
        user_data = next((u for u in res.data if u['gebruikersnaam'] == selected_user), None)
        if user_data and user_data['wachtwoord'] == password:
            st.session_state.logged_in, st.session_state.role, st.session_state.user = True, user_data['rol'], selected_user
            st.rerun()

# --- 3. NAVIGATIE ---
menu_options = ["Cliënt Registratie"]
if st.session_state.logged_in:
    menu_options += ["Medewerker Portaal", "Agenda Overzicht", "Rapportages"]
    if str(st.session_state.role).lower() == "admin": menu_options.append("Admin Instellingen")
    
    # QR Code in sidebar voor medewerker
    app_url = "https://dgw-wanica.streamlit.app/"
    qr_api = f"https://api.qrserver.com/v1/create-qr-code/?size=150x150&data={urllib.parse.quote(app_url)}"
    st.sidebar.write("---")
    st.sidebar.image(qr_api, caption="Scan voor cliënt")
    
    if st.sidebar.button("🚪 Uitloggen"):
        st.session_state.logged_in = False
        st.rerun()
else: login()

menu = st.sidebar.radio("Navigatie", menu_options)

# --- 4. PAGINA'S ---
if menu == "Cliënt Registratie":
    st.header("📝 Nieuwe Aanvraag")
    col1, col2 = st.columns(2)
    with col1:
        vnaam, anaam = st.text_input("Voornaam *"), st.text_input("Achternaam *")
        id_nr, email = st.text_input("ID-Nummer *"), st.text_input("E-mailadres *")
    with col2:
        tel, woonadres = st.text_input("Telefoonnummer *"), st.text_input("Woonadres *")
        lad_nr = st.text_input("LAD Nummer")
    bericht = st.text_area("Omschrijving *")
    datum = st.date_input("Datum", min_value=datetime.date.today())
    
    if datum.weekday() in [0, 2]:
        res = supabase.table("aanvragen").select("afspraak_tijd").eq("afspraak_datum", str(datum)).execute()
        bezet = [r['afspraak_tijd'] for r in res.data] if res.data else []
        tijden = [f"{h:02d}:{m:02d}" for h in range(7, 15) for m in [0, 15, 30, 45]]
        vrije_tijden = [t for t in tijden if t not in bezet and "07:00" <= t <= "14:45"]
        gekozen_tijd = st.selectbox("Tijdstip", ["--- Kies ---"] + vrije_tijden)
        
        if st.button("Verzenden"):
            if all([vnaam, anaam, email, bericht]) and gekozen_tijd != "--- Kies ---":
                supabase.table("aanvragen").insert({"voornaam": vnaam, "achternaam": anaam, "email": email, "afspraak_datum": str(datum), "afspraak_tijd": gekozen_tijd, "status": "In behandeling", "bericht": bericht}).execute()
                stuur_mail(email, "Ontvangstbevestiging DGW", f"Uw aanvraag voor {datum} om {gekozen_tijd} uur is ontvangen en wordt momenteel verwerkt.")
                st.success("✅ Verzonden!")
    else: st.error("Afspraken alleen op Ma/Wo.")

elif menu == "Medewerker Portaal":
    st.header("📋 Beheer Aanvragen")
    res = supabase.table("aanvragen").select("*").order('afspraak_datum').execute()
    if res.data:
        df = pd.DataFrame(res.data)
        st.dataframe(df)
        sel_id = st.selectbox("Selecteer ID", df['id'].tolist())
        
        n_status = st.selectbox("Nieuwe Status", ["Bevestigd", "In behandeling", "Geannuleerd", "Verwezen"])
        toelichting = st.text_area("Toelichting voor mail (optioneel)")
        
        if st.button("Status Bijwerken & Mailen"):
            # Update Database
            supabase.table("aanvragen").update({"status": n_status}).eq("id", sel_id).execute()
            
            # Direct mail sturen met de NIEUWE status
            aanvraag = next(item for item in res.data if item['id'] == sel_id)
            mail_inhoud = f"De status van uw aanvraag (ID: {sel_id}) is bijgewerkt naar: **{n_status}**."
            if toelichting:
                mail_inhoud += f"\n\nExtra informatie van de medewerker:\n{toelichting}"
            
            stuur_mail(aanvraag['email'], f"Status Update: {n_status}", mail_inhoud)
            st.success(f"✅ Status is nu '{n_status}' en mail is verzonden naar {aanvraag['email']}.")
            st.rerun()

elif menu == "Agenda Overzicht":
    st.header("📅 Agenda")
    res = supabase.table("aanvragen").select("*").execute()
    if res.data:
        df = pd.DataFrame(res.data)
        dag = st.date_input("Bekijk datum", value=datetime.date.today())
        dag_data = df[df['afspraak_datum'] == str(dag)].sort_values('afspraak_tijd')
        for _, r in dag_data.iterrows():
            st.markdown(f'<div class="status-card"><b>🕒 {r["afspraak_tijd"]}</b> | {r["voornaam"]} {r["achternaam"]} | <b>Status: {r["status"]}</b></div>', unsafe_allow_html=True)

elif menu == "Rapportages":
    st.header("📊 Statistieken")
    res = supabase.table("aanvragen").select("*").execute()
    if res.data:
        df = pd.DataFrame(res.data)
        st.bar_chart(df['status'].value_counts())
        st.dataframe(df)

elif menu == "Admin Instellingen":
    st.header("⚙️ Admin")
    res_m = supabase.table("medewerkers").select("*").execute()
    df_m = pd.DataFrame(res_m.data)
    st.table(df_m[['gebruikersnaam', 'rol']])
    # Hier kunnen functies voor toevoegen/verwijderen weer staan zoals in de vorige versie

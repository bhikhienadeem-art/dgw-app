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
    .stButton>button { background-color: #2e7d32 !important; color: white !important; height: 45px; }
    </style>
    """, unsafe_allow_html=True)

# Verbinding met Supabase
supabase = create_client(st.secrets["SUPABASE_URL"], st.secrets["SUPABASE_KEY"])

# --- VERBETERDE MAIL FUNCTIE (MET SUPPORT VOOR BIJLAGEN) ---
def stuur_mail(ontvanger, onderwerp, inhoud, bestanden=None):
    try:
        msg = MIMEMultipart()
        msg['Subject'] = onderwerp
        msg['From'] = f"DGW Wanica <{st.secrets['EMAIL_USER']}>"
        msg['To'] = ontvanger
        
        body = f"""Geachte,\n\n{inhoud}\n\nMet vriendelijke groet,\n\nDistrictscommissariaat Wanica Centrum\nAfdeling Grondzaken (DGW)"""
        msg.attach(MIMEText(body, 'plain'))

        if bestanden:
            for f in bestanden:
                f.seek(0)
                bijlage = MIMEApplication(f.read(), Name=f.name)
                bijlage['Content-Disposition'] = f'attachment; filename="{f.name}"'
                msg.attach(bijlage)
                f.seek(0) # Reset voor eventueel volgend gebruik

        with smtplib.SMTP_SSL('smtp.gmail.com', 465) as server:
            server.login(st.secrets["EMAIL_USER"], st.secrets["EMAIL_PASS"])
            server.send_message(msg)
    except Exception as e:
        st.error(f"Fout bij verzenden mail naar {ontvanger}: {e}")

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
    bericht = st.text_area("Omschrijving klacht/verzoek *")
    uploaded_files = st.file_uploader("Documenten uploaden (ID, Perceelkaart, etc.)", accept_multiple_files=True)
    datum = st.date_input("Datum", min_value=datetime.date.today())
    
    if datum.weekday() in [0, 2]:
        res = supabase.table("aanvragen").select("afspraak_tijd").eq("afspraak_datum", str(datum)).execute()
        bezet = [r['afspraak_tijd'] for r in res.data] if res.data else []
        tijden = [f"{h:02d}:{m:02d}" for h in range(7, 15) for m in [0, 15, 30, 45]]
        vrije_tijden = [t for t in tijden if t not in bezet and "07:00" <= t <= "14:45"]
        gekozen_tijd = st.selectbox("Tijdstip", ["--- Kies ---"] + vrije_tijden)
        
        if st.button("Versturen"):
            if all([vnaam, anaam, email, id_nr, bericht]) and gekozen_tijd != "--- Kies ---":
                # Opslaan in Database
                supabase.table("aanvragen").insert({
                    "voornaam": vnaam, "achternaam": anaam, "email": email, 
                    "id_nummer": id_nr, "woonadres": woonadres, "telefoon": tel,
                    "lad_nummer": lad_nr, "afspraak_datum": str(datum), 
                    "afspraak_tijd": gekozen_tijd, "status": "In behandeling", "bericht": bericht
                }).execute()
                
                # Mail naar cliënt
                stuur_mail(email, "Ontvangstbevestiging DGW", f"Geachte {vnaam},\n\nUw aanvraag voor {datum} om {gekozen_tijd} uur is ontvangen.")
                
                # Mail naar medewerker MET documenten
                notificatie = f"Nieuwe aanvraag van {vnaam} {anaam}.\nID: {id_nr}\nDatum: {datum} om {gekozen_tijd}u.\n\nBericht:\n{bericht}"
                stuur_mail(st.secrets["EMAIL_USER"], f"NIEUWE AANVRAAG: {vnaam} {anaam}", notificatie, bestanden=uploaded_files)
                
                st.success("✅ Uw aanvraag is verzonden. De medewerker heeft uw documenten ontvangen.")
                st.balloons()
            else: st.error("⚠️ Vul alle verplichte velden in.")
    else: st.error("Afspraken uitsluitend op Maandag en Woensdag.")

elif menu == "Medewerker Portaal":
    st.header("📋 Beheer Aanvragen")
    res = supabase.table("aanvragen").select("*").order('created_at', desc=True).execute()
    if res.data:
        df = pd.DataFrame(res.data)
        st.dataframe(df)
        sel_id = st.selectbox("Selecteer ID voor update", df['id'].tolist())
        
        n_status = st.selectbox("Nieuwe Status", ["Bevestigd", "In behandeling", "Geannuleerd", "Verwezen"])
        toelichting = st.text_area("Toelichting voor de mail naar de cliënt")
        
        if st.button("Status Bijwerken & Mailen"):
            supabase.table("aanvragen").update({"status": n_status}).eq("id", sel_id).execute()
            aanvraag = next(item for item in res.data if item['id'] == sel_id)
            
            mail_tekst = f"De status van uw aanvraag is gewijzigd naar: {n_status}."
            if toelichting: mail_tekst += f"\n\nToelichting:\n{toelichting}"
            
            stuur_mail(aanvraag['email'], f"Update status: {n_status}", mail_tekst)
            st.success("✅ Status bijgewerkt en cliënt geïnformeerd.")
            st.rerun()

elif menu == "Agenda Overzicht":
    st.header("📅 Dagplanning")
    res = supabase.table("aanvragen").select("*").execute()
    if res.data:
        df = pd.DataFrame(res.data)
        dag = st.date_input("Datum", value=datetime.date.today())
        dag_data = df[df['afspraak_datum'] == str(dag)].sort_values('afspraak_tijd')
        for _, r in dag_data.iterrows():
            st.markdown(f'<div class="status-card"><b>🕒 {r["afspraak_tijd"]}</b> | {r["voornaam"]} {r["achternaam"]} | <b>{r["status"]}</b></div>', unsafe_allow_html=True)

elif menu == "Rapportages":
    st.header("📊 Statistieken")
    res = supabase.table("aanvragen").select("*").execute()
    if res.data:
        df = pd.DataFrame(res.data)
        st.bar_chart(df['status'].value_counts())
        st.download_button("Download Data", df.to_csv(index=False), "DGW_Data.csv")

elif menu == "Admin Instellingen":
    st.header("⚙️ Admin")
    with st.expander("Nieuwe Medewerker"):
        u, p, r = st.text_input("Naam"), st.text_input("Wachtwoord"), st.selectbox("Rol", ["Medewerker", "Admin"])
        if st.button("Toevoegen"):
            supabase.table("medewerkers").insert({"gebruikersnaam": u, "wachtwoord": p, "rol": r}).execute()
            st.rerun()

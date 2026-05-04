import streamlit as st
from supabase import create_client, Client
import datetime
import pandas as pd
import smtplib
from email.mime.text import MIMEText
from email.mime.multipart import MIMEMultipart
from email.mime.application import MIMEApplication
import urllib.parse
from streamlit_calendar import calendar

# --- 1. CONFIGURATIE & STYLING ---
st.set_page_config(page_title="Registratie Dienst Grondzaken Wanica", layout="wide")

try:
    st.sidebar.image("orgineel logo Centrum.png", use_container_width=True)
except:
    st.sidebar.warning("Logo bestand niet gevonden.")

st.markdown("""
    <style>
    .tijd-knop { display: inline-block; padding: 10px; margin: 5px; border-radius: 5px; text-align: center; font-weight: bold; width: 100px; }
    .vrij { background-color: #e8f5e9; border: 2px solid #2e7d32; color: #2e7d32; }
    .bezet { background-color: #ffebee; border: 2px solid #c62828; color: #c62828; text-decoration: line-through; opacity: 0.6; }
    .status-card { padding: 20px; border-radius: 10px; border-left: 8px solid #2e7d32; background-color: #ffffff; margin-bottom: 15px; border: 1px solid #ddd; box-shadow: 2px 2px 5px rgba(0,0,0,0.1); }
    .stButton>button { background-color: #2e7d32 !important; color: white !important; }
    </style>
    """, unsafe_allow_html=True)

# Verbinding met Supabase
supabase = create_client(st.secrets["SUPABASE_URL"], st.secrets["SUPABASE_KEY"])

# --- PROFESSIONELE MAIL FUNCTIE ---
def stuur_mail(ontvanger, onderwerp, inhoud, bestanden=None):
    try:
        msg = MIMEMultipart()
        msg['Subject'] = onderwerp
        msg['From'] = f"Dienst Grondzaken Wanica <{st.secrets['EMAIL_USER']}>"
        msg['To'] = ontvanger
        
        footer = "\n\n---\nMet vriendelijke groet,\n\nDistrictscommissariaat Wanica-Centrum\nAfdeling Dienst Grondzaken Wanica (DGW)\nLelydorp, Suriname"
        msg.attach(MIMEText(inhoud + footer, 'plain'))
        
        if bestanden:
            for f in bestanden:
                f.seek(0)
                bijlage = MIMEApplication(f.read(), Name=f.name)
                bijlage['Content-Disposition'] = f'attachment; filename="{f.name}"'
                msg.attach(bijlage)
                f.seek(0)
                
        with smtplib.SMTP_SSL('smtp.gmail.com', 465) as server:
            server.login(st.secrets["EMAIL_USER"], st.secrets["EMAIL_PASS"])
            server.send_message(msg)
    except Exception as e:
        st.error(f"Fout bij verzenden mail: {e}")

# --- 2. LOGIN STATUS ---
if 'logged_in' not in st.session_state:
    st.session_state.logged_in, st.session_state.role, st.session_state.user = False, None, None

def login():
    st.sidebar.subheader("🔐 Inloggen Medewerkers")
    res = supabase.table("medewerkers").select("*").execute()
    user_list = [u['gebruikersnaam'] for u in res.data] if res.data else []
    selected_user = st.sidebar.selectbox("Gebruiker", ["--- Kies Gebruiker ---"] + user_list)
    password = st.sidebar.text_input("Wachtwoord", type="password")
    if st.sidebar.button("Inloggen"):
        user_data = next((u for u in res.data if u['gebruikersnaam'] == selected_user), None)
        if user_data and user_data['wachtwoord'] == password:
            st.session_state.logged_in, st.session_state.role, st.session_state.user = True, user_data['rol'], selected_user
            st.rerun()

# --- 3. NAVIGATIE ---
menu_options = ["Registratie DGW"]
if st.session_state.logged_in:
    menu_options += ["Medewerker Portaal", "Agenda Overzicht", "Rapportages"]
    if str(st.session_state.role).lower() == "admin": menu_options.append("Admin Instellingen")
    
    app_url = "https://dgw-wanica.streamlit.app/"
    qr_api = f"https://api.qrserver.com/v1/create-qr-code/?size=150x150&data={urllib.parse.quote(app_url)}"
    st.sidebar.write("---")
    st.sidebar.image(qr_api, caption="Scan QR voor cliënt")
    if st.sidebar.button("🚪 Uitloggen"):
        st.session_state.logged_in = False
        st.rerun()
else: login()

menu = st.sidebar.radio("Navigatie", menu_options)

# --- 4. PAGINA'S ---

if menu == "Registratie DGW":
    st.header("📝 Registratie Dienst Grondzaken Wanica")
    st.info("Vul onderstaand formulier volledig in om een afspraak te maken.")
    
    col1, col2 = st.columns(2)
    with col1:
        vnaam = st.text_input("Voornaam *")
        anaam = st.text_input("Achternaam *")
        id_nr = st.text_input("ID-Nummer *")
        email = st.text_input("E-mailadres *")
    with col2:
        tel = st.text_input("Telefoonnummer *")
        woonadres = st.text_input("Woonadres *")
        lad_nr = st.text_input("LAD Nummer")
    
    bericht = st.text_area("Omschrijving van uw klacht of verzoek *")
    uploaded_files = st.file_uploader("Documenten uploaden (ID-kaart, Perceelkaart, etc.)", accept_multiple_files=True)
    
    st.write("---")
    st.subheader("📅 Selecteer uw afspraakmoment")
    datum = st.date_input("Kies een datum", min_value=datetime.date.today())
    
    if datum.weekday() in [0, 2]:
        tijden = [f"{h:02d}:{m:02d}" for h in range(7, 15) for m in [0, 15, 30, 45] if "07:00" <= f"{h:02d}:{m:02d}" <= "14:45"]
        res = supabase.table("aanvragen").select("afspraak_tijd").eq("afspraak_datum", str(datum)).execute()
        bezet = [r['afspraak_tijd'] for r in res.data] if res.data else []
        
        st.write("Beschikbare tijdstippen:")
        cols = st.columns(4)
        for i, t in enumerate(tijden):
            with cols[i % 4]:
                if t in bezet:
                    st.markdown(f'<div class="tijd-knop bezet">{t}</div>', unsafe_allow_html=True)
                else:
                    if st.button(f"Kies {t}", key=f"btn_{t}"):
                        st.session_state.selected_time = t
        
        if 'selected_time' in st.session_state:
            st.success(f"Geselecteerd tijdstip: **{st.session_state.selected_time}**")
            if st.button("Registratie Definitief Verzenden"):
                if all([vnaam, anaam, email, id_nr, bericht]):
                    supabase.table("aanvragen").insert({
                        "voornaam": vnaam, "achternaam": anaam, "email": email, "id_nummer": id_nr, 
                        "woonadres": woonadres, "telefoon": tel, "lad_nummer": lad_nr, 
                        "afspraak_datum": str(datum), "afspraak_tijd": st.session_state.selected_time, 
                        "status": "In behandeling", "bericht": bericht
                    }).execute()
                    
                    client_inhoud = f"Geachte heer/mevrouw {anaam},\n\nHierbij bevestigen wij uw afspraak op {datum.strftime('%d-%m-%Y')} om {st.session_state.selected_time} uur bij de Dienst Grondzaken Wanica."
                    stuur_mail(email, "Bevestiging Ontvangst Registratie - DGW Wanica", client_inhoud)
                    
                    med_inhoud = f"Nieuwe Registratie:\nNaam: {vnaam} {anaam}\nID: {id_nr}\nLAD: {lad_nr}\n\nVerzoek:\n{bericht}"
                    stuur_mail(st.secrets["EMAIL_USER"], f"NIEUWE REGISTRATIE: {vnaam} {anaam}", med_inhoud, bestanden=uploaded_files)
                    
                    st.success("✅ Uw registratie is succesvol verzonden.")
                    st.balloons()
                    del st.session_state.selected_time
                else: st.error("Gelieve alle verplichte velden (*) in te vullen.")
    else: st.error("⚠️ Afspraken uitsluitend op maandag en woensdag.")

elif menu == "Medewerker Portaal":
    st.header("📋 Beheer Registraties")
    res = supabase.table("aanvragen").select("*").order('created_at', desc=True).execute()
    if res.data:
        df = pd.DataFrame(res.data)
        st.dataframe(df[['id', 'voornaam', 'achternaam', 'afspraak_datum', 'status']])
        
        sel_id = st.selectbox("Selecteer een dossier ID voor bewerking", df['id'].tolist())
        reg = next(item for item in res.data if item['id'] == sel_id)
        
        # UITGEBREIDE DETAILS VOOR DE MEDEWERKER
        st.markdown(f"""
        <div class="status-card">
            <h3>Dossier Details: {reg['voornaam']} {reg['achternaam']}</h3>
            <div style="display: flex; justify-content: space-between;">
                <div style="flex: 1;">
                    <p><b>📅 Afspraak datum:</b> {reg['afspraak_datum']}</p>
                    <p><b>🕒 Afspraak tijd:</b> {reg['afspraak_tijd']}</p>
                    <p><b>🆔 ID-Nummer:</b> {reg['id_nummer']}</p>
                    <p><b>📄 LAD-Nummer:</b> {reg.get('lad_nummer', 'Niet opgegeven')}</p>
                </div>
                <div style="flex: 1;">
                    <p><b>📞 Telefoon:</b> {reg['telefoon']}</p>
                    <p><b>📧 E-mail:</b> {reg['email']}</p>
                    <p><b>🏠 Woonadres:</b> {reg['woonadres']}</p>
                    <p><b>🚦 Huidige Status:</b> {reg['status']}</p>
                </div>
            </div>
            <hr>
            <p><b>📝 Omschrijving verzoek:</b><br>{reg['bericht']}</p>
        </div>
        """, unsafe_allow_html=True)
        
        n_status = st.selectbox("Wijzig Status naar:", ["Bevestigd", "In behandeling", "Geannuleerd", "Verwezen"])
        toelichting = st.text_area("Toelichting voor de cliënt")
        
        if st.button("Update Status & Mailen"):
            supabase.table("aanvragen").update({"status": n_status, "medewerker_toelichting": toelichting}).eq("id", sel_id).execute()
            
            update_mail = f"Geachte heer/mevrouw {reg['achternaam']},\n\nDe status van uw dossier is bijgewerkt naar: {n_status}\n\nToelichting:\n{toelichting}"
            stuur_mail(reg['email'], f"Update Registratie: {n_status}", update_mail)
            stuur_mail(st.secrets["EMAIL_USER"], f"LOG: Status Update {sel_id}", f"Medewerker {st.session_state.user} wijzigde status naar {n_status}.")
            
            st.success("✅ Bijgewerkt!")
            st.rerun()

elif menu == "Agenda Overzicht":
    st.header("📅 Agenda Overzicht")
    res = supabase.table("aanvragen").select("*").execute()
    if res.data:
        events = [{"title": f"{r['afspraak_tijd']} - {r['voornaam']}", "start": r['afspraak_datum'], "end": r['afspraak_datum'], "color": "#2e7d32"} for r in res.data]
        calendar(events=events, options={"initialView": "dayGridMonth"})

elif menu == "Rapportages":
    st.header("📊 Rapportages")
    res = supabase.table("aanvragen").select("*").order('created_at', desc=True).execute()
    if res.data:
        df = pd.DataFrame(res.data)
        st.dataframe(df[['id', 'voornaam', 'achternaam', 'status', 'medewerker_toelichting', 'afspraak_datum']])

elif menu == "Admin Instellingen":
    st.header("⚙️ Systeembeheer")
    
    with st.expander("➕ Nieuwe Medewerker Toevoegen"):
        with st.form("add_user_form", clear_on_submit=True):
            new_u = st.text_input("Gebruikersnaam")
            new_p = st.text_input("Wachtwoord", type="password")
            new_r = st.selectbox("Rol", ["Medewerker", "Admin"])
            if st.form_submit_button("Account Aanmaken"):
                supabase.table("medewerkers").insert({"gebruikersnaam": new_u, "wachtwoord": new_p, "rol": new_r}).execute()
                st.success(f"✅ Medewerker {new_u} toegevoegd.")
                st.rerun()

    st.write("---")
    st.subheader("👥 Medewerkers Beheren")
    res_med = supabase.table("medewerkers").select("*").execute()
    if res_med.data:
        for med in res_med.data:
            col1, col2, col3, col4 = st.columns([2, 1, 2, 1])
            with col1: st.write(f"**{med['gebruikersnaam']}** ({med['rol']})")
            with col2:
                if med['gebruikersnaam'] != st.session_state.user:
                    if st.button("🗑️ Wis", key=f"del_{med['id']}"):
                        supabase.table("medewerkers").delete().eq("id", med['id']).execute()
                        st.rerun()
            with col3: n_pass = st.text_input("Nieuw wachtwoord", type="password", key=f"p_{med['id']}", label_visibility="collapsed")
            with col4:
                if st.button("💾 Opslaan", key=f"save_{med['id']}"):
                    supabase.table("medewerkers").update({"wachtwoord": n_pass}).eq("id", med['id']).execute()
                    st.success("Bijgewerkt!")

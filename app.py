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
    .status-card { padding: 20px; border-radius: 10px; border-left: 8px solid #2e7d32; background-color: #ffffff; margin-bottom: 15px; border: 1px solid #ddd; box-shadow: 2px 2px 5px rgba(0,0,0,0.1); }
    .report-box { background-color: #f8f9fa; padding: 15px; border-radius: 5px; border: 1px solid #e9ecef; margin-top: 10px; }
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
    if st.sidebar.button("🚪 Uitloggen"):
        st.session_state.logged_in = False
        st.rerun()
else: login()

menu = st.sidebar.radio("Navigatie", menu_options)

# --- 4. PAGINA'S ---

if menu == "Registratie DGW":
    st.header("📝 Nieuwe Aanvraag DGW")
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
    uploaded_files = st.file_uploader("Documenten uploaden", accept_multiple_files=True)
    datum = st.date_input("Kies een datum", min_value=datetime.date.today())
    
    if st.button("Registratie Verzenden"):
        if all([vnaam, anaam, email, id_nr, bericht]):
            supabase.table("aanvragen").insert({
                "voornaam": vnaam, "achternaam": anaam, "email": email, "id_nummer": id_nr, 
                "woonadres": woonadres, "telefoon": tel, "lad_nummer": lad_nr, 
                "afspraak_datum": str(datum), "status": "In behandeling", "bericht": bericht
            }).execute()
            st.success("✅ Succesvol verzonden!")
        else: st.error("Vul alle verplichte velden in.")

elif menu == "Medewerker Portaal":
    st.header("📋 Beheer Registraties & Dossieropbouw")
    res = supabase.table("aanvragen").select("*").order('created_at', desc=True).execute()
    if res.data:
        df = pd.DataFrame(res.data)
        st.dataframe(df[['id', 'voornaam', 'achternaam', 'afspraak_datum', 'status']])
        
        sel_id = st.selectbox("Selecteer Dossier ID", df['id'].tolist())
        reg = next(item for item in res.data if item['id'] == sel_id)
        
        st.markdown(f"""
        <div class="status-card">
            <h3>Dossier: {reg['voornaam']} {reg['achternaam']}</h3>
            <p><b>Contact:</b> {reg['telefoon']} | {reg['email']}</p>
            <p><b>Verzoek:</b> {reg['bericht']}</p>
        </div>
        """, unsafe_allow_html=True)
        
        st.subheader("✍️ Rapportage Bijwerken")
        col1, col2 = st.columns(2)
        with col1:
            n_status = st.selectbox("Status aanpassen", ["Bevestigd", "In behandeling", "Afgehandeld", "Geannuleerd", "Verwezen"])
            behandeld_tekst = st.selectbox("Is dit dossier afgehandeld?", ["Nee", "Ja"], index=1 if reg.get('behandeld') == "Ja" else 0)
        with col2:
            volgende_stappen = st.text_area("Mee te nemen documenten / Vervolgstappen", value=reg.get('volgende_stappen', ""))
        
        intern_verslag = st.text_area("Wat is er afgesproken? (Intern verslag)", value=reg.get('intern_verslag', ""))
        toelichting_mail = st.text_area("Bericht voor de cliënt (optioneel)")
        
        if st.button("Dossier & Rapportage Opslaan"):
            supabase.table("aanvragen").update({
                "status": n_status,
                "behandeld": behandeld_tekst,
                "volgende_stappen": volgende_stappen,
                "intern_verslag": intern_verslag,
                "medewerker_toelichting": toelichting_mail
            }).eq("id", sel_id).execute()
            
            if toelichting_mail:
                mail_tekst = f"Geachte {reg['achternaam']},\n\nUw dossier status: {n_status}\n\nVolgende stappen: {volgende_stappen}\n\nToelichting: {toelichting_mail}"
                stuur_mail(reg['email'], f"DGW Update: {reg['voornaam']} {reg['achternaam']}", mail_tekst)
            
            st.success("✅ Dossier succesvol bijgewerkt.")
            st.rerun()

elif menu == "Rapportages":
    st.header("📊 Dossier Rapportages")
    res = supabase.table("aanvragen").select("*").order('created_at', desc=True).execute()
    if res.data:
        df = pd.DataFrame(res.data)
        st.dataframe(df[['id', 'voornaam', 'achternaam', 'status', 'behandeld']])
        
        st.write("---")
        st.subheader("🔍 Rapport Inzien")
        sel_rep = st.selectbox("Kies een cliënt voor het volledige rapport", [f"{r['id']} - {r['voornaam']} {r['achternaam']}" for r in res.data])
        rep_id = int(sel_rep.split(" - ")[0])
        row = next(item for item in res.data if item['id'] == rep_id)
        
        st.markdown(f"""
        <div class="report-box">
            <h4>Rapportage: {row['voornaam']} {row['achternaam']}</h4>
            <p><b>Status:</b> {row['status']} | <b>Afgehandeld:</b> {row.get('behandeld', 'Nee')}</p>
            <hr>
            <p><b>Gemaakte Afspraken (Intern):</b><br>{row.get('intern_verslag', 'Geen afspraken genoteerd.')}</p>
            <p><b>Volgende Stappen (Cliënt):</b><br>{row.get('volgende_stappen', 'Geen vervolgstappen genoteerd.')}</p>
            <p><b>Laatst gestuurde toelichting:</b><br><i>{row.get('medewerker_toelichting', 'Geen toelichting.')}</i></p>
        </div>
        """, unsafe_allow_html=True)

elif menu == "Agenda Overzicht":
    st.header("📅 Agenda Overzicht")
    res = supabase.table("aanvragen").select("*").execute()
    if res.data:
        events = [{"title": f"{r['voornaam']} {r['achternaam']}", "start": r['afspraak_datum'], "end": r['afspraak_datum'], "color": "#2e7d32"} for r in res.data]
        calendar(events=events, options={"initialView": "dayGridMonth"})

elif menu == "Admin Instellingen":
    st.header("⚙️ Systeembeheer")
    
    with st.expander("➕ Nieuwe Medewerker Toevoegen"):
        with st.form("add_user_form", clear_on_submit=True):
            new_u = st.text_input("Gebruikersnaam")
            new_p = st.text_input("Wachtwoord", type="password")
            new_r = st.selectbox("Rol", ["Medewerker", "Admin"])
            if st.form_submit_button("Account Aanmaken"):
                if new_u and new_p:
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
            with col3: n_pass = st.text_input("Wachtwoord wijzigen", type="password", key=f"p_{med['id']}", label_visibility="collapsed", placeholder="Nieuw wachtwoord")
            with col4:
                if st.button("💾 Opslaan", key=f"save_{med['id']}"):
                    if n_pass:
                        supabase.table("medewerkers").update({"wachtwoord": n_pass}).eq("id", med['id']).execute()
                        st.success("Wachtwoord bijgewerkt!")

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
st.set_page_config(page_title="Dienst Grondzaken Wanica Centrum", layout="wide")

try:
    st.sidebar.image("orgineel logo Centrum.png", use_container_width=True)
except:
    st.sidebar.warning("Logo bestand niet gevonden.")

st.markdown("""
    <style>
    .main-title { color: #2e7d32; font-weight: bold; }
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
        msg['From'] = f"DGW Centrum <{st.secrets['EMAIL_USER']}>"
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
    st.sidebar.subheader("🔐 Medewerker Login")
    res = supabase.table("medewerkers").select("*").execute()
    user_list = [u['gebruikersnaam'] for u in res.data] if res.data else []
    selected_user = st.sidebar.selectbox("Selecteer Gebruiker", ["--- Maak een keuze ---"] + user_list)
    password = st.sidebar.text_input("Wachtwoord", type="password")
    if st.sidebar.button("Inloggen"):
        user_data = next((u for u in res.data if u['gebruikersnaam'] == selected_user), None)
        if user_data and user_data['wachtwoord'] == password:
            st.session_state.logged_in, st.session_state.role, st.session_state.user = True, user_data['rol'], selected_user
            st.rerun()

# --- 3. NAVIGATIE ---
menu_options = ["Nieuwe Aanvraag DGW"]
if st.session_state.logged_in:
    menu_options += ["Beheer Registraties", "Agenda", "Rapportages"]
    if str(st.session_state.role).lower() == "admin": menu_options.append("Systeembeheer")
    if st.sidebar.button("🚪 Uitloggen"):
        st.session_state.logged_in = False
        st.rerun()
else: login()

menu = st.sidebar.radio("Navigatie", menu_options)

# --- 4. PAGINA'S ---

if menu == "Nieuwe Aanvraag DGW":
    st.header("📝 Dienst Grondzaken Wanica Centrum")
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
    datum = st.date_input("Voorkeursdatum afspraak", min_value=datetime.date.today())
    
    if st.button("Registratie Verzenden"):
        if all([vnaam, anaam, email, id_nr, bericht]):
            supabase.table("aanvragen").insert({
                "voornaam": vnaam, "achternaam": anaam, "email": email, "id_nummer": id_nr, 
                "woonadres": woonadres, "telefoon": tel, "lad_nummer": lad_nr, 
                "afspraak_datum": str(datum), "status": "In behandeling", "bericht": bericht
            }).execute()
            st.success("✅ Uw aanvraag is succesvol geregistreerd bij DGW Centrum.")
        else: st.error("Vul alle verplichte velden (*) in.")

elif menu == "Beheer Registraties":
    st.header("📋 Beheer Registraties DGW Centrum")
    res = supabase.table("aanvragen").select("*").order('created_at', desc=True).execute()
    if res.data:
        df = pd.DataFrame(res.data)
        st.dataframe(df[['id', 'voornaam', 'achternaam', 'afspraak_datum', 'status']])
        
        sel_id = st.selectbox("Selecteer dossier ID voor bewerking", df['id'].tolist())
        reg = next(item for item in res.data if item['id'] == sel_id)
        
        st.markdown(f"""
        <div class="status-card">
            <h3>Dossier: {reg['voornaam']} {reg['achternaam']}</h3>
            <p><b>Status:</b> {reg['status']}</p>
            <p><b>Verzoek:</b> {reg['bericht']}</p>
        </div>
        """, unsafe_allow_html=True)
        
        st.subheader("✍️ Rapportage & Status Bijwerken")
        col_a, col_b = st.columns(2)
        with col_a:
            n_status = st.selectbox("Status aanpassen", ["Bevestigd", "In behandeling", "Afgehandeld", "Geannuleerd", "Verwezen"], 
                                    index=["Bevestigd", "In behandeling", "Afgehandeld", "Geannuleerd", "Verwezen"].index(reg['status']) if reg['status'] in ["Bevestigd", "In behandeling", "Afgehandeld", "Geannuleerd", "Verwezen"] else 1)
            behandeld_tekst = st.selectbox("Dossier afgehandeld?", ["Nee", "Ja"], index=1 if reg.get('behandeld') == "Ja" else 0)
        with col_b:
            volgende_stappen = st.text_area("Volgende stappen / Mee te nemen stukken", value=reg.get('volgende_stappen', ""))
        
        intern_verslag = st.text_area("Intern verslag (Wat is er afgesproken?)", value=reg.get('intern_verslag', ""))
        toelichting_mail = st.text_area("Bericht voor de cliënt (optioneel)", placeholder="Vul hier extra info in voor de cliënt...")
        
        if st.button("Wijzigingen Opslaan"):
            supabase.table("aanvragen").update({
                "status": n_status,
                "behandeld": behandeld_tekst,
                "volgende_stappen": volgende_stappen,
                "intern_verslag": intern_verslag,
                "medewerker_toelichting": toelichting_mail if toelichting_mail else reg.get('medewerker_toelichting', "")
            }).eq("id", sel_id).execute()
            
            if toelichting_mail:
                mail_content = f"Geachte {reg['achternaam']},\n\nUpdate status: {n_status}\n\nVolgende stappen: {volgende_stappen}\n\nToelichting: {toelichting_mail}"
                stuur_mail(reg['email'], f"DGW Centrum Update: Dossier {sel_id}", mail_content)
            
            st.success("✅ Dossier succesvol bijgewerkt.")
            st.rerun()

elif menu == "Rapportages":
    st.header("📊 Rapportages DGW Centrum")
    res = supabase.table("aanvragen").select("*").order('created_at', desc=True).execute()
    if res.data:
        df = pd.DataFrame(res.data)
        st.dataframe(df[['id', 'voornaam', 'achternaam', 'status', 'behandeld', 'afspraak_datum']])
        
        st.write("---")
        st.subheader("🔍 Inzage Dossier Rapport")
        sel_rep = st.selectbox("Kies cliënt", [f"{r['id']} - {r['voornaam']} {r['achternaam']}" for r in res.data])
        rep_id = int(sel_rep.split(" - ")[0])
        row = next(item for item in res.data if item['id'] == rep_id)
        
        st.markdown(f"""
        <div class="report-box">
            <h4>Rapportage: {row['voornaam']} {row['achternaam']}</h4>
            <p><b>Behandeld:</b> {row.get('behandeld', 'Nee')}</p>
            <hr>
            <p><b>Interne Afspraken:</b><br>{row.get('intern_verslag', 'Nog geen verslag.')}</p>
            <p><b>Mee te nemen door cliënt:</b><br>{row.get('volgende_stappen', 'Geen instructies.')}</p>
            <p><b>Laatste mail toelichting:</b><br><i>{row.get('medewerker_toelichting', 'Geen.')}</i></p>
        </div>
        """, unsafe_allow_html=True)

elif menu == "Agenda":
    st.header("📅 Agenda DGW Centrum")
    res = supabase.table("aanvragen").select("*").execute()
    if res.data:
        events = [{"title": f"{r['voornaam']} {r['achternaam']}", "start": r['afspraak_datum'], "end": r['afspraak_datum'], "color": "#2e7d32"} for r in res.data]
        calendar(events=events, options={"initialView": "dayGridMonth"})

elif menu == "Systeembeheer":
    st.header("⚙️ Systeembeheer DGW Centrum")
    
    with st.expander("➕ Nieuwe Medewerker"):
        with st.form("new_user_form"):
            u = st.text_input("Gebruikersnaam")
            p = st.text_input("Wachtwoord", type="password")
            r = st.selectbox("Rol", ["Medewerker", "Admin"])
            if st.form_submit_button("Account Aanmaken"):
                supabase.table("medewerkers").insert({"gebruikersnaam": u, "wachtwoord": p, "rol": r}).execute()
                st.success("✅ Account aangemaakt.")
                st.rerun()

    st.write("---")
    res_m = supabase.table("medewerkers").select("*").execute()
    for med in res_m.data:
        c1, c2, c3 = st.columns([3, 2, 1])
        with c1: st.write(f"👤 **{med['gebruikersnaam']}** ({med['rol']})")
        with c2: new_p = st.text_input("Nieuw wachtwoord", type="password", key=f"pw_{med['id']}", label_visibility="collapsed")
        with c3:
            if st.button("💾", key=f"s_{med['id']}"):
                supabase.table("medewerkers").update({"wachtwoord": new_p}).eq("id", med['id']).execute()
                st.success("Ok")

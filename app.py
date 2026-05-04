import streamlit as st
from supabase import create_client, Client
import datetime
import pandas as pd
import smtplib
from email.mime.text import MIMEText
from email.mime.multipart import MIMEMultipart
from email.mime.application import MIMEApplication
from streamlit_calendar import calendar

# --- 1. CONFIGURATIE & STYLING ---
st.set_page_config(page_title="Dienst Grondzaken Wanica Centrum", layout="wide")

# Logo laden
try:
    st.sidebar.image("orgineel logo Centrum.png", use_container_width=True)
except:
    st.sidebar.warning("Logo niet gevonden.")

st.markdown("""
    <style>
    .tijd-knop { display: inline-block; padding: 10px; margin: 5px; border-radius: 5px; text-align: center; font-weight: bold; width: 100px; border: 1px solid #ddd; }
    .vrij { background-color: #e8f5e9; color: #2e7d32; cursor: pointer; }
    .bezet { background-color: #ffebee; color: #c62828; cursor: not-allowed; }
    .geselecteerd { background-color: #2e7d32; color: white; }
    .status-card { padding: 20px; border-radius: 10px; border-left: 8px solid #2e7d32; background-color: #ffffff; margin-bottom: 15px; border: 1px solid #ddd; }
    .stButton>button { background-color: #2e7d32 !important; color: white !important; }
    </style>
    """, unsafe_allow_html=True)

# Verbinding met Supabase
supabase = create_client(st.secrets["SUPABASE_URL"], st.secrets["SUPABASE_KEY"])

# --- HULPFUNCTIES ---
def stuur_mail(ontvanger, onderwerp, inhoud):
    try:
        msg = MIMEMultipart()
        msg['Subject'] = onderwerp
        msg['From'] = f"DGW Centrum <{st.secrets['EMAIL_USER']}>"
        msg['To'] = ontvanger
        msg.attach(MIMEText(inhoud + "\n\n---\nDistrictscommissariaat Wanica-Centrum", 'plain'))
        with smtplib.SMTP_SSL('smtp.gmail.com', 465) as server:
            server.login(st.secrets["EMAIL_USER"], st.secrets["EMAIL_PASS"])
            server.send_message(msg)
    except Exception as e:
        st.error(f"Mail fout: {e}")

# --- 2. LOGIN STATUS ---
if 'logged_in' not in st.session_state:
    st.session_state.update({'logged_in': False, 'role': None, 'user': None})

if not st.session_state.logged_in:
    st.sidebar.subheader("🔐 Medewerker Login")
    res_m = supabase.table("medewerkers").select("*").execute()
    user_list = [u['gebruikersnaam'] for u in res_m.data] if res_m.data else []
    u_sel = st.sidebar.selectbox("Gebruiker", ["---"] + user_list)
    p_inp = st.sidebar.text_input("Wachtwoord", type="password")
    if st.sidebar.button("Inloggen"):
        user_data = next((u for u in res_m.data if u['gebruikersnaam'] == u_sel), None)
        if user_data and user_data['wachtwoord'] == p_inp:
            st.session_state.update({'logged_in': True, 'role': user_data['rol'], 'user': u_sel})
            st.rerun()

# --- 3. NAVIGATIE ---
menu_options = ["Nieuwe Aanvraag DGW"]
if st.session_state.logged_in:
    menu_options += ["Beheer Registraties", "Agenda", "Rapportages"]
    if str(st.session_state.role).lower() == "admin": menu_options.append("Systeembeheer")
    if st.sidebar.button("🚪 Uitloggen"):
        st.session_state.logged_in = False
        st.rerun()

menu = st.sidebar.radio("Menu", menu_options)

# --- 4. PAGINA'S ---

if menu == "Nieuwe Aanvraag DGW":
    st.header("📝 Dienst Grondzaken Wanica Centrum")
    col1, col2 = st.columns(2)
    with col1:
        vnaam = st.text_input("Voornaam *")
        anaam = st.text_input("Achternaam *")
        email = st.text_input("E-mailadres *")
    with col2:
        id_nr = st.text_input("ID-Nummer *")
        tel = st.text_input("Telefoonnummer *")
        lad_nr = st.text_input("LAD Nummer")
    
    bericht = st.text_area("Omschrijving van uw verzoek *")
    datum = st.date_input("Kies een datum", min_value=datetime.date.today())
    
    # --- AFSPRAAK TIJDEN LOGICA ---
    st.subheader("⏰ Beschikbare Tijden")
    tijdsblokken = ["08:00", "08:30", "09:00", "09:30", "10:00", "10:30", "11:00", "11:30", "12:00", "12:30"]
    
    # Haal bezette tijden op voor gekozen datum
    res_t = supabase.table("aanvragen").select("afspraak_tijd").eq("afspraak_datum", str(datum)).execute()
    bezette_tijden = [r['afspraak_tijd'] for r in res_t.data] if res_t.data else []
    
    gekozen_tijd = None
    cols = st.columns(5)
    for i, tijd in enumerate(tijdsblokken):
        is_bezet = tijd in bezette_tijden
        label = "🚫 Bezet" if is_bezet else tijd
        stijl = "bezet" if is_bezet else "vrij"
        
        if cols[i % 5].button(label, key=f"t_{tijd}", disabled=is_bezet):
            st.session_state.sel_tijd = tijd
            
    if 'sel_tijd' in st.session_state:
        st.info(f"Geselecteerde tijd: **{st.session_state.sel_tijd}**")
        gekozen_tijd = st.session_state.sel_tijd

    if st.button("Registratie Verzenden"):
        if all([vnaam, anaam, email, id_nr, bericht, gekozen_tijd]):
            supabase.table("aanvragen").insert({
                "voornaam": vnaam, "achternaam": anaam, "email": email, "id_nummer": id_nr,
                "telefoon": tel, "lad_nummer": lad_nr, "afspraak_datum": str(datum),
                "afspraak_tijd": gekozen_tijd, "status": "In behandeling", "bericht": bericht
            }).execute()
            st.success("✅ Succesvol geregistreerd bij DGW Centrum!")
            del st.session_state.sel_tijd
        else:
            st.error("Vul alle verplichte velden en kies een tijdstip.")

elif menu == "Beheer Registraties":
    st.header("📋 Beheer Registraties DGW Centrum")
    res = supabase.table("aanvragen").select("*").order('created_at', desc=True).execute()
    if res.data:
        df = pd.DataFrame(res.data)
        st.dataframe(df[['id', 'voornaam', 'achternaam', 'afspraak_datum', 'afspraak_tijd', 'status']])
        
        sel_id = st.selectbox("Selecteer dossier ID", df['id'].tolist())
        reg = next(item for item in res.data if item['id'] == sel_id)
        
        with st.container():
            st.markdown(f"**Dossier van:** {reg['voornaam']} {reg['achternaam']} | **ID:** {reg['id_nummer']}")
            col_a, col_b = st.columns(2)
            with col_a:
                n_status = st.selectbox("Status", ["Bevestigd", "In behandeling", "Afgehandeld", "Geannuleerd", "Verwezen"], index=0)
                behandeld = st.selectbox("Afgehandeld?", ["Nee", "Ja"], index=1 if reg.get('behandeld') == "Ja" else 0)
            with col_b:
                stappen = st.text_area("Volgende stappen voor cliënt", value=reg.get('volgende_stappen', ""))
            
            verslag = st.text_area("Intern verslag", value=reg.get('intern_verslag', ""))
            mail_bericht = st.text_area("Extra toelichting voor de cliënt", value=reg.get('medewerker_toelichting', ""))
            
            if st.button("Update Opslaan"):
                supabase.table("aanvragen").update({
                    "status": n_status, "behandeld": behandeld,
                    "volgende_stappen": stappen, "intern_verslag": verslag,
                    "medewerker_toelichting": mail_bericht
                }).eq("id", sel_id).execute()
                
                if mail_bericht:
                    stuur_mail(reg['email'], "Update DGW Centrum", f"Status: {n_status}\n\nToelichting: {mail_bericht}")
                st.success("Dossier bijgewerkt.")
                st.rerun()

elif menu == "Rapportages":
    st.header("📊 Statistieken & Rapportages")
    res = supabase.table("aanvragen").select("*").execute()
    if res.data:
        df = pd.DataFrame(res.data)
        st.write("Aantal aanvragen per status:")
        st.table(df['status'].value_counts())
        
        st.write("---")
        sel_rep = st.selectbox("Bekijk volledig rapport van cliënt", [f"{r['id']} - {r['voornaam']} {r['achternaam']}" for r in res.data])
        rid = int(sel_rep.split(" - ")[0])
        row = next(item for item in res.data if item['id'] == rid)
        st.json(row)

elif menu == "Agenda":
    st.header("📅 Afsprakenoverzicht")
    res = supabase.table("aanvragen").select("*").execute()
    if res.data:
        events = [{"title": f"{r['voornaam']} {r['achternaam']} ({r['afspraak_tijd']})", "start": r['afspraak_datum'], "color": "#2e7d32"} for r in res.data]
        calendar(events=events, options={"initialView": "dayGridMonth"})

elif menu == "Systeembeheer":
    st.header("⚙️ Admin Instellingen")
    with st.expander("➕ Medewerker Toevoegen"):
        with st.form("add_user"):
            new_u = st.text_input("Gebruikersnaam")
            new_p = st.text_input("Wachtwoord", type="password")
            new_r = st.selectbox("Rol", ["Medewerker", "Admin"])
            if st.form_submit_button("Opslaan"):
                supabase.table("medewerkers").insert({"gebruikersnaam": new_u, "wachtwoord": new_p, "rol": new_r}).execute()
                st.rerun()

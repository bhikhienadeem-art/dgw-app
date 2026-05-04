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

try:
    st.sidebar.image("orgineel logo Centrum.png", use_container_width=True)
except:
    st.sidebar.warning("Logo niet gevonden.")

st.markdown("""
    <style>
    .tijd-knop { display: inline-block; padding: 10px; margin: 5px; border-radius: 5px; text-align: center; font-weight: bold; width: 80px; border: 1px solid #ddd; }
    .vrij { background-color: #e8f5e9; color: #2e7d32; cursor: pointer; }
    .bezet { background-color: #ffebee; color: #c62828; cursor: not-allowed; }
    .stButton>button { background-color: #2e7d32 !important; color: white !important; }
    </style>
    """, unsafe_allow_html=True)

# Verbinding met Supabase
supabase = create_client(st.secrets["SUPABASE_URL"], st.secrets["SUPABASE_KEY"])

# --- MAIL FUNCTIE ---
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
    uploaded_files = st.file_uploader("Documenten uploaden", accept_multiple_files=True)
    
    # Datum selectie met beperking op Maandag (0) en Woensdag (2)
    datum = st.date_input("Kies een datum (Alleen Maandag & Woensdag)", min_value=datetime.date.today())
    
    # Controleer of de dag Maandag of Woensdag is
    if datum.weekday() not in [0, 2]:
        st.warning("⚠️ Let op: Er kunnen alleen afspraken op maandag of woensdag gemaakt worden.")
    else:
        # --- TIJDEN GENEREREN (08:00 - 14:30, elke 15 min) ---
        st.subheader("⏰ Beschikbare Tijden (Maandag/Woensdag)")
        tijdsblokken = []
        start = datetime.datetime.strptime("08:00", "%H:%M")
        eind = datetime.datetime.strptime("14:30", "%H:%M")
        while start <= eind:
            tijdsblokken.append(start.strftime("%H:%M"))
            start += datetime.timedelta(minutes=15)
        
        res_t = supabase.table("aanvragen").select("afspraak_tijd").eq("afspraak_datum", str(datum)).execute()
        bezette_tijden = [r['afspraak_tijd'] for r in res_t.data] if res_t.data else []
        
        gekozen_tijd = None
        cols = st.columns(6)
        for i, tijd in enumerate(tijdsblokken):
            is_bezet = tijd in bezette_tijden
            label = f"🚫 {tijd}" if is_bezet else tijd
            if cols[i % 6].button(label, key=f"t_{tijd}", disabled=is_bezet):
                st.session_state.sel_tijd = tijd
                
        if 'sel_tijd' in st.session_state:
            st.info(f"Geselecteerde tijd: **{st.session_state.sel_tijd}**")
            gekozen_tijd = st.session_state.sel_tijd

    if st.button("Registratie Verzenden"):
        if all([vnaam, anaam, email, id_nr, bericht]) and 'sel_tijd' in st.session_state:
            supabase.table("aanvragen").insert({
                "voornaam": vnaam, "achternaam": anaam, "email": email, "id_nummer": id_nr,
                "telefoon": tel, "lad_nummer": lad_nr, "afspraak_datum": str(datum),
                "afspraak_tijd": st.session_state.sel_tijd, "status": "In behandeling", "bericht": bericht
            }).execute()
            st.success("✅ Succesvol geregistreerd bij DGW Centrum!")
            del st.session_state.sel_tijd
            st.rerun()
        else:
            st.error("Vul alle velden in en kies een geldig tijdstip op een maandag of woensdag.")

elif menu == "Beheer Registraties":
    st.header("📋 Beheer Registraties DGW Centrum")
    res = supabase.table("aanvragen").select("*").order('created_at', desc=True).execute()
    if res.data:
        df = pd.DataFrame(res.data)
        st.dataframe(df[['id', 'voornaam', 'achternaam', 'afspraak_datum', 'afspraak_tijd', 'status']])
        
        sel_id = st.selectbox("Selecteer dossier ID", df['id'].tolist())
        reg = next(item for item in res.data if item['id'] == sel_id)
        
        st.markdown(f"**Dossier:** {reg['voornaam']} {reg['achternaam']}")
        col_a, col_b = st.columns(2)
        with col_a:
            n_status = st.selectbox("Status", ["Bevestigd", "In behandeling", "Afgehandeld", "Geannuleerd", "Verwezen"], index=0)
            behandeld = st.selectbox("Afgehandeld?", ["Nee", "Ja"], index=1 if reg.get('behandeld') == "Ja" else 0)
        with col_b:
            stappen = st.text_area("Vervolgstappen", value=reg.get('volgende_stappen', ""))
        
        verslag = st.text_area("Intern verslag", value=reg.get('intern_verslag', ""))
        mail_bericht = st.text_area("Bericht cliënt", value=reg.get('medewerker_toelichting', ""))
        
        if st.button("Wijzigingen Opslaan"):
            supabase.table("aanvragen").update({
                "status": n_status, "behandeld": behandeld,
                "volgende_stappen": stappen, "intern_verslag": verslag,
                "medewerker_toelichting": mail_bericht
            }).eq("id", sel_id).execute()
            if mail_bericht:
                stuur_mail(reg['email'], "Update DGW Centrum", mail_bericht)
            st.success("Dossier succesvol bijgewerkt.")
            st.rerun()

elif menu == "Rapportages":
    st.header("📊 Overzicht & Rapportages")
    res = supabase.table("aanvragen").select("*").execute()
    if res.data:
        df = pd.DataFrame(res.data)
        st.subheader("Statistieken")
        st.table(df['status'].value_counts())
        st.dataframe(df[['id', 'voornaam', 'achternaam', 'status', 'behandeld', 'intern_verslag']])

elif menu == "Agenda":
    st.header("📅 Afspraken (Ma & Wo)")
    res = supabase.table("aanvragen").select("*").execute()
    if res.data:
        events = [{"title": f"{r['voornaam']} {r['achternaam']} ({r['afspraak_tijd']})", "start": r['afspraak_datum'], "color": "#2e7d32"} for r in res.data]
        calendar(events=events, options={"initialView": "dayGridMonth"})

elif menu == "Systeembeheer":
    st.header("⚙️ Beheer Medewerkers")
    with st.expander("➕ Nieuwe Medewerker"):
        with st.form("add_user"):
            new_u = st.text_input("Gebruikersnaam")
            new_p = st.text_input("Wachtwoord", type="password")
            new_r = st.selectbox("Rol", ["Medewerker", "Admin"])
            if st.form_submit_button("Account Aanmaken"):
                supabase.table("medewerkers").insert({"gebruikersnaam": new_u, "wachtwoord": new_p, "rol": new_r}).execute()
                st.success(f"Medewerker {new_u} toegevoegd.")
                st.rerun()

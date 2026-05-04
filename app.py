import streamlit as st
from supabase import create_client, Client
import datetime
import pandas as pd
import smtplib
from email.mime.text import MIMEText
from email.mime.multipart import MIMEMultipart
from streamlit_calendar import calendar

# --- 1. CONFIGURATIE & STYLING ---
st.set_page_config(page_title="DGW Wanica Centrum", layout="wide")

# Database verbinding
supabase = create_client(st.secrets["SUPABASE_URL"], st.secrets["SUPABASE_KEY"])

st.markdown("""
    <style>
    .stButton>button { background-color: #2e7d32 !important; color: white !important; border-radius: 5px; }
    .css-1offfwp { background-color: #f0f2f6; }
    </style>
    """, unsafe_allow_html=True)

# --- HELPER FUNCTIES ---
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
        st.error(f"E-mail kon niet verzonden worden: {e}")

# --- 2. AUTHENTICATIE ---
if 'logged_in' not in st.session_state:
    st.session_state.update({'logged_in': False, 'role': None, 'user': None})

if not st.session_state.logged_in:
    st.sidebar.subheader("🔐 Inloggen Medewerker")
    res_m = supabase.table("medewerkers").select("*").execute()
    user_list = [u['gebruikersnaam'] for u in res_m.data] if res_m.data else []
    u_sel = st.sidebar.selectbox("Gebruikersnaam", ["---"] + user_list)
    p_inp = st.sidebar.text_input("Wachtwoord", type="password")
    if st.sidebar.button("Inloggen"):
        user_data = next((u for u in res_m.data if u['gebruikersnaam'] == u_sel), None)
        if user_data and user_data['wachtwoord'] == p_inp:
            st.session_state.update({'logged_in': True, 'role': user_data['rol'], 'user': u_sel})
            st.rerun()

# --- 3. MENU NAVIGATIE ---
menu_options = ["Nieuwe Aanvraag DGW"]
if st.session_state.logged_in:
    menu_options += ["Beheer Registraties", "Agenda", "Rapportages", "Systeembeheer"]
    if st.sidebar.button("🚪 Uitloggen"):
        st.session_state.logged_in = False
        st.rerun()

menu = st.sidebar.radio("Hoofdmenu", menu_options)

# --- 4. PAGINA'S ---

if menu == "Nieuwe Aanvraag DGW":
    st.header("📝 Nieuwe Aanvraag DGW Wanica Centrum")
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
    st.file_uploader("Documenten uploaden", accept_multiple_files=True)
    
    datum = st.date_input("Kies een datum (Maandag of Woensdag)", min_value=datetime.date.today())
    
    if datum.weekday() not in [0, 2]:
        st.error("⚠️ Afspraken kunnen alleen op maandag of woensdag worden gemaakt.")
    else:
        st.subheader("⏰ Beschikbare Tijden (Kwartier per afspraak)")
        tijdsblokken = []
        start_t = datetime.datetime.strptime("08:00", "%H:%M")
        eind_t = datetime.datetime.strptime("14:30", "%H:%M")
        while start_t <= eind_t:
            tijdsblokken.append(start_t.strftime("%H:%M"))
            start_t += datetime.timedelta(minutes=15)
        
        res_t = supabase.table("aanvragen").select("afspraak_tijd").eq("afspraak_datum", str(datum)).execute()
        bezet = [r['afspraak_tijd'] for r in res_t.data] if res_t.data else []
        
        cols = st.columns(6)
        for i, tijd in enumerate(tijdsblokken):
            is_bezet = tijd in bezet
            if cols[i % 6].button(f"🚫 {tijd}" if is_bezet else tijd, key=f"t_{tijd}", disabled=is_bezet):
                st.session_state.sel_tijd = tijd
        
        if 'sel_tijd' in st.session_state:
            st.success(f"Geselecteerd tijdstip: **{st.session_state.sel_tijd}**")

    if st.button("Registratie Verzenden"):
        if all([vnaam, anaam, email, id_nr, bericht]) and 'sel_tijd' in st.session_state:
            supabase.table("aanvragen").insert({
                "voornaam": vnaam, "achternaam": anaam, "email": email, "id_nummer": id_nr,
                "telefoon": tel, "lad_nummer": lad_nr, "afspraak_datum": str(datum),
                "afspraak_tijd": st.session_state.sel_tijd, "status": "In behandeling", "bericht": bericht
            }).execute()
            st.success("✅ Aanvraag succesvol verstuurd!")
            del st.session_state.sel_tijd
        else:
            st.error("Vul alle verplichte velden in en kies een tijdstip.")

elif menu == "Beheer Registraties":
    st.header("📋 Beheer Registraties")
    res = supabase.table("aanvragen").select("*").order('created_at', desc=True).execute()
    if res.data:
        df = pd.DataFrame(res.data)
        st.dataframe(df[['id', 'voornaam', 'achternaam', 'afspraak_datum', 'status']])
        
        sel_id = st.selectbox("Selecteer dossier ID voor bewerking", df['id'].tolist())
        reg = next(item for item in res.data if item['id'] == sel_id)
        
        with st.form("edit_form"):
            st.subheader(f"Dossier: {reg['voornaam']} {reg['achternaam']}")
            c1, c2 = st.columns(2)
            with c1:
                n_status = st.selectbox("Status", ["Bevestigd", "In behandeling", "Afgehandeld", "Geannuleerd", "Verwezen"], 
                                      index=["Bevestigd", "In behandeling", "Afgehandeld", "Geannuleerd", "Verwezen"].index(reg['status']))
                behandeld = st.selectbox("Afgehandeld?", ["Nee", "Ja"], index=1 if reg.get('behandeld') == "Ja" else 0)
            with c2:
                stappen = st.text_area("Volgende stappen", value=str(reg.get('volgende_stappen') or ""))
            
            verslag = st.text_area("Intern verslag", value=str(reg.get('intern_verslag') or ""))
            mail_tekst = st.text_area("Bericht naar cliënt", value=str(reg.get('medewerker_toelichting') or ""))
            
            if st.form_submit_button("Wijzigingen Opslaan"):
                supabase.table("aanvragen").update({
                    "status": n_status, "behandeld": behandeld,
                    "volgende_stappen": stappen, "intern_verslag": verslag,
                    "medewerker_toelichting": mail_tekst
                }).eq("id", sel_id).execute()
                if mail_tekst:
                    stuur_mail(reg['email'], "Update Grondzaken Dossier", mail_tekst)
                st.success("✅ Dossier bijgewerkt.")
                st.rerun()

elif menu == "Agenda":
    st.header("📅 Afspraken Agenda")
    res = supabase.table("aanvragen").select("*").execute()
    if res.data:
        events = [{"title": f"{r['voornaam']} {r['achternaam']}", "start": r['afspraak_datum'], "color": "#2e7d32"} for r in res.data]
        calendar(events=events, options={"initialView": "dayGridMonth"})

elif menu == "Rapportages":
    st.header("📊 Rapportages")
    res = supabase.table("aanvragen").select("*").execute()
    if res.data:
        df = pd.DataFrame(res.data)
        st.dataframe(df[['id', 'voornaam', 'achternaam', 'status', 'behandeld', 'afspraak_datum']])

elif menu == "Systeembeheer":
    st.header("⚙️ Systeembeheer")
    with st.expander("➕ Medewerker Toevoegen"):
        with st.form("add_user"):
            u = st.text_input("Gebruikersnaam")
            p = st.text_input("Wachtwoord", type="password")
            r = st.selectbox("Rol", ["Medewerker", "Admin"])
            if st.form_submit_button("Account Aanmaken"):
                supabase.table("medewerkers").insert({"gebruikersnaam": u, "wachtwoord": p, "rol": r}).execute()
                st.success(f"Medewerker {u} toegevoegd.")

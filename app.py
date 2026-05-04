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
st.set_page_config(page_title="DGW Wanica Portaal", layout="wide")

try:
    st.sidebar.image("orgineel logo Centrum.png", use_container_width=True)
except:
    st.sidebar.warning("Logo bestand niet gevonden.")

st.markdown("""
    <style>
    .tijd-knop { display: inline-block; padding: 10px; margin: 5px; border-radius: 5px; text-align: center; font-weight: bold; width: 100px; }
    .vrij { background-color: #e8f5e9; border: 2px solid #2e7d32; color: #2e7d32; }
    .bezet { background-color: #ffebee; border: 2px solid #c62828; color: #c62828; text-decoration: line-through; opacity: 0.6; }
    .status-card { padding: 15px; border-radius: 10px; border-left: 5px solid #2e7d32; background-color: #f9f9f9; margin-bottom: 10px; border: 1px solid #ddd; }
    .stButton>button { background-color: #2e7d32 !important; color: white !important; }
    </style>
    """, unsafe_allow_html=True)

# Verbinding met Supabase
supabase = create_client(st.secrets["SUPABASE_URL"], st.secrets["SUPABASE_KEY"])

# --- MAIL FUNCTIE ---
def stuur_mail(ontvanger, onderwerp, inhoud, bestanden=None):
    try:
        msg = MIMEMultipart()
        msg['Subject'] = onderwerp
        msg['From'] = f"DGW Wanica <{st.secrets['EMAIL_USER']}>"
        msg['To'] = ontvanger
        body = f"Geachte,\n\n{inhoud}\n\nMet vriendelijke groet,\nDistrictscommissariaat Wanica Centrum\nAfdeling Grondzaken (DGW)"
        msg.attach(MIMEText(body, 'plain'))
        if bestanden:
            for f in bestanden:
                f.seek(0)
                bijlage = MIMEApplication(f.read(), Name=f.name)
                bijlage['Content-Disposition'] = f'attachment; filename="{f.name}"'
                msg.attach(bijlage)
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
menu_options = ["Registratie DGW"]
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
if menu == "Registratie DGW":
    st.header("📝 Registratie Dienst Grondzaken Wanica")
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
    
    bericht = st.text_area("Omschrijving klacht/verzoek *")
    uploaded_files = st.file_uploader("Documenten uploaden", accept_multiple_files=True)
    
    st.write("---")
    st.subheader("📅 Kies uw afspraakmoment")
    datum = st.date_input("Selecteer datum", min_value=datetime.date.today())
    
    if datum.weekday() in [0, 2]: # Maandag en Woensdag
        tijden = [f"{h:02d}:{m:02d}" for h in range(7, 15) for m in [0, 15, 30, 45] if "07:00" <= f"{h:02d}:{m:02d}" <= "14:45"]
        res = supabase.table("aanvragen").select("afspraak_tijd").eq("afspraak_datum", str(datum)).execute()
        bezet = [r['afspraak_tijd'] for r in res.data] if res.data else []
        
        st.write("Beschikbare tijden:")
        cols = st.columns(4)
        for i, t in enumerate(tijden):
            with cols[i % 4]:
                if t in bezet:
                    st.markdown(f'<div class="tijd-knop bezet">{t}</div>', unsafe_allow_html=True)
                else:
                    if st.button(f"Kies {t}", key=f"btn_{t}"):
                        st.session_state.selected_time = t
        
        if 'selected_time' in st.session_state:
            st.success(f"Gekozen: **{st.session_state.selected_time}**")
            if st.button("Definitief Verzenden"):
                if all([vnaam, anaam, email, id_nr, bericht]):
                    supabase.table("aanvragen").insert({
                        "voornaam": vnaam, "achternaam": anaam, "email": email, "id_nummer": id_nr, 
                        "woonadres": woonadres, "telefoon": tel, "lad_nummer": lad_nr, 
                        "afspraak_datum": str(datum), "afspraak_tijd": st.session_state.selected_time, 
                        "status": "In behandeling", "bericht": bericht
                    }).execute()
                    stuur_mail(email, "Bevestiging Registratie DGW", f"Uw afspraak bij Dienst Grondzaken Wanica op {datum} om {st.session_state.selected_time} is ontvangen.")
                    stuur_mail(st.secrets["EMAIL_USER"], f"NIEUWE REGISTRATIE DGW: {vnaam}", f"Nieuwe registratie van {vnaam} {anaam}.", bestanden=uploaded_files)
                    st.success("✅ Registratie succesvol verzonden!")
                    st.balloons()
                    del st.session_state.selected_time
                else: st.error("Vul alle velden in.")
    else: st.error("⚠️ Afspraken uitsluitend op Maandag en Woensdag.")

elif menu == "Medewerker Portaal":
    st.header("📋 Beheer Registraties")
    res = supabase.table("aanvragen").select("*").order('created_at', desc=True).execute()
    if res.data:
        df = pd.DataFrame(res.data)
        st.dataframe(df)
        sel_id = st.selectbox("Selecteer ID", df['id'].tolist())
        n_status = st.selectbox("Nieuwe Status", ["Bevestigd", "In behandeling", "Geannuleerd", "Verwezen"])
        toelichting = st.text_area("Toelichting voor cliënt")
        if st.button("Update & Mail"):
            supabase.table("aanvragen").update({"status": n_status}).eq("id", sel_id).execute()
            aanvraag = next(item for item in res.data if item['id'] == sel_id)
            stuur_mail(aanvraag['email'], f"Update Registratie DGW: {n_status}", f"De status van uw registratie bij Dienst Grondzaken Wanica is gewijzigd naar {n_status}. {toelichting}")
            st.success("Gereed!")
            st.rerun()

elif menu == "Agenda Overzicht":
    st.header("📅 Interactieve Agenda")
    res = supabase.table("aanvragen").select("*").execute()
    
    if res.data:
        calendar_events = []
        for r in res.data:
            color = "#2e7d32" if r['status'] == "Bevestigd" else "#f39c12"
            if r['status'] == "Geannuleerd": color = "#c62828"
            
            calendar_events.append({
                "title": f"{r['afspraak_tijd']} - {r['voornaam']}",
                "start": r['afspraak_datum'],
                "end": r['afspraak_datum'],
                "color": color,
                "allDay": True,
                "extendedProps": r
            })

        calendar_options = {
            "headerToolbar": {"left": "prev,next today", "center": "title", "right": "dayGridMonth,listWeek"},
            "initialView": "dayGridMonth",
            "selectable": True,
        }
        
        cal = calendar(events=calendar_events, options=calendar_options)
        
        if cal.get("callback") == "dateClick" or cal.get("dateClick"):
            clicked_date = cal["dateClick"]["date"].split("T")[0]
            st.subheader(f"Details voor {clicked_date}")
            df = pd.DataFrame(res.data)
            dag_data = df[df['afspraak_datum'] == clicked_date].sort_values('afspraak_tijd')
            
            if not dag_data.empty:
                for _, r in dag_data.iterrows():
                    st.markdown(f"""
                    <div class="status-card">
                        <b>🕒 {r['afspraak_tijd']}</b> | {r['voornaam']} {r['achternaam']}<br>
                        📞 {r['telefoon']} | 📧 {r['email']}<br>
                        <b>Status: {r['status']}</b><br>
                        📄 {r['bericht']}
                    </div>
                    """, unsafe_allow_html=True)
            else:
                st.info("Geen registraties op deze dag.")

elif menu == "Rapportages":
    st.header("📊 Statistieken")
    res = supabase.table("aanvragen").select("*").execute()
    if res.data:
        df = pd.DataFrame(res.data)
        st.bar_chart(df['status'].value_counts())

elif menu == "Admin Instellingen":
    st.header("⚙️ Admin")
    with st.expander("Nieuwe Medewerker"):
        u, p, r = st.text_input("Naam"), st.text_input("Wachtwoord"), st.selectbox("Rol", ["Medewerker", "Admin"])
        if st.button("Toevoegen"):
            supabase.table("medewerkers").insert({"gebruikersnaam": u, "wachtwoord": p, "rol": r}).execute()
            st.rerun()

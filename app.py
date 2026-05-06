import streamlit as st
from supabase import create_client, Client
import datetime
import pandas as pd
import smtplib
from email.mime.text import MIMEText
from email.mime.multipart import MIMEMultipart
from email.mime.application import MIMEApplication

# --- 1. CONFIGURATIE ---
st.set_page_config(page_title="Registratie Dienst Grondzaken Wanica Centrum", layout="wide")

# Verbinding met Supabase
supabase = create_client(st.secrets["SUPABASE_URL"], st.secrets["SUPABASE_KEY"])

# Email instellingen
EMAIL_USER = "wanicacentrum.gz@gmail.com"
EMAIL_PASS = "kmebjorjujxwqbvo"

# --- 2. STYLING (Groen/Wit Huisstijl) ---
st.markdown("""
    <style>
    .stApp { background-color: white; }
    h1, h2, h3 { color: #2e7d32; font-weight: bold; }
    .stButton>button { background-color: #2e7d32; color: white; border-radius: 8px; font-weight: bold; }
    .stSidebar { background-color: #f1f8e9; }
    /* Specifieke styling voor de rode verwijderknop */
    button[data-testid="stBaseButton-secondary"] {
        background-color: #d32f2f !important;
        color: white !important;
        border: none !important;
    }
    </style>
""", unsafe_allow_html=True)

# --- 3. EMAIL FUNCTIE ---
def stuur_mail(ontvanger, onderwerp, inhoud, bestanden=None):
    msg = MIMEMultipart()
    msg['From'] = f"Dienst Grondzaken Wanica Centrum <{EMAIL_USER}>"
    msg['To'] = ontvanger
    msg['Subject'] = onderwerp
    
    html_inhoud = f"""
    <html>
        <body style="font-family: Arial, sans-serif; color: #333;">
            <div style="background-color: #2e7d32; padding: 20px; color: white; text-align: center;">
                <h2>Dienst Grondzaken Wanica Centrum</h2>
            </div>
            <div style="padding: 20px; border: 1px solid #ddd;">
                {inhoud.replace('\\n', '<br>')}
            </div>
        </body>
    </html>
    """
    msg.attach(MIMEText(html_inhoud, 'html'))
    
    if bestanden:
        for f in bestanden:
            f.seek(0)
            part = MIMEApplication(f.read(), Name=f.name)
            part['Content-Disposition'] = f'attachment; filename="{f.name}"'
            msg.attach(part)
            
    try:
        server = smtplib.SMTP('smtp.gmail.com', 587)
        server.starttls()
        server.login(EMAIL_USER, EMAIL_PASS)
        server.send_message(msg)
        server.quit()
        return True
    except: return False

# --- 4. STATE INITIALISATIE ---
if 'logged_in' not in st.session_state:
    st.session_state.update({'logged_in': False, 'role': None, 'user': None})
if 'selected_time' not in st.session_state:
    st.session_state.selected_time = None

# --- 5. MENU STRUCTUUR ---
menu_options = ["📝 Nieuwe Registratie"]
if st.session_state.logged_in:
    menu_options += ["📋 Dossierbeheer", "📊 Rapportages", "📅 Agenda", "⚙️ Systeembeheer"]

menu = st.sidebar.radio("Hoofdmenu", menu_options)

# Sidebar voor Inloggen/Uitloggen
if st.session_state.logged_in:
    st.sidebar.write(f"Ingelogd: **{st.session_state.user}**")
    if st.sidebar.button("🚪 Afmelden"):
        st.session_state.update({'logged_in': False, 'role': None, 'user': None})
        st.rerun()
else:
    with st.sidebar.expander("🔐 Medewerker Login"):
        res_m = supabase.table("medewerkers").select("*").execute()
        u_list = [u['gebruikersnaam'] for u in res_m.data] if res_m.data else []
        u_sel = st.selectbox("Gebruiker", ["---"] + u_list)
        p_inp = st.text_input("Wachtwoord", type="password")
        if st.button("Inloggen"):
            user = next((u for u in res_m.data if u['gebruikersnaam'] == u_sel), None)
            if user and user['wachtwoord'] == p_inp:
                st.session_state.update({'logged_in': True, 'role': str(user['rol']).lower(), 'user': u_sel})
                st.rerun()
            else:
                st.error("Onjuiste gegevens.")

# --- 6. PAGINA LOGICA ---

# A. CLIENT REGISTRATIE
if menu == "📝 Nieuwe Registratie":
    col_l, col_r = st.columns([1, 4])
    with col_l:
        st.image("https://raw.githubusercontent.com/bhikhienadeem-art/dgw-app/main/orgineel%20logo%20Centrum.png", width=120)
    with col_r:
        st.title("Registratie Grondzaken Wanica Centrum")
    
    st.divider()
    c1, c2 = st.columns(2)
    with c1:
        vnaam = st.text_input("Voornaam *")
        anaam = st.text_input("Achternaam *")
        adres = st.text_input("Woonadres *")
        email = st.text_input("E-mailadres *")
    with c2:
        id_nr = st.text_input("ID-nummer *")
        tel = st.text_input("Telefoonnummer *")
        lad = st.text_input("LAD-nummer")
    
    bericht = st.text_area("Omschrijving klacht/verzoek *")
    docs = st.file_uploader("Documenten uploaden", accept_multiple_files=True)
    
    st.divider()
    st.subheader("📅 Afspraak inplannen (Ma & Wo)")
    datum = st.date_input("Kies datum", min_value=datetime.date.today())
    
    if datum.weekday() in [0, 2]:
        tijden = [f"{h:02d}:{m:02d}" for h in range(8, 15) for m in (0, 15, 30, 45) if not (h == 14 and m > 30)]
        cols = st.columns(6)
        for idx, t in enumerate(tijden):
            with cols[idx % 6]:
                if st.button(t, key=f"t_{t}", type="primary" if st.session_state.selected_time == t else "secondary", use_container_width=True):
                    st.session_state.selected_time = t
                    st.rerun()
    else:
        st.warning("Bezoekafspraken zijn enkel op maandag en woensdag.")

    if st.button("✅ Registratie Indienen", type="primary", use_container_width=True):
        if all([vnaam, anaam, adres, email, id_nr, bericht]) and st.session_state.selected_time:
            data = {"voornaam": vnaam, "achternaam": anaam, "woonadres": adres, "email": email, "id_nummer": id_nr, "telefoon": tel, "lad_nummer": lad, "afspraak_datum": str(datum), "afspraak_tijd": st.session_state.selected_time, "status": "In behandeling", "bericht": bericht}
            supabase.table("aanvragen").insert(data).execute()
            st.success("Registratie succesvol!")
            st.session_state.selected_time = None
        else: st.error("Vul alle velden in.")

# B. DOSSIERBEHEER (INGELOGD)
elif menu == "📋 Dossierbeheer" and st.session_state.logged_in:
    st.header("📋 Dossierbeheer")
    res = supabase.table("aanvragen").select("*").order('id', desc=True).execute()
    if res.data:
        df = pd.DataFrame(res.data)
        st.dataframe(df[['id', 'voornaam', 'achternaam', 'status', 'afspraak_datum']], hide_index=True, use_container_width=True)
        
        sel_id = st.selectbox("Selecteer Dossier", df['id'].tolist())
        d = next(item for item in res.data if item['id'] == sel_id)
        
        st.divider()
        ce1, ce2 = st.columns(2)
        with ce1:
            st.subheader("📝 Status & Datum")
            n_status = st.selectbox("Status", ["In behandeling", "Wacht op documenten", "Bevestigd", "Afgehandeld"], index=["In behandeling", "Wacht op documenten", "Bevestigd", "Afgehandeld"].index(d['status']) if d['status'] in ["In behandeling", "Wacht op documenten", "Bevestigd", "Afgehandeld"] else 0)
            n_datum = st.date_input("Datum", value=datetime.datetime.strptime(d['afspraak_datum'], '%Y-%m-%d').date())
            n_tijd = st.text_input("Tijd", value=d['afspraak_tijd'])
        with ce2:
            st.subheader("💬 Notities")
            toelichting = st.text_area("Interne Notitie", value=d.get('medewerker_toelichting', ""))
            mail_tekst = st.text_area("Bericht naar Cliënt")

        b1, b2 = st.columns(2)
        with b1:
            if st.button("💾 Bijwerken & Mailen", use_container_width=True):
                supabase.table("aanvragen").update({"status": n_status, "afspraak_datum": str(n_datum), "afspraak_tijd": n_tijd, "medewerker_toelichting": toelichting}).eq("id", sel_id).execute()
                if mail_tekst:
                    mail_body = f"Uw dossier is bijgewerkt naar: {n_status}.\\nAfspraak: {n_datum} om {n_tijd}.\\n\\n{mail_tekst}"
                    stuur_mail(d['email'], "Update Dossier", mail_body)
                st.success("Bijgewerkt!")
                st.rerun()
        with b2:
            if st.button(f"🗑️ Verwijder Dossier #{sel_id}", type="secondary", use_container_width=True):
                supabase.table("aanvragen").delete().eq("id", sel_id).execute()
                st.rerun()

# C. OVERIGE PAGINA'S
elif menu == "📊 Rapportages" and st.session_state.logged_in:
    res = supabase.table("aanvragen").select("*").execute()
    if res.data: st.dataframe(pd.DataFrame(res.data), use_container_width=True)

elif menu == "📅 Agenda" and st.session_state.logged_in:
    res = supabase.table("aanvragen").select("voornaam, achternaam, afspraak_datum, afspraak_tijd, status").execute()
    if res.data: st.table(pd.DataFrame(res.data).sort_values('afspraak_datum'))

elif menu == "⚙️ Systeembeheer" and st.session_state.logged_in:
    if st.session_state.role == 'admin':
        st.header("⚙️ Systeembeheer")
        # Hier kun je medewerkers toevoegen/verwijderen zoals in je eerdere code
    else: st.error("Geen admin rechten.")

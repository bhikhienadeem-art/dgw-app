import streamlit as st
from supabase import create_client, Client
import datetime
import pandas as pd
import plotly.express as px
import smtplib
from email.mime.text import MIMEText
from email.mime.multipart import MIMEMultipart
from email.mime.application import MIMEApplication

# --- 1. CONFIGURATIE ---
st.set_page_config(page_title="Dienst Grondzaken Wanica Centrum", layout="wide")

supabase = create_client(st.secrets["SUPABASE_URL"], st.secrets["SUPABASE_KEY"])

EMAIL_USER = "wanicacentrum.gz@gmail.com"
EMAIL_PASS = "kmebjorjujxwqbvo"

# --- 2. STYLING (DEFINITIEVE LEESBAARHEID) ---
st.markdown("""
    <style>
    .stApp { background-color: white; }
    h1, h2, h3, .stTitle { color: #1b5e20 !important; font-family: 'Segoe UI', sans-serif; font-weight: bold; }
    [data-testid="stSidebar"] { background-color: #f1f8e9 !important; }
    [data-testid="stSidebar"] .st-emotion-cache-17l69uz, [data-testid="stSidebar"] p, [data-testid="stSidebar"] label {
        color: #1b5e20 !important; font-weight: bold !important;
    }
    .stTextInput>div>div>input, .stTextArea>div>div>textarea, .stSelectbox>div>div>div {
        background-color: white !important; color: black !important; border: 2px solid #2e7d32 !important; border-radius: 8px !important;
    }
    div.stButton > button { width: 100%; border-radius: 10px; background-color: #2e7d32; color: white; font-weight: bold; height: 3.5em; }
    </style>
""", unsafe_allow_html=True)

# --- 3. EMAIL FUNCTIE ---
def stuur_mail(ontvanger, onderwerp, inhoud, bestanden=None):
    msg = MIMEMultipart()
    msg['From'] = f"Dienst Grondzaken Wanica Centrum <{EMAIL_USER}>"
    msg['To'] = ontvanger
    msg['Subject'] = onderwerp
    html = f"<html><body style='font-family: Arial;'>{inhoud.replace('\\n', '<br>')}</body></html>"
    msg.attach(MIMEText(html, 'html'))
    if bestanden:
        for f in bestanden:
            f.seek(0)
            part = MIMEApplication(f.read(), Name=f.name)
            part['Content-Disposition'] = f'attachment; filename="{f.name}"'
            msg.attach(part)
    try:
        server = smtplib.SMTP('smtp.gmail.com', 587)
        server.starttls(); server.login(EMAIL_USER, EMAIL_PASS)
        server.send_message(msg); server.quit()
        return True
    except: return False

# --- 4. STATE & LOGIN ---
if 'logged_in' not in st.session_state:
    st.session_state.update({'logged_in': False, 'role': None, 'user': None})
if 'selected_time' not in st.session_state:
    st.session_state.selected_time = None

# --- 5. NAVIGATIE ---
menu_options = ["📝 Nieuwe Registratie"]
if st.session_state.logged_in:
    menu_options += ["📋 Dossierbeheer", "📊 Rapportages", "📅 Agenda", "⚙️ Systeembeheer"]

menu = st.sidebar.radio("Hoofdmenu", menu_options)

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

# --- 6. REGISTRATIE ---
if menu == "📝 Nieuwe Registratie":
    st.image("https://raw.githubusercontent.com/bhikhienadeem-art/dgw-app/main/orgineel%20logo%20Centrum.png", width=120)
    st.title("Registratie Grondzaken")
    vnaam = st.text_input("Voornaam *")
    anaam = st.text_input("Achternaam *")
    email = st.text_input("E-mailadres *")
    id_nr = st.text_input("ID-nummer *")
    bericht = st.text_area("Omschrijving klacht *")
    
    st.subheader("📅 Afspraak (Ma & Wo)")
    datum = st.date_input("Datum", min_value=datetime.date.today())
    if datum.weekday() in [0, 2]:
        tijden = [f"{h:02d}:{m:02d}" for h in range(8, 15) for m in (0, 30)]
        cols = st.columns(4)
        for idx, t in enumerate(tijden):
            if cols[idx % 4].button(t, key=f"t_{t}", type="primary" if st.session_state.selected_time == t else "secondary"):
                st.session_state.selected_time = t; st.rerun()
    
    if st.button("✅ VERZENDEN"):
        if all([vnaam, email, id_nr, bericht]) and st.session_state.selected_time:
            data = {"voornaam": vnaam, "achternaam": anaam, "email": email, "id_nummer": id_nr, "afspraak_datum": str(datum), "afspraak_tijd": st.session_state.selected_time, "status": "In behandeling", "bericht": bericht}
            supabase.table("aanvragen").insert(data).execute()
            st.success("Registratie succesvol!"); st.session_state.selected_time = None
        else: st.error("Vul alle velden in.")

# --- 7. DOSSIERBEHEER (VOLLEDIG HERSTELD) ---
elif menu == "📋 Dossierbeheer":
    st.header("📋 Dossierbeheer")
    res = supabase.table("aanvragen").select("*").order('id', desc=True).execute()
    if res.data:
        df = pd.DataFrame(res.data)
        st.dataframe(df[['id', 'voornaam', 'achternaam', 'status', 'afspraak_datum']], use_container_width=True)
        sel_id = st.selectbox("Selecteer Dossier ID", df['id'].tolist())
        d = next(item for item in res.data if item['id'] == sel_id)
        
        st.markdown(f"### 📄 Dossier #{sel_id}: {d['voornaam']} {d['achternaam']}")
        st.write(f"**ID-nummer:** {d['id_nummer']} | **E-mail:** {d['email']}")
        st.info(f"**Klacht:** {d['bericht']}")
        
        n_status = st.selectbox("Update Status", ["In behandeling", "Bevestigd", "Afgehandeld"], index=0)
        toelichting = st.text_area("Interne Notitie", value=d.get('medewerker_toelichting', ""))
        
        c1, c2 = st.columns(2)
        if c1.button("💾 BIJWERKEN"):
            supabase.table("aanvragen").update({"status": n_status, "medewerker_toelichting": toelichting}).eq("id", sel_id).execute()
            st.success("Dossier bijgewerkt."); st.rerun()
        if c2.button(f"🗑️ VERWIJDER DOSSIER #{sel_id}", type="secondary"):
            supabase.table("aanvragen").delete().eq("id", sel_id).execute(); st.rerun()

# --- 8. SYSTEEMBEHEER (INCLUSIEF VERWIJDEREN) ---
elif menu == "⚙️ Systeembeheer":
    st.header("⚙️ Systeembeheer")
    if st.session_state.role == 'admin':
        st.subheader("Medewerkersbeheer")
        with st.expander("➕ Nieuwe Medewerker Toevoegen"):
            n_user = st.text_input("Gebruikersnaam")
            n_pass = st.text_input("Wachtwoord", type="password")
            n_rol = st.selectbox("Rol", ["medewerker", "admin"])
            if st.button("💾 Medewerker Opslaan"):
                supabase.table("medewerkers").insert({"gebruikersnaam": n_user, "wachtwoord": n_pass, "rol": n_rol}).execute()
                st.success("Medewerker toegevoegd."); st.rerun()
        
        st.divider()
        res_m = supabase.table("medewerkers").select("*").execute()
        if res_m.data:
            df_m = pd.DataFrame(res_m.data)
            st.dataframe(df_m[['id', 'gebruikersnaam', 'rol']], use_container_width=True)
            
            sel_m_id = st.selectbox("Selecteer Medewerker ID om te verwijderen", df_m['id'].tolist())
            if st.button(f"🗑️ Verwijder Medewerker #{sel_m_id}", type="secondary"):
                supabase.table("medewerkers").delete().eq("id", sel_m_id).execute()
                st.success("Medewerker verwijderd."); st.rerun()
    else: st.error("U heeft geen admin-rechten voor deze pagina.")

# --- 9. RAPPORTAGES & AGENDA ---
elif menu == "📊 Rapportages":
    st.header("📊 Dashboard")
    res = supabase.table("aanvragen").select("*").execute()
    if res.data:
        df = pd.DataFrame(res.data)
        st.plotly_chart(px.pie(df, names='status', title="Status Verdeling", color_discrete_sequence=['#2e7d32', '#81c784', '#d32f2f']), use_container_width=True)

elif menu == "📅 Agenda":
    st.header("📅 Agenda")
    res = supabase.table("aanvragen").select("voornaam, achternaam, afspraak_datum, afspraak_tijd").execute()
    if res.data: st.table(pd.DataFrame(res.data).sort_values('afspraak_datum'))

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
st.set_page_config(page_title="Registratie Dienst Grondzaken Wanica Centrum", layout="wide")

supabase = create_client(st.secrets["SUPABASE_URL"], st.secrets["SUPABASE_KEY"])

EMAIL_USER = "wanicacentrum.gz@gmail.com"
EMAIL_PASS = "kmebjorjujxwqbvo"

# --- 2. STYLING (HERSTEL LEESBAARHEID) ---
st.markdown("""
    <style>
    .stApp { background-color: white; }
    h1, h2, h3 { color: #2e7d32; font-family: 'Segoe UI', sans-serif; }
    
    /* Herstel leesbaarheid: Witte achtergrond, zwarte tekst voor alle velden */
    .stTextInput>div>div>input, .stTextArea>div>div>textarea, .stSelectbox>div>div>div {
        background-color: white !important;
        color: black !important;
        border: 1px solid #2e7d32 !important;
        border-radius: 8px !important;
    }
    
    /* Labels duidelijk maken */
    label { color: #2e7d32 !important; font-weight: bold !important; }

    /* Grote groene knoppen voor mobiele gebruiksvriendelijkheid */
    div.stButton > button {
        width: 100%;
        border-radius: 10px;
        background-color: #2e7d32;
        color: white;
        font-weight: bold;
        height: 3.5em;
        border: none;
    }
    
    .stSidebar { background-color: #f1f8e9; }
    </style>
""", unsafe_allow_html=True)

# --- 3. EMAIL FUNCTIE ---
def stuur_mail(ontvanger, onderwerp, inhoud, bestanden=None):
    msg = MIMEMultipart()
    msg['From'] = f"Dienst Grondzaken Wanica Centrum <{EMAIL_USER}>"
    msg['To'] = ontvanger
    msg['Subject'] = onderwerp
    html_inhoud = f"<html><body style='font-family: Arial;'>{inhoud.replace('\\n', '<br>')}</body></html>"
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
    st.sidebar.write(f"Medewerker: **{st.session_state.user}**")
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

# --- 6. REGISTRATIE PAGINA ---
if menu == "📝 Nieuwe Registratie":
    st.image("https://raw.githubusercontent.com/bhikhienadeem-art/dgw-app/main/orgineel%20logo%20Centrum.png", width=120)
    st.title("Registratie Grondzaken")
    
    vnaam = st.text_input("Voornaam *")
    anaam = st.text_input("Achternaam *")
    id_nr = st.text_input("ID-nummer *")
    email = st.text_input("E-mailadres *")
    tel = st.text_input("Telefoonnummer")
    bericht = st.text_area("Omschrijving klacht/verzoek *")
    docs = st.file_uploader("Documenten uploaden", accept_multiple_files=True)
    
    st.subheader("📅 Afspraak (Ma & Wo)")
    datum = st.date_input("Kies datum", min_value=datetime.date.today())
    
    if datum.weekday() in [0, 2]:
        tijden = [f"{h:02d}:{m:02d}" for h in range(8, 15) for m in (0, 15, 30, 45) if not (h == 14 and m > 30)]
        cols = st.columns(4)
        for idx, t in enumerate(tijden):
            if cols[idx % 4].button(t, key=f"t_{t}", type="primary" if st.session_state.selected_time == t else "secondary"):
                st.session_state.selected_time = t
                st.rerun()
    else:
        st.warning("Afspraken zijn enkel op maandag en woensdag.")

    if st.button("✅ REGISTRATIE INDIENEN"):
        if all([vnaam, anaam, email, id_nr, bericht]) and st.session_state.selected_time:
            data = {"voornaam": vnaam, "achternaam": anaam, "email": email, "id_nummer": id_nr, "telefoon": tel, "afspraak_datum": str(datum), "afspraak_tijd": st.session_state.selected_time, "status": "In behandeling", "bericht": bericht}
            supabase.table("aanvragen").insert(data).execute()
            stuur_mail(EMAIL_USER, f"Nieuwe Klacht: {vnaam}", f"Nieuwe registratie ontvangen van {vnaam} {anaam}.", docs)
            st.success("Succesvol ingediend!")
            st.session_state.selected_time = None
        else:
            st.error("Vul alle verplichte velden in.")

# --- 7. DASHBOARD & VISUALISATIE ---
elif menu == "📊 Rapportages":
    st.header("📊 Management Dashboard")
    res = supabase.table("aanvragen").select("*").execute()
    if res.data:
        df = pd.DataFrame(res.data)
        
        c1, c2, c3 = st.columns(3)
        c1.metric("Totaal", len(df))
        c2.metric("Openstaand", len(df[df['status'] == 'In behandeling']))
        c3.metric("Gereed", len(df[df['status'] == 'Afgehandeld']))

        col_left, col_right = st.columns(2)
        with col_left:
            fig_pie = px.pie(df, names='status', title="Status Verdeling", color_discrete_sequence=['#2e7d32', '#81c784', '#d32f2f'])
            st.plotly_chart(fig_pie, use_container_width=True)
        with col_right:
            df['datum'] = pd.to_datetime(df['created_at']).dt.date
            trend = df.groupby('datum').size().reset_index(name='aantal')
            fig_line = px.bar(trend, x='datum', y='aantal', title="Aanvragen per dag", color_discrete_sequence=['#2e7d32'])
            st.plotly_chart(fig_line, use_container_width=True)
            
        st.dataframe(df[['id_nummer', 'achternaam', 'status', 'afspraak_datum']], use_container_width=True)

# --- OVERIGE SECTIES ---
elif menu == "📋 Dossierbeheer":
    st.header("📋 Dossierbeheer")
    res = supabase.table("aanvragen").select("*").order('id', desc=True).execute()
    if res.data:
        df = pd.DataFrame(res.data)
        sel_id = st.selectbox("Selecteer Dossier ID", df['id'].tolist())
        d = next(item for item in res.data if item['id'] == sel_id)
        st.write(f"**Cliënt:** {d['voornaam']} {d['achternaam']}")
        if st.button(f"🗑️ Verwijder Dossier #{sel_id}"):
            supabase.table("aanvragen").delete().eq("id", sel_id).execute()
            st.rerun()

elif menu == "📅 Agenda":
    st.header("📅 Bezoekagenda")
    res = supabase.table("aanvragen").select("voornaam, achternaam, afspraak_datum, afspraak_tijd, status").execute()
    if res.data:
        st.table(pd.DataFrame(res.data).sort_values('afspraak_datum'))

elif menu == "⚙️ Systeembeheer":
    st.header("⚙️ Systeembeheer")
    if st.session_state.role == 'admin':
        st.write("Medewerkersbeheer actief.")
    else:
        st.error("Geen admin rechten.")

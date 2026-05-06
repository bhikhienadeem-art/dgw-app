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

# --- 2. STYLING (HERSTEL LEESBAARHEID HOOFDMENU & REGISTRATIE) ---
st.markdown("""
    <style>
    .stApp { background-color: white; }
    
    /* TITELS & KOPPEN (Registratie Grondzaken) */
    h1, h2, h3, .stTitle { 
        color: #1b5e20 !important; 
        font-family: 'Segoe UI', sans-serif; 
        font-weight: bold;
    }
    
    /* HOOFDMENU LEESBAAR MAKEN (Zijbalk) */
    [data-testid="stSidebar"] {
        background-color: #f1f8e9 !important;
    }
    
    /* Navigatie labels en Radio-button teksten */
    [data-testid="stSidebar"] .st-emotion-cache-17l69uz, 
    [data-testid="stSidebar"] p, 
    [data-testid="stSidebar"] label {
        color: #1b5e20 !important; 
        font-weight: bold !important;
        font-size: 1rem !important;
    }

    /* INPUT VELDEN (Witte boxen met zwarte tekst) */
    .stTextInput>div>div>input, .stTextArea>div>div>textarea, .stSelectbox>div>div>div {
        background-color: white !important;
        color: black !important;
        border: 2px solid #2e7d32 !important;
        border-radius: 8px !important;
    }
    
    /* GROTE GROENE KNOPPEN */
    div.stButton > button {
        width: 100%;
        border-radius: 10px;
        background-color: #2e7d32;
        color: white;
        font-weight: bold;
        height: 3.5em;
        border: none;
    }

    /* Specifieke kleur voor Afmelden-knop */
    div.stButton > button:contains("Afmelden") {
        background-color: #d32f2f !important;
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

# --- 4. STATE & LOGIN ---
if 'logged_in' not in st.session_state:
    st.session_state.update({'logged_in': False, 'role': None, 'user': None})
if 'selected_time' not in st.session_state:
    st.session_state.selected_time = None

# --- 5. MENU ---
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

# --- 6. REGISTRATIE PAGINA ---
if menu == "📝 Nieuwe Registratie":
    st.image("https://raw.githubusercontent.com/bhikhienadeem-art/dgw-app/main/orgineel%20logo%20Centrum.png", width=120)
    st.title("Registratie Dienst Grondzaken Wanica Centrum")
    
    vnaam = st.text_input("Voornaam *")
    anaam = st.text_input("Achternaam *")
    adres = st.text_input("Woonadres *")
    email = st.text_input("E-mailadres *")
    id_nr = st.text_input("ID-nummer *")
    tel = st.text_input("Telefoonnummer")
    lad = st.text_input("LAD-nummer")
    bericht = st.text_area("Omschrijving klacht/verzoek *")
    docs = st.file_uploader("Documenten uploaden", accept_multiple_files=True)
    
    st.subheader("📅 Afspraak plannen (Ma & Wo)")
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
            data = {"voornaam": vnaam, "achternaam": anaam, "woonadres": adres, "email": email, "id_nummer": id_nr, "telefoon": tel, "lad_nummer": lad, "afspraak_datum": str(datum), "afspraak_tijd": st.session_state.selected_time, "status": "In behandeling", "bericht": bericht}
            supabase.table("aanvragen").insert(data).execute()
            stuur_mail(EMAIL_USER, f"Nieuwe Klacht: {vnaam}", f"Nieuwe registratie van {vnaam} {anaam}.", docs)
            st.success("Succesvol ingediend!")
            st.session_state.selected_time = None
        else:
            st.error("Vul alle verplichte velden in en kies een tijd.")

# --- 7. DOSSIERBEHEER (HERSTELD NAAR ORIGINEEL) ---
elif menu == "📋 Dossierbeheer":
    st.header("📋 Dossierbeheer")
    res = supabase.table("aanvragen").select("*").order('id', desc=True).execute()
    if res.data:
        df = pd.DataFrame(res.data)
        st.dataframe(df[['id', 'voornaam', 'achternaam', 'status', 'afspraak_datum']], hide_index=True, use_container_width=True)
        
        sel_id = st.selectbox("Selecteer Dossier ID", df['id'].tolist())
        d = next(item for item in res.data if item['id'] == sel_id)
        
        st.markdown("### 📄 Dossier Informatie")
        c1, c2 = st.columns(2)
        with c1:
            st.write(f"**Naam:** {d['voornaam']} {d['achternaam']}")
            st.write(f"**ID-nummer:** {d['id_nummer']}")
            st.write(f"**LAD-nummer:** {d.get('lad_nummer', 'Nvt')}")
        with c2:
            st.write(f"**E-mail:** {d['email']}")
            st.write(f"**Telefoon:** {d.get('telefoon', 'Nvt')}")
            st.write(f"**Afspraak:** {d['afspraak_datum']} om {d['afspraak_tijd']}")
        
        st.info(f"**Bericht cliënt:** {d['bericht']}")
        st.divider()

        # Update sectie
        u1, u2 = st.columns(2)
        with u1:
            n_status = st.selectbox("Nieuwe Status", ["In behandeling", "Wacht op documenten", "Bevestigd", "Afgehandeld"], index=["In behandeling", "Wacht op documenten", "Bevestigd", "Afgehandeld"].index(d['status']) if d['status'] in ["In behandeling", "Wacht op documenten", "Bevestigd", "Afgehandeld"] else 0)
            n_datum = st.date_input("Nieuwe Datum", value=datetime.datetime.strptime(d['afspraak_datum'], '%Y-%m-%d').date())
        with u2:
            toelichting = st.text_area("Interne Notitie", value=d.get('medewerker_toelichting', ""))
            mail_tekst = st.text_area("Bericht aan Cliënt (per mail)")

        btn_c1, btn_c2 = st.columns(2)
        with btn_c1:
            if st.button("💾 BIJWERKEN & MAILEN"):
                supabase.table("aanvragen").update({"status": n_status, "afspraak_datum": str(n_datum), "medewerker_toelichting": toelichting}).eq("id", sel_id).execute()
                if mail_tekst:
                    mail_inhoud = f"Geachte {d['voornaam']},\n\nUpdate dossier: {n_status}.\n\n{mail_tekst}"
                    stuur_mail(d['email'], "Update Grondzaken Dossier", mail_inhoud)
                st.success("Dossier succesvol bijgewerkt.")
                st.rerun()
        with btn_c2:
            if st.button(f"🗑️ VERWIJDER DOSSIER #{sel_id}", type="secondary"):
                supabase.table("aanvragen").delete().eq("id", sel_id).execute()
                st.success("Dossier verwijderd.")
                st.rerun()

# --- 8. DASHBOARD & VISUALISATIE ---
elif menu == "📊 Rapportages":
    st.header("📊 Management Dashboard")
    res = supabase.table("aanvragen").select("*").execute()
    if res.data:
        df = pd.DataFrame(res.data)
        c1, c2, c3 = st.columns(3)
        c1.metric("Totaal", len(df))
        c2.metric("Open", len(df[df['status'] == 'In behandeling']))
        c3.metric("Klaar", len(df[df['status'] == 'Afgehandeld']))

        cl, cr = st.columns(2)
        with cl:
            fig_pie = px.pie(df, names='status', title="Status Verdeling", color_discrete_sequence=['#2e7d32', '#81c784', '#d32f2f'])
            st.plotly_chart(fig_pie, use_container_width=True)
        with cr:
            df['datum'] = pd.to_datetime(df['created_at']).dt.date
            trend = df.groupby('datum').size().reset_index(name='aantal')
            fig_bar = px.bar(trend, x='datum', y='aantal', title="Aanvragen per dag", color_discrete_sequence=['#2e7d32'])
            st.plotly_chart(fig_bar, use_container_width=True)
            
        st.dataframe(df[['id_nummer', 'achternaam', 'status', 'afspraak_datum']], use_container_width=True)

# --- 9. OVERIGE SECTIES ---
elif menu == "📅 Agenda":
    st.header("📅 Bezoekagenda")
    res = supabase.table("aanvragen").select("voornaam, achternaam, afspraak_datum, afspraak_tijd, status").execute()
    if res.data:
        st.table(pd.DataFrame(res.data).sort_values('afspraak_datum'))

elif menu == "⚙️ Systeembeheer":
    st.header("⚙️ Systeembeheer")
    if st.session_state.role == 'admin':
        st.subheader("Medewerkersbeheer")
        # Hier kan de admin-code voor het toevoegen van medewerkers blijven staan
    else:
        st.error("U heeft geen admin-rechten om deze pagina te bekijken.")

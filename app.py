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

supabase = create_client(st.secrets["SUPABASE_URL"], st.secrets["SUPABASE_KEY"])

EMAIL_USER = "wanicacentrum.gz@gmail.com"
EMAIL_PASS = "kmebjorjujxwqbvo"

# --- 2. STYLING (ALLEEN KLEUREN AANGEPAST VOOR LEESBAARHEID) ---
st.markdown("""
    <style>
    /* Achtergrond van de hele app */
    .stApp { background-color: white; }
    
    /* Titels */
    h1, h2, h3 { color: #2e7d32 !important; font-weight: bold; }
    
    /* Invoervelden: Witte achtergrond met ZWARTE tekst voor optimale leesbaarheid */
    input, textarea, [data-baseweb="select"] > div {
        background-color: white !important;
        color: black !important;
        border: 1px solid #2e7d32 !important;
    }
    
    /* Labels boven de velden: Donkergroen */
    label p {
        color: #1b5e20 !important;
        font-weight: bold !important;
    }

    /* Knoppen: Groen met witte tekst */
    .stButton>button { 
        background-color: #2e7d32 !important; 
        color: white !important; 
        border-radius: 5px; 
        font-weight: bold;
    }

    /* Sidebar: Lichtgroen */
    [data-testid="stSidebar"] { background-color: #f1f8e9 !important; }
    
    /* Verwijderknop: Rood */
    button[data-testid="stBaseButton-secondary"] {
        background-color: #d32f2f !important;
        color: white !important;
        border: none !important;
    }
    
    /* Tabel tekst kleur */
    .stDataFrame { color: black !important; }
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

# --- 4. STATE ---
if 'logged_in' not in st.session_state:
    st.session_state.update({'logged_in': False, 'role': None, 'user': None})
if 'selected_time' not in st.session_state:
    st.session_state.selected_time = None

# --- 5. MENU & LOGIN ---
menu_options = ["📝 Nieuwe Registratie"]
if st.session_state.logged_in:
    menu_options += ["📋 Dossierbeheer", "📊 Rapportages", "📅 Agenda", "⚙️ Systeembeheer"]

menu = st.sidebar.radio("Hoofdmenu", menu_options)

if not st.session_state.logged_in:
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
    st.sidebar.write(f"Ingelogd: **{st.session_state.user}**")
    if st.sidebar.button("🚪 Afmelden"):
        st.session_state.update({'logged_in': False, 'role': None, 'user': None})
        st.rerun()

# --- 6. PAGINA LOGICA ---
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
    st.subheader("📅 Indien noodzakelijk kan een afspraak worden ingepland. Afspraken zijn uitsluitend mogelijk op maandag en woensdag tussen 08:00 en 12:00 uur.")
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
        else: st.error("Vul alle velden in en kies een tijdstip.")
            # --- CONTACT SECTIE VOOR CLIENTEN ---
    st.write("") # Extra witruimte
    st.divider()
    
    with st.container():
        st.subheader("📞 Direct Contact met een medewerker")
        st.write("Heeft u vragen over uw aanvraag of ondervindt u problemen? Neem contact met ons op:")
        
        icon_col, info_col = st.columns([0.1, 0.9])
        with info_col:
            st.markdown(f"""
                <div style="background-color: #f1f8e9; padding: 15px; border-radius: 10px; border-left: 5px solid #2e7d32;">
                    <p style="margin: 0; color: black;"><b>📧 E-mail:</b> <a href="mailto:wanicacentrum.gz@gmail.com" style="color: #2e7d32;">wanicacentrum.gz@gmail.com</a></p>
                    <p style="margin: 0; color: black;"><b>📞 Telefoon:</b> +597-366660 / +597-366929</p>
                </div>
            """, unsafe_allow_html=True)

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
            n_status = st.selectbox("Status", ["In behandeling", "Wacht op documenten", "Bevestigd", "Afgehandeld"], index=["In behandeling", "Wacht op documenten", "Bevestigd", "Afgehandeld"].index(d['status']) if d['status'] in ["In behandeling", "Wacht op documenten", "Bevestigd", "Afgehandeld"] else 0)
            n_datum = st.date_input("Datum", value=datetime.datetime.strptime(d['afspraak_datum'], '%Y-%m-%d').date())
            n_tijd = st.text_input("Tijd", value=d['afspraak_tijd'])
        with ce2:
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

elif menu == "📊 Rapportages" and st.session_state.logged_in:
    res = supabase.table("aanvragen").select("*").execute()
    if res.data: st.dataframe(pd.DataFrame(res.data), use_container_width=True)

elif menu == "📅 Agenda" and st.session_state.logged_in:
    res = supabase.table("aanvragen").select("voornaam, achternaam, afspraak_datum, afspraak_tijd, status").execute()
    if res.data: st.table(pd.DataFrame(res.data).sort_values('afspraak_datum'))

elif menu == "⚙️ Systeembeheer" and st.session_state.logged_in:
    if st.session_state.role == 'admin':
        st.header("⚙️ Systeembeheer")
        # Medewerkersbeheer...
    else: st.error("Geen admin rechten.")

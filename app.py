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

# Huisstijl Groen/Wit
st.markdown("""
    <style>
    .stApp { background-color: white; }
    h1, h2, h3 { color: #2e7d32; }
    .stButton>button { background-color: #2e7d32; color: white; border-radius: 5px; }
    .stSidebar { background-color: #f1f8e9; }
    div.stButton > button:first-child[data-testid="stBaseButton-secondary"] {
        background-color: #d32f2f;
        border-color: #d32f2f;
    }
    </style>
""", unsafe_allow_html=True)

# --- 2. EMAIL FUNCTIE ---
def stuur_mail(ontvanger, onderwerp, inhoud, bestanden=None):
    msg = MIMEMultipart()
    msg['From'] = EMAIL_USER
    msg['To'] = ontvanger
    msg['Subject'] = onderwerp
    msg.attach(MIMEText(inhoud, 'plain'))
    if bestanden:
        for f in bestanden:
            part = MIMEApplication(f.read(), Name=f.name)
            part['Content-Disposition'] = f'attachment; filename="{f.name}"'
            msg.attach(part)
            f.seek(0)
    try:
        server = smtplib.SMTP('smtp.gmail.com', 587)
        server.starttls()
        server.login(EMAIL_USER, EMAIL_PASS)
        server.send_message(msg)
        server.quit()
        return True
    except Exception as e:
        st.error(f"E-mail niet verzonden: {e}")
        return False

# --- 3. LOGIN & STATE ---
if 'logged_in' not in st.session_state:
    st.session_state.update({'logged_in': False, 'role': None, 'user': None})
if 'selected_time' not in st.session_state:
    st.session_state.selected_time = None

with st.sidebar:
    st.image("https://upload.wikimedia.org/wikipedia/commons/thumb/8/82/Coat_of_arms_of_Suriname.svg/1200px-Coat_of_arms_of_Suriname.svg.png", width=100)
    st.markdown("<h3 style='text-align: center;'>DGW Wanica Centrum</h3>", unsafe_allow_html=True)
    st.divider()

if not st.session_state.logged_in:
    with st.sidebar:
        st.subheader("🔑 Medewerkers Login")
        try:
            res_m = supabase.table("medewerkers").select("*").execute()
            user_list = [u['gebruikersnaam'] for u in res_m.data] if res_m.data else []
            u_sel = st.selectbox("Selecteer Naam", ["---"] + user_list)
            p_inp = st.text_input("Wachtwoord", type="password")
            if st.button("Inloggen"):
                user_data = next((u for u in res_m.data if u['gebruikersnaam'] == u_sel), None)
                if user_data and user_data['wachtwoord'] == p_inp:
                    st.session_state.update({'logged_in': True, 'role': user_data['rol'], 'user': u_sel})
                    st.rerun()
        except: st.error("Database verbinding mislukt")

# --- 4. NAVIGATION ---
menu_options = ["📝 Registratie"]
if st.session_state.logged_in:
    menu_options += ["📋 Dossierbeheer", "📊 Rapportages", "📅 Agenda", "⚙️ Systeembeheer"]
    if st.sidebar.button("Logout"):
        st.session_state.update({'logged_in': False, 'role': None, 'user': None})
        st.rerun()

menu = st.sidebar.radio("Hoofdmenu", menu_options)

# --- 5. REGISTRATIE ---
if menu == "📝 Registratie":
    st.header("Nieuwe Registratie Grondzaken")
    col1, col2 = st.columns(2)
    with col1:
        vnaam = st.text_input("Voornaam *")
        anaam = st.text_input("Achternaam *")
        adres = st.text_input("Woonadres *")
        email = st.text_input("E-mailadres *")
    with col2:
        id_nr = st.text_input("ID-nummer *")
        tel = st.text_input("Telefoonnummer *")
        lad = st.text_input("LAD-nummer")
    
    klacht = st.text_area("Omschrijving van het verzoek *")
    docs = st.file_uploader("Documenten uploaden", accept_multiple_files=True)
    
    st.divider()
    datum = st.date_input("Kies datum", min_value=datetime.date.today())
    if datum.weekday() in [0, 2]: # Ma & Wo
        tijden = [f"{h:02d}:{m:02d}" for h in range(8, 15) for m in (0, 15, 30, 45) if not (h == 14 and m > 30)]
        cols = st.columns(4)
        for idx, t in enumerate(tijden):
            with cols[idx % 4]:
                if st.button(t, key=f"t_{t}", type="primary" if st.session_state.selected_time == t else "secondary"):
                    st.session_state.selected_time = t
                    st.rerun()
    else:
        st.warning("Let op: Bezoekafspraken zijn alleen op Maandag en Woensdag mogelijk.")

    if st.button("Indienen", type="primary", use_container_width=True):
        if all([vnaam, anaam, adres, email, id_nr, klacht]) and st.session_state.selected_time:
            db_data = {"voornaam": vnaam, "achternaam": anaam, "woonadres": adres, "email": email, "id_nummer": id_nr, "telefoon": tel, "lad_nummer": lad, "afspraak_datum": str(datum), "afspraak_tijd": st.session_state.selected_time, "status": "In behandeling", "bericht": klacht}
            supabase.table("aanvragen").insert(db_data).execute()
            stuur_mail(EMAIL_USER, f"Nieuwe Aanvraag: {vnaam}", f"Cliënt: {vnaam} {anaam}\nBericht: {klacht}", docs)
            st.success("Registratie succesvol verzonden.")
            st.session_state.selected_time = None
        else: st.error("Vul alle verplichte velden in.")

# --- 6. DOSSIERBEHEER ---
elif menu == "📋 Dossierbeheer":
    st.header("Dossierbeheer & Wijzigingen")
    res = supabase.table("aanvragen").select("*").order('id', desc=True).execute()
    if res.data:
        df = pd.DataFrame(res.data)
        st.dataframe(df[['id', 'voornaam', 'achternaam', 'status', 'afspraak_datum']], hide_index=True)
        
        sel_id = st.selectbox("Selecteer Dossier ID voor acties", df['id'].tolist())
        d = next(item for item in res.data if item['id'] == sel_id)
        
        col_c1, col_c2 = st.columns(2)
        with col_c1:
            st.info(f"**Cliënt:** {d['voornaam']} {d['achternaam']}\n\n**Adres:** {d.get('woonadres', 'Nvt')}\n\n**LAD:** {d.get('lad_nummer', 'Nvt')}")
        with col_c2:
            st.warning(f"**Status:** {d['status']}\n\n**Huidige Afspraak:** {d['afspraak_datum']} om {d['afspraak_tijd']}")

        st.divider()
        c_edit1, c_edit2 = st.columns(2)
        with c_edit1:
            n_status = st.selectbox("Nieuwe Status", ["In behandeling", "Wacht op documenten", "Bevestigd", "Afgehandeld"])
            n_datum = st.date_input("Afspraak verzetten naar:", value=datetime.datetime.strptime(d['afspraak_datum'], '%Y-%m-%d').date())
            n_tijd = st.text_input("Nieuwe Tijd (HH:MM)", value=d['afspraak_tijd'])
        with c_edit2:
            # Kolommen uit screenshot image_f30225.png
            toelichting_int = st.text_area("Interne Notitie (Medewerker)", value=d.get('medewerker_toelichting', ""))
            mail_tekst = st.text_area("Bericht voor de Cliënt (E-mail)")

        c_btn1, c_btn2 = st.columns(2)
        with c_btn1:
            if st.button("💾 Opslaan & Mailen", use_container_width=True):
                supabase.table("aanvragen").update({
                    "status": n_status, "afspraak_datum": str(n_datum), 
                    "afspraak_tijd": n_tijd, "medewerker_toelichting": toelichting_int,
                    "volgende_stappen": mail_tekst
                }).eq("id", sel_id).execute()
                
                inhoud = f"Geachte {d['voornaam']},\n\nUw status is: {n_status}.\nAfspraak: {n_datum} om {n_tijd}.\n\nToelichting:\n{mail_tekst}"
                stuur_mail(d['email'], "Update Grondzaken Wanica", inhoud)
                st.success("Opgeslagen en cliënt geïnformeerd.")
                st.rerun()
        with c_btn2:
            if st.button(f"🗑️ Verwijder Dossier #{sel_id}", type="secondary", use_container_width=True):
                supabase.table("aanvragen").delete().eq("id", sel_id).execute()
                st.rerun()

# --- 7. RAPPORTAGES ---
elif menu == "📊 Rapportages":
    st.header("Management Rapport")
    res = supabase.table("aanvragen").select("*").execute()
    if res.data:
        df = pd.DataFrame(res.data)
        st.dataframe(df, use_container_width=True)
        st.download_button("📥 Download Rapport (CSV)", df.to_csv(index=False).encode('utf-8'), "DGW_Rapport.csv", "text/csv")

# --- 8. AGENDA ---
elif menu == "📅 Agenda":
    st.header("Bezoekagenda")
    res = supabase.table("aanvragen").select("voornaam, achternaam, afspraak_datum, afspraak_tijd, status").order('afspraak_datum').execute()
    if res.data:
        st.table(pd.DataFrame(res.data))

# --- 9. BEHEER ---
elif menu == "⚙️ Systeembeheer":
    st.header("Medewerkersbeheer")
    with st.expander("Nieuwe Medewerker"):
        u = st.text_input("Gebruikersnaam")
        p = st.text_input("Wachtwoord", type="password")
        r = st.selectbox("Rol", ["user", "admin"])
        if st.button("Voeg toe"):
            supabase.table("medewerkers").insert({"gebruikersnaam": u, "wachtwoord": p, "rol": r}).execute()
            st.rerun()
    
    res_m = supabase.table("medewerkers").select("*").execute()
    if res_m.data:
        for m in res_m.data:
            col_m1, col_m2 = st.columns([3, 1])
            col_m1.write(f"👤 {m['gebruikersnaam']} ({m['rol']})")
            if col_m2.button("Verwijder", key=f"del_{m['id']}"):
                supabase.table("medewerkers").delete().eq("id", m['id']).execute()
                st.rerun()

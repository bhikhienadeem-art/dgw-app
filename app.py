import streamlit as st
from supabase import create_client, Client
import datetime
import pandas as pd
import smtplib
from email.mime.text import MIMEText
from email.mime.multipart import MIMEMultipart
from email.mime.application import MIMEApplication
from io import BytesIO

# --- 1. CONFIGURATIE & VERBINDING ---
st.set_page_config(page_title="Registratie Dienst Grondzaken Wanica Centrum", layout="wide")

# Supabase Verbinding
supabase = create_client(st.secrets["SUPABASE_URL"], st.secrets["SUPABASE_KEY"])

# E-mail Instellingen
EMAIL_USER = "wanicacentrum.gz@gmail.com"
EMAIL_PASS = "kmebjorjujxwqbvo"

# Kleuren Groen/Wit (Huisstijl)
st.markdown("""
    <style>
    .stApp { background-color: white; }
    h1, h2, h3 { color: #2e7d32; }
    .stButton>button { background-color: #2e7d32; color: white; border-radius: 5px; }
    .stSidebar { background-color: #f1f8e9; }
    </style>
""", unsafe_allow_html=True)

# --- 2. EMAIL FUNCTIES ---
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
            f.seek(0) # Reset voor hergebruik

    try:
        server = smtplib.SMTP('smtp.gmail.com', 587)
        server.starttls()
        server.login(EMAIL_USER, EMAIL_PASS)
        server.send_message(msg)
        server.quit()
        return True
    except Exception as e:
        st.error(f"E-mail naar {ontvanger} mislukt: {e}")
        return False

# --- 3. AUTHENTICATIE & MENU ---
if 'logged_in' not in st.session_state:
    st.session_state.update({'logged_in': False, 'role': None, 'user': None})
if 'selected_time' not in st.session_state:
    st.session_state.selected_time = None

# Sidebar Logo & Titel
with st.sidebar:
    st.markdown("<h2 style='text-align: center;'>DGW Wanica Centrum</h2>", unsafe_allow_html=True)
    st.divider()

if not st.session_state.logged_in:
    with st.sidebar:
        st.subheader("🔐 Medewerkers Portaal")
        try:
            res_m = supabase.table("medewerkers").select("*").execute()
            user_list = [u['gebruikersnaam'] for u in res_m.data] if res_m.data else []
            u_sel = st.selectbox("Gebruiker", ["---"] + user_list)
            p_inp = st.text_input("Wachtwoord", type="password")
            if st.button("Inloggen"):
                user_data = next((u for u in res_m.data if u['gebruikersnaam'] == u_sel), None)
                if user_data and user_data['wachtwoord'] == p_inp:
                    st.session_state.update({'logged_in': True, 'role': user_data['rol'], 'user': u_sel})
                    st.rerun()
        except: pass

menu_options = ["📝 Nieuwe Registratie"]
if st.session_state.logged_in:
    menu_options += ["📋 Dossierbeheer", "📊 Rapportages", "📅 Agenda & Kalender"]
    if st.sidebar.button("Afmelden"):
        st.session_state.update({'logged_in': False, 'role': None, 'user': None})
        st.rerun()

menu = st.sidebar.radio("Menu", menu_options)

# --- 4. NIEUWE REGISTRATIE ---
if menu == "📝 Nieuwe Registratie":
    st.header("Officiële Registratie Dienst Grondzaken Wanica Centrum")
    
    col1, col2 = st.columns(2)
    with col1:
        vnaam = st.text_input("Voornaam *")
        anaam = st.text_input("Achternaam *")
        woonadres = st.text_input("Woonadres *")
        email = st.text_input("E-mailadres *")
    with col2:
        id_nr = st.text_input("ID-nummer *")
        tel = st.text_input("Telefoonnummer *")
        lad_nr = st.text_input("LAD-nummer")
    
    bericht = st.text_area("Omschrijving klacht/verzoek *")
    
    st.markdown("### Documenten Bijvoegen")
    bestanden = st.file_uploader("Upload relevante documenten (ID, perceelkaart, etc.)", accept_multiple_files=True)
    
    st.divider()
    st.markdown("### Planning Bezoekafspraak")
    datum = st.date_input("Kies een datum", min_value=datetime.date.today())
    
    # Afspraken alleen op maandag en woensdag
    if datum.weekday() in [0, 2]:
        tijdsblokken = [f"{h:02d}:{m:02d}" for h in range(8, 15) for m in (0, 15, 30, 45) if not (h == 14 and m > 30)]
        cols = st.columns(4)
        for idx, tijd in enumerate(tijdsblokken):
            with cols[idx % 4]:
                style = "primary" if st.session_state.selected_time == tijd else "secondary"
                if st.button(f"🕒 {tijd}", key=f"reg_{tijd}", type=style, use_container_width=True):
                    st.session_state.selected_time = tijd
                    st.rerun()
    else:
        st.warning("Bezoekafspraken zijn enkel mogelijk op maandag en woensdag.")

    if st.button("Registratie Definitief Indienen", type="primary", use_container_width=True):
        if all([vnaam, anaam, woonadres, email, id_nr, bericht]) and st.session_state.selected_time:
            try:
                data = {
                    "voornaam": vnaam, "achternaam": anaam, "woonadres": woonadres,
                    "email": email, "id_nummer": id_nr, "telefoon": tel, 
                    "lad_nummer": lad_nr, "afspraak_datum": str(datum),
                    "afspraak_tijd": st.session_state.selected_time, "status": "In behandeling", "bericht": bericht
                }
                supabase.table("aanvragen").insert(data).execute()
                
                # Mail naar medewerker met alle info en bijlagen
                mail_body = f"Nieuwe registratie ontvangen:\n\nNaam: {vnaam} {anaam}\nAdres: {woonadres}\nID: {id_nr}\nBericht: {bericht}\n\nAfspraak: {datum} om {st.session_state.selected_time}"
                stuur_mail(EMAIL_USER, f"Nieuwe Registratie: {vnaam} {anaam}", mail_body, bestanden)
                
                st.success("Registratie succesvol ingediend. De medewerkers zijn per mail geïnformeerd.")
                st.session_state.selected_time = None
            except Exception as e: st.error(f"Fout: {e}")
        else:
            st.error("Vul alle verplichte velden in en selecteer een tijdstip.")

# --- 5. DOSSIERBEHEER ---
elif menu == "📋 Dossierbeheer":
    st.header("📋 Dossierbeheer & Communicatie")
    res = supabase.table("aanvragen").select("*").order('id', desc=True).execute()
    if res.data:
        df = pd.DataFrame(res.data)
        st.dataframe(df[['id', 'voornaam', 'achternaam', 'status', 'afspraak_datum', 'woonadres']], hide_index=True)
        
        st.divider()
        sel_id = st.selectbox("Selecteer dossier ID", df['id'].tolist())
        d = next(item for item in res.data if item['id'] == sel_id)
        
        col_a, col_b = st.columns(2)
        with col_a:
            st.markdown(f"**Cliënt:** {d['voornaam']} {d['achternaam']}")
            n_status = st.selectbox("Nieuwe Status", ["In behandeling", "Wacht op documenten", "Bevestigd", "Afgehandeld"], index=0)
            i_notitie = st.text_area("Interne Notitie", value=d.get('interne_notitie', ""))
        with col_b:
            volgende_stappen = st.text_area("Instructies voor Cliënt")
            n_datum = st.date_input("Verzetten naar:", value=datetime.datetime.strptime(d['afspraak_datum'], '%Y-%m-%d').date())
            n_tijd = st.text_input("Nieuwe Tijd", value=d['afspraak_tijd'])

        if st.button("💾 Opslaan & Mailen", type="primary", use_container_width=True):
            try:
                supabase.table("aanvragen").update({
                    "status": n_status, "interne_notitie": i_notitie, 
                    "instructies_client": volgende_stappen, "afspraak_datum": str(n_datum), "afspraak_tijd": n_tijd
                }).eq("id", sel_id).execute()

                mail_inhoud = f"Beste {d['voornaam']},\n\nUw dossier is bijgewerkt.\nStatus: {n_status}\nInstructies: {volgende_stappen}\nNieuwe afspraak: {n_datum} om {n_tijd}"
                stuur_mail(d['email'], "Update Dossier DGW", mail_inhoud)
                stuur_mail(EMAIL_USER, f"Kopie Update: {d['voornaam']}", mail_inhoud)
                
                st.success("Dossier bijgewerkt en mails verzonden.")
                st.rerun()
            except Exception as e: st.error(f"Fout: {e}")

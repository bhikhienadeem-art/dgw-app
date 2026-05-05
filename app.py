import streamlit as st
from supabase import create_client, Client
import datetime
import pandas as pd
import smtplib
import os
from email.mime.text import MIMEText
from email.mime.multipart import MIMEMultipart
from io import BytesIO

# --- 1. CONFIGURATIE & VERBINDING ---
st.set_page_config(page_title="Registratie Dienst Grondzaken Wanica Centrum", layout="wide")

# Supabase Verbinding
supabase = create_client(st.secrets["SUPABASE_URL"], st.secrets["SUPABASE_KEY"])

# E-mail Instellingen
EMAIL_USER = "wanicacentrum.gz@gmail.com"
EMAIL_PASS = "kmebjorjujxwqbvo" # Je verstrekte App Password

# Kleuren Groen/Wit (Huisstijl)
st.markdown("""
    <style>
    .stApp { background-color: white; }
    h1, h2, h3 { color: #2e7d32; }
    .stButton>button { background-color: #2e7d32; color: white; border-radius: 5px; }
    .stSidebar { background-color: #f1f8e9; }
    </style>
""", unsafe_allow_html=True)

# --- 2. HULPFUNCTIES ---
def stuur_mail(ontvanger, onderwerp, inhoud):
    msg = MIMEMultipart()
    msg['From'] = EMAIL_USER
    msg['To'] = ontvanger
    msg['Subject'] = onderwerp
    msg.attach(MIMEText(inhoud, 'plain'))
    
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
    if st.sidebar.button("🚪 Afmelden"):
        st.session_state.update({'logged_in': False, 'role': None, 'user': None})
        st.rerun()

menu = st.sidebar.radio("Menu", menu_options)

# --- 4. NIEUWE REGISTRATIE (ONGEWIJZIGD) ---
if menu == "📝 Nieuwe Registratie":
    st.header("Officiële Registratie Dienst Grondzaken Wanica Centrum")
    col1, col2 = st.columns(2)
    with col1:
        vnaam = st.text_input("Voornaam *")
        anaam = st.text_input("Achternaam *")
        email = st.text_input("E-mailadres *")
    with col2:
        id_nr = st.text_input("ID-nummer *")
        tel = st.text_input("Telefoonnummer *")
        lad_nr = st.text_input("LAD-nummer")
    
    bericht = st.text_area("Omschrijving klacht/verzoek *")
    st.divider()
    datum = st.date_input("Kies een datum", min_value=datetime.date.today())
    
    if datum.weekday() in [0, 2]:
        tijdsblokken = [f"{h:02d}:{m:02d}" for h in range(8, 15) for m in (0, 15, 30, 45) if not (h == 14 and m > 30)]
        cols = st.columns(4)
        for idx, tijd in enumerate(tijdsblokken):
            with cols[idx % 4]:
                style = "primary" if st.session_state.selected_time == tijd else "secondary"
                if st.button(f"🕒 {tijd}", key=f"reg_{tijd}", type=style, use_container_width=True):
                    st.session_state.selected_time = tijd
                    st.rerun()
    
    if st.button("Registratie Indienen", type="primary", use_container_width=True):
        if all([vnaam, anaam, email, id_nr, bericht]) and st.session_state.selected_time:
            supabase.table("aanvragen").insert({
                "voornaam": vnaam, "achternaam": anaam, "email": email, "id_nummer": id_nr,
                "telefoon": tel, "lad_nummer": lad_nr, "afspraak_datum": str(datum),
                "afspraak_tijd": st.session_state.selected_time, "status": "In behandeling", "bericht": bericht
            }).execute()
            st.success("Uw aanvraag is succesvol geregistreerd.")
            st.session_state.selected_time = None
        else:
            st.error("Vul alle verplichte velden in.")

# --- 5. DOSSIERBEHEER (MET EMAIL UPDATES) ---
elif menu == "📋 Dossierbeheer":
    st.header("📋 Dossierbeheer & Communicatie")
    res = supabase.table("aanvragen").select("*").order('id', desc=True).execute()
    if res.data:
        df = pd.DataFrame(res.data)
        st.dataframe(df[['id', 'voornaam', 'achternaam', 'status', 'afspraak_datum']], hide_index=True)
        
        st.divider()
        sel_id = st.selectbox("Selecteer dossier ID", df['id'].tolist())
        d = next(item for item in res.data if item['id'] == sel_id)
        
        col_a, col_b = st.columns(2)
        with col_a:
            st.markdown(f"**Cliënt:** {d['voornaam']} {d['achternaam']}")
            n_status = st.selectbox("Nieuwe Status", ["In behandeling", "Wacht op documenten", "Bevestigd", "Afgehandeld"], index=0)
            i_notitie = st.text_area("Interne Notitie (Systeem)", value=d.get('interne_notitie', ""))
        with col_b:
            volgende_stappen = st.text_area("Instructies voor Cliënt (gaat in de mail)", placeholder="Bijv: Neem uw originele ID-kaart mee.")
            n_datum = st.date_input("Afspraak verzetten naar:", value=datetime.datetime.strptime(d['afspraak_datum'], '%Y-%m-%d').date())
            n_tijd = st.text_input("Tijd", value=d['afspraak_tijd'])

        if st.button("💾 Opslaan & E-mails Verzenden", type="primary", use_container_width=True):
            try:
                # Update Database
                supabase.table("aanvragen").update({
                    "status": n_status, "interne_notitie": i_notitie, 
                    "instructies_client": volgende_stappen, "afspraak_datum": str(n_datum), "afspraak_tijd": n_tijd
                }).eq("id", sel_id).execute()

                # Mail opstellen
                mail_body = f"""
Beste {d['voornaam']} {d['achternaam']},

Uw dossier bij Dienst Grondzaken Wanica Centrum is bijgewerkt.

Status: {n_status}
Afspraak: {n_datum} om {n_tijd} uur

Instructies medewerker:
{volgende_stappen}

Met vriendelijke groet,
Dienst Grondzaken Wanica Centrum
                """
                # Verzenden naar cliënt en kopie naar medewerker
                stuur_mail(d['email'], f"Update Dossier #{sel_id}", mail_body)
                stuur_mail(EMAIL_USER, f"KOPIE Update Dossier #{sel_id} ({d['voornaam']})", mail_body)
                
                st.success("Dossier bijgewerkt en e-mails verzonden.")
                st.rerun()
            except Exception as e: st.error(f"Fout: {e}")

# --- 6. RAPPORTAGES ---
elif menu == "📊 Rapportages":
    st.header("📊 Management Rapportages")
    res = supabase.table("aanvragen").select("*").execute()
    if res.data:
        df = pd.DataFrame(res.data)
        st.dataframe(df, use_container_width=True)
        csv = df.to_csv(index=False).encode('utf-8')
        st.download_button("📥 Download CSV Rapport", data=csv, file_name="DGW_Rapport.csv", mime="text/csv")

# --- 7. AGENDA ---
elif menu == "📅 Agenda & Kalender":
    st.header("📅 Agenda Overzicht")
    res = supabase.table("aanvragen").select("voornaam, achternaam, afspraak_datum, afspraak_tijd, status").execute()
    if res.data:
        df_cal = pd.DataFrame(res.data)
        st.dataframe(df_cal.sort_values(['afspraak_datum', 'afspraak_tijd']), use_container_width=True)

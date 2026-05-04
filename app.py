import streamlit as st
from supabase import create_client, Client
import datetime
import pandas as pd
import smtplib
from email.mime.text import MIMEText
from email.mime.multipart import MIMEMultipart
from email.mime.application import MIMEApplication
import os

# --- 1. CONFIGURATIE & VISUELE IDENTITEIT ---
st.set_page_config(page_title="Dienst Grondzaken Wanica Centrum", layout="wide")

# Verbinding met Supabase
supabase = create_client(st.secrets["SUPABASE_URL"], st.secrets["SUPABASE_KEY"])

# Sidebar met Logo en Benaming
with st.sidebar:
    logo_path = "orgineel logo Centrum.png"
    if os.path.exists(logo_path):
        st.image(logo_path, use_container_width=True) # cite: image_650ce2.png
    
    # Benaming aangepast naar Dienst Grondzaken Wanica Centrum
    st.markdown("<h2 style='text-align: center;'>Dienst Grondzaken Wanica Centrum</h2>", unsafe_allow_html=True) 
    st.divider()

# --- COMMUNICATIE SERVICE (E-MAIL) ---
def stuur_notificatie(ontvanger, onderwerp, html_inhoud, bijlagen=None):
    try:
        msg = MIMEMultipart()
        msg['Subject'] = onderwerp
        msg['From'] = f"Dienst Grondzaken Wanica Centrum <{st.secrets['EMAIL_USER']}>"
        msg['To'] = ontvanger
        msg.attach(MIMEText(html_inhoud, 'html'))
        
        if bijlagen:
            for f in bijlagen:
                part = MIMEApplication(f.read(), Name=f.name)
                part['Content-Disposition'] = f'attachment; filename="{f.name}"'
                msg.attach(part)
                f.seek(0)
        
        with smtplib.SMTP_SSL('smtp.gmail.com', 465) as server:
            server.login(st.secrets["EMAIL_USER"], st.secrets["EMAIL_PASS"])
            server.send_message(msg)
    except Exception as e:
        st.error(f"Communicatiefout: {e}")

# --- 2. TOEGANGSBEHEER ---
if 'logged_in' not in st.session_state:
    st.session_state.update({'logged_in': False, 'role': None, 'user': None})

if not st.session_state.logged_in:
    st.sidebar.subheader("🔐 Medewerker Portaal") # cite: image_6513c4.png
    res_m = supabase.table("medewerkers").select("*").execute()
    user_list = [u['gebruikersnaam'] for u in res_m.data] if res_m.data else []
    u_sel = st.sidebar.selectbox("Gebruikersnaam", ["---"] + user_list)
    p_inp = st.sidebar.text_input("Wachtwoord", type="password")
    if st.sidebar.button("Aanmelden"):
        user_data = next((u for u in res_m.data if u['gebruikersnaam'] == u_sel), None)
        if user_data and user_data['wachtwoord'] == p_inp:
            st.session_state.update({'logged_in': True, 'role': user_data['rol'], 'user': u_sel})
            st.rerun()

# --- 3. NAVIGATIE ---
menu_options = ["📝 Nieuwe Registratie"]
if st.session_state.logged_in:
    menu_options += ["📋 Dossierbeheer", "📅 Agenda", "📊 Rapportages", "⚙️ Systeeminstellingen"]
    if st.sidebar.button("Logout"):
        st.session_state.logged_in = False
        st.rerun()

menu = st.sidebar.radio("Hoofdmenu", menu_options)

# --- 4. FUNCTIONALITEITEN ---

if menu == "📝 Nieuwe Registratie":
    # Titel aangepast naar Registratie Dienst Grondzaken Wanica Centrum
    st.header("📝 Registratie Dienst Grondzaken Wanica Centrum") # cite: image_6436c4.png
    
    with st.container():
        col1, col2 = st.columns(2)
        with col1:
            vnaam = st.text_input("Voornaam *") # cite: image_651b69.png
            anaam = st.text_input("Achternaam *")
            email = st.text_input("E-mailadres *")
        with col2:
            id_nr = st.text_input("ID-Nummer *")
            tel = st.text_input("Telefoonnummer *")
            lad_nr = st.text_input("LAD Nummer (indien van toepassing)")
    
    bericht = st.text_area("Omschrijving van het verzoek *")
    geuploade_bestanden = st.file_uploader("Relevante documentatie uploaden", accept_multiple_files=True)
    
    st.divider()
    # Professionele formulering voor de afspraken
    st.markdown("### Afspraak inplannen")
    st.info("Indien u een afspraak wenst, gelieve een datum en tijdstip te selecteren (beschikbaar op maandag en woensdag).") # cite: image_642ae8.png
    
    datum = st.date_input("Voorkeursdatum", min_value=datetime.date.today())
    
    if datum.weekday() not in [0, 2]: # Alleen Maandag (0) en Woensdag (2)
        st.warning("Let op: Afspraken op locatie zijn uitsluitend mogelijk op maandag en woensdag.")
    else:
        st.subheader("Beschikbare tijdstippen")
        tijdsblokken = [f"{h:02d}:{m:02d}" for h in range(8, 15) for m in (0, 15, 30, 45) if not (h == 14 and m > 30)]
        
        res_t = supabase.table("aanvragen").select("afspraak_tijd").eq("afspraak_datum", str(datum)).execute()
        bezet = [r['afspraak_tijd'] for r in res_t.data] if res_t.data else []
        
        # Gekleurde tijdslots als knoppen (image_651b69.png stijl)
        cols = st.columns(6)
        for i, slot in enumerate(tijdsblokken):
            is_bezet = slot in bezet
            if cols[i % 6].button(
                f"🚫 {slot}" if is_bezet else slot, 
                key=f"btn_{slot}", 
                disabled=is_bezet,
                use_container_width=True
            ):
                st.session_state.geselecteerde_tijd = slot
        
        if 'geselecteerde_tijd' in st.session_state:
            st.success(f"Geselecteerd tijdstip: **{st.session_state.geselecteerde_tijd}**")

    if st.button("Registratie Definitief Indienen"): # cite: image_642724.png
        if all([vnaam, anaam, email, id_nr, bericht]) and ('geselecteerde_tijd' in st.session_state):
            try:
                supabase.table("aanvragen").insert({
                    "voornaam": vnaam, "achternaam": anaam, "email": email, "id_nummer": id_nr,
                    "telefoon": tel, "lad_nummer": lad_nr, "afspraak_datum": str(datum),
                    "afspraak_tijd": st.session_state.geselecteerde_tijd, "status": "In behandeling", "bericht": bericht
                }).execute()
                
                # E-mail notificatie (image_65757b.png stijl)
                html_msg = f"""
                <div style='font-family: Arial, sans-serif; border: 1px solid #ddd; padding: 20px;'>
                    <h2 style='color: #2c3e50;'>Nieuwe Registratie Ontvangen</h2>
                    <p>Cliënt: <b>{vnaam} {anaam}</b></p>
                    <p><b>ID-Nummer:</b> {id_nr}</p>
                    <p><b>Afspraak:</b> {datum} om {st.session_state.geselecteerde_tijd}</p>
                    <p><b>Omschrijving:</b><br>{bericht}</p>
                </div>
                """
                stuur_notificatie(st.secrets['EMAIL_USER'], f"Nieuwe Registratie: {anaam}", html_msg, geuploade_bestanden)
                
                st.success("Uw registratie is succesvol verwerkt.")
                del st.session_state.geselecteerde_tijd
            except Exception as e:
                st.error(f"Fout bij opslaan: {e}")
        else:
            st.error("Gelieve alle verplichte velden in te vullen en een tijdstip te selecteren.")

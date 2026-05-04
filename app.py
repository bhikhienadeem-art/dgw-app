import streamlit as st
from supabase import create_client, Client
import datetime
import pandas as pd
import smtplib
from email.mime.text import MIMEText
from email.mime.multipart import MIMEMultipart
from email.mime.application import MIMEApplication
from streamlit_calendar import calendar

# --- 1. CONFIGURATIE & TITEL ---
st.set_page_config(page_title="Registratie Dienst Grondzaken Wanica Centrum", layout="wide")

# Verbinding met Supabase
supabase = create_client(st.secrets["SUPABASE_URL"], st.secrets["SUPABASE_KEY"])

# --- VERBETERDE PROFESSIONELE MAIL FUNCTIE MET BIJLAGEN ---
def stuur_mail_met_bijlagen(ontvanger, onderwerp, html_inhoud, bestanden=None):
    try:
        msg = MIMEMultipart()
        msg['Subject'] = onderwerp
        msg['From'] = f"DGW Wanica Centrum <{st.secrets['EMAIL_USER']}>"
        msg['To'] = ontvanger
        
        msg.attach(MIMEText(html_inhoud, 'html'))
        
        # Voeg documenten toe als bijlagen
        if bestanden:
            for f in bestanden:
                part = MIMEApplication(f.read(), Name=f.name)
                part['Content-Disposition'] = f'attachment; filename="{f.name}"'
                msg.attach(part)
                f.seek(0) # Reset file pointer voor later gebruik
        
        with smtplib.SMTP_SSL('smtp.gmail.com', 465) as server:
            server.login(st.secrets["EMAIL_USER"], st.secrets["EMAIL_PASS"])
            server.send_message(msg)
    except Exception as e:
        st.error(f"E-mail fout: {e}")

# --- MAIL TEMPLATES ---
def template_bevestiging_aanvraag(naam, datum, tijd):
    return f"""
    <html>
        <body style="font-family: Arial, sans-serif; color: #333;">
            <div style="background-color: #2e7d32; padding: 20px; color: white; text-align: center;">
                <h2>Ontvangstbevestiging Registratie</h2>
            </div>
            <div style="padding: 20px; border: 1px solid #ddd;">
                <p>Beste <b>{naam}</b>,</p>
                <p>Uw aanvraag bij de Dienst Grondzaken Wanica Centrum is succesvol ontvangen.</p>
                <p><b>Afspraakgegevens:</b><br>Datum: {datum}<br>Tijdstip: {tijd}</p>
                <p>Onze medewerkers zullen uw verzoek in behandeling nemen.</p>
                <hr>
                <p style="font-size: 12px; color: #777;">Districtscommissariaat Wanica-Centrum</p>
            </div>
        </body>
    </html>
    """

def template_nieuwe_aanvraag_intern_volledig(data):
    return f"""
    <html>
        <body style="font-family: Arial, sans-serif; color: #333;">
            <div style="background-color: #444; padding: 15px; color: white;">
                <h3>Nieuwe Aanvraag Binnengekomen (Volledige Details)</h3>
            </div>
            <div style="padding: 20px; border: 1px solid #ddd; background-color: #f9f9f9;">
                <p><b>Cliëntgegevens:</b></p>
                <ul>
                    <li><b>Naam:</b> {data['vnaam']} {data['anaam']}</li>
                    <li><b>E-mail:</b> {data['email']}</li>
                    <li><b>Telefoon:</b> {data['tel']}</li>
                    <li><b>ID-Nummer:</b> {data['id_nr']}</li>
                    <li><b>LAD-Nummer:</b> {data['lad_nr']}</li>
                </ul>
                <p><b>Afspraak:</b> {data['datum']} om {data['tijd']}</p>
                <hr>
                <p><b>Bericht/Omschrijving:</b><br>{data['bericht']}</p>
                <hr>
                <p style="color: #d32f2f;"><i>De upgeloade documenten zijn als bijlage bij deze mail gevoegd.</i></p>
            </div>
        </body>
    </html>
    """

# --- 2. AUTHENTICATIE ---
if 'logged_in' not in st.session_state:
    st.session_state.update({'logged_in': False, 'role': None, 'user': None})

if not st.session_state.logged_in:
    st.sidebar.subheader("🔐 Medewerker Login")
    res_m = supabase.table("medewerkers").select("*").execute()
    user_list = [u['gebruikersnaam'] for u in res_m.data] if res_m.data else []
    u_sel = st.sidebar.selectbox("Gebruiker", ["---"] + user_list)
    p_inp = st.sidebar.text_input("Wachtwoord", type="password")
    if st.sidebar.button("Inloggen"):
        user_data = next((u for u in res_m.data if u['gebruikersnaam'] == u_sel), None)
        if user_data and user_data['wachtwoord'] == p_inp:
            st.session_state.update({'logged_in': True, 'role': user_data['rol'], 'user': u_sel})
            st.rerun()

# --- 3. MENU ---
menu_options = ["Nieuwe Aanvraag DGW"]
if st.session_state.logged_in:
    menu_options += ["Beheer Registraties", "Agenda", "Rapportages", "Systeembeheer"]
    if st.sidebar.button("🚪 Uitloggen"):
        st.session_state.logged_in = False
        st.rerun()

menu = st.sidebar.radio("Hoofdmenu", menu_options)

# --- 4. PAGINA'S ---

if menu == "Nieuwe Aanvraag DGW":
    st.header("📝 Registratie Dienst Grondzaken Wanica Centrum")
    col1, col2 = st.columns(2)
    with col1:
        vnaam = st.text_input("Voornaam *")
        anaam = st.text_input("Achternaam *")
        email = st.text_input("E-mailadres *")
    with col2:
        id_nr = st.text_input("ID-Nummer *")
        tel = st.text_input("Telefoonnummer *")
        lad_nr = st.text_input("LAD Nummer")
    
    bericht = st.text_area("Omschrijving van uw verzoek *")
    geuploade_bestanden = st.file_uploader("Documenten uploaden", accept_multiple_files=True)
    
    datum = st.date_input("Kies een datum", min_value=datetime.date.today())
    
    if datum.weekday() not in [0, 2]:
        st.warning("⚠️ Afspraken zijn enkel mogelijk op maandag en woensdag.")
    else:
        st.subheader("⏰ Beschikbare Tijden")
        tijdsblokken = [f"{h:02d}:{m:02d}" for h in range(8, 15) for m in (0, 15, 30, 45) if not (h == 14 and m > 30)]
        res_t = supabase.table("aanvragen").select("afspraak_tijd").eq("afspraak_datum", str(datum)).execute()
        bezet = [r['afspraak_tijd'] for r in res_t.data] if res_t.data else []
        
        cols = st.columns(6)
        for i, tijd in enumerate(tijdsblokken):
            is_bezet = tijd in bezet
            if cols[i % 6].button(f"🚫 {tijd}" if is_bezet else tijd, key=f"t_{tijd}", disabled=is_bezet):
                st.session_state.sel_tijd = tijd
        
        if 'sel_tijd' in st.session_state:
            st.info(f"Geselecteerd: **{st.session_state.sel_tijd}**")

    if st.button("Registratie Verzenden"):
        if all([vnaam, anaam, email, id_nr, bericht]) and 'sel_tijd' in st.session_state:
            # Opslaan in database
            supabase.table("aanvragen").insert({
                "voornaam": vnaam, "achternaam": anaam, "email": email, "id_nummer": id_nr,
                "telefoon": tel, "lad_nummer": lad_nr, "afspraak_datum": str(datum),
                "afspraak_tijd": st.session_state.sel_tijd, "status": "In behandeling", "bericht": bericht
            }).execute()
            
            # --- VERZEND MAILS BIJ REGISTRATIE ---
            # 1. Bevestiging naar Cliënt
            html_cli = template_bevestiging_aanvraag(f"{vnaam} {anaam}", str(datum), st.session_state.sel_tijd)
            stuur_mail_met_bijlagen(email, "Bevestiging Registratie DGW", html_cli)
            
            # 2. Volledige details naar Medewerker inclusief bestanden
            data_intern = {
                "vnaam": vnaam, "anaam": anaam, "email": email, "tel": tel, 
                "id_nr": id_nr, "lad_nr": lad_nr, "datum": str(datum), 
                "tijd": st.session_state.sel_tijd, "bericht": bericht
            }
            html_med = template_nieuwe_aanvraag_intern_volledig(data_intern)
            stuur_mail_met_bijlagen(st.secrets['EMAIL_USER'], f"NIEUWE AANVRAAG: {vnaam} {anaam}", html_med, geuploade_bestanden)
            
            st.success("✅ Aanvraag succesvol verzonden. Bevestigingen zijn verstuurd.")
            del st.session_state.sel_tijd
        else:
            st.error("Vul alle verplichte velden in.")

# (Rest van de pagina's: Beheer, Rapportages, Agenda, Systeembeheer blijven gelijk)

import streamlit as st
from supabase import create_client, Client
import datetime
import pandas as pd
import smtplib
from email.mime.text import MIMEText
from email.mime.multipart import MIMEMultipart
from streamlit_calendar import calendar

# --- 1. CONFIGURATIE & TITEL ---
st.set_page_config(page_title="Registratie Dienst Grondzaken Wanica Centrum", layout="wide")

# Verbinding met Supabase
supabase = create_client(st.secrets["SUPABASE_URL"], st.secrets["SUPABASE_KEY"])

# --- PROFESSIONELE MAIL FUNCTIES ---
def stuur_mail(ontvanger, onderwerp, html_inhoud):
    try:
        msg = MIMEMultipart()
        msg['Subject'] = onderwerp
        msg['From'] = f"DGW Wanica Centrum <{st.secrets['EMAIL_USER']}>"
        msg['To'] = ontvanger
        msg.attach(MIMEText(html_inhoud, 'html'))
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
                <p><b>Afspraakgegevens:</b><br>
                Datum: {datum}<br>
                Tijdstip: {tijd}</p>
                <p>Onze medewerkers zullen uw verzoek in behandeling nemen. U ontvangt nader bericht over de voortgang.</p>
                <hr>
                <p style="font-size: 12px; color: #777;">Districtscommissariaat Wanica-Centrum</p>
            </div>
        </body>
    </html>
    """

def template_nieuwe_aanvraag_intern(vnaam, anaam, id_nr, bericht):
    return f"""
    <html>
        <body style="font-family: Arial, sans-serif; color: #333;">
            <div style="background-color: #444; padding: 15px; color: white;">
                <h3>Nieuwe Aanvraag Binnengekomen</h3>
            </div>
            <div style="padding: 20px; border: 1px solid #ddd; background-color: #f9f9f9;">
                <p>Er is een nieuwe registratie gedaan door:</p>
                <p><b>Naam:</b> {vnaam} {anaam}</p>
                <p><b>ID-Nummer:</b> {id_nr}</p>
                <p><b>Bericht:</b><br>{bericht}</p>
                <hr>
                <p>Log in op het systeem om de volledige details te bekijken en de afspraak te bevestigen.</p>
            </div>
        </body>
    </html>
    """

def template_client_update(naam, status, toelichting, stappen):
    return f"""
    <html>
        <body style="font-family: Arial, sans-serif; color: #333;">
            <div style="background-color: #2e7d32; padding: 20px; color: white; text-align: center;">
                <h2>Dienst Grondzaken Wanica Centrum</h2>
            </div>
            <div style="padding: 20px; border: 1px solid #ddd;">
                <p>Geachte heer/mevrouw <b>{naam}</b>,</p>
                <p>Hierbij ontvangt u een update betreffende uw dossier.</p>
                <p><b>Status:</b> <span style="color: #2e7d32; font-weight: bold;">{status}</span></p>
                <hr>
                <p><b>Toelichting:</b><br>{toelichting if toelichting else 'In behandeling.'}</p>
                <p><b>Volgende stappen:</b><br>{stappen if stappen else 'Geen actie vereist.'}</p>
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
    st.file_uploader("Documenten uploaden", accept_multiple_files=True)
    
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
            # 1. Opslaan in Database
            supabase.table("aanvragen").insert({
                "voornaam": vnaam, "achternaam": anaam, "email": email, "id_nummer": id_nr,
                "telefoon": tel, "lad_nummer": lad_nr, "afspraak_datum": str(datum),
                "afspraak_tijd": st.session_state.sel_tijd, "status": "In behandeling", "bericht": bericht
            }).execute()
            
            # 2. VERZEND MAILS BIJ REGISTRATIE
            # Mail naar de Cliënt
            html_bevestiging = template_bevestiging_aanvraag(f"{vnaam} {anaam}", str(datum), st.session_state.sel_tijd)
            stuur_mail(email, "Bevestiging Registratie Dienst Grondzaken", html_bevestiging)
            
            # Mail naar de Medewerker (Notificatie)
            html_intern = template_nieuwe_aanvraag_intern(vnaam, anaam, id_nr, bericht)
            stuur_mail(st.secrets['EMAIL_USER'], "NIEUWE REGISTRATIE: " + anaam, html_intern)
            
            st.success("✅ Uw aanvraag is verzonden. Zowel u als onze medewerkers hebben een bevestiging per mail ontvangen.")
            del st.session_state.sel_tijd
        else:
            st.error("Vul alle verplichte velden in.")

elif menu == "Beheer Registraties":
    st.header("📋 Cliëntendossiers Beheren")
    res = supabase.table("aanvragen").select("*").order('created_at', desc=True).execute()
    if res.data:
        df = pd.DataFrame(res.data)
        st.dataframe(df[['id', 'voornaam', 'achternaam', 'status', 'afspraak_datum']])
        
        sel_id = st.selectbox("Selecteer Dossier ID", df['id'].tolist())
        reg = next(item for item in res.data if item['id'] == sel_id)

        with st.form("update_dossier"):
            st.subheader("Dossier Bijwerken")
            stat = st.selectbox("Status", ["Bevestigd", "In behandeling", "Afgehandeld", "Geannuleerd", "Verwezen"])
            beh_optie = st.selectbox("Afgehandeld?", ["Nee", "Ja"], index=1 if reg.get('behandeld') else 0)
            stappen = st.text_area("Volgende stappen voor cliënt", value=str(reg.get('volgende_stappen') or ""))
            verslag = st.text_area("Intern verslag", value=str(reg.get('intern_verslag') or ""))
            mail_tekst = st.text_area("Toelichting voor cliënt")
            
            if st.form_submit_button("Opslaan & Update Mailen"):
                is_beh = (beh_optie == "Ja")
                supabase.table("aanvragen").update({
                    "status": stat, "behandeld": is_beh, "volgende_stappen": stappen, "intern_verslag": verslag
                }).eq("id", sel_id).execute()
                
                # Update Mail naar Cliënt
                html_update = template_client_update(f"{reg['voornaam']} {reg['achternaam']}", stat, mail_tekst, stappen)
                stuur_mail(reg['email'], "Update Grondzaken Dossier", html_update)
                
                st.success("Dossier bijgewerkt en cliënt genotificeerd.")
                st.rerun()

elif menu == "Rapportages":
    st.header("📊 Rapportages")
    res = supabase.table("aanvragen").select("*").execute()
    if res.data:
        df_rep = pd.DataFrame(res.data)
        st.dataframe(df_rep)

elif menu == "Agenda":
    st.header("📅 Agenda")
    res = supabase.table("aanvragen").select("*").execute()
    if res.data:
        events = [{"title": f"{r['voornaam']} {r['achternaam']}", "start": r['afspraak_datum']} for r in res.data]
        calendar(events=events)

elif menu == "Systeembeheer":
    st.header("⚙️ Beheer Medewerkers")
    # ... (Systeembeheer code blijft gelijk aan vorige versie)

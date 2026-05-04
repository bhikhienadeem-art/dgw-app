import streamlit as st
from supabase import create_client, Client
import datetime
import pandas as pd
import smtplib
from email.mime.text import MIMEText
from email.mime.multipart import MIMEMultipart
from email.mime.application import MIMEApplication
from streamlit_calendar import calendar
import os

# --- 1. CONFIGURATIE & VISUELE IDENTITEIT ---
st.set_page_config(page_title="DGW Wanica Centrum - Officiële Registratie", layout="wide")

# Verbinding met Supabase
supabase = create_client(st.secrets["SUPABASE_URL"], st.secrets["SUPABASE_KEY"])

# Sidebar met Logo en Officiële Benaming
with st.sidebar:
    logo_path = "orgineel logo Centrum.png"
    if os.path.exists(logo_path):
        st.image(logo_path, use_container_width=True)
    
    st.markdown("<h2 style='text-align: center;'>DGW Wanica Centrum</h2>", unsafe_allow_html=True)
    st.divider()

# --- COMMUNICATIE SERVICE (E-MAIL) ---
def stuur_notificatie(ontvanger, onderwerp, html_inhoud, bijlagen=None):
    try:
        msg = MIMEMultipart()
        msg['Subject'] = onderwerp
        msg['From'] = f"DGW Wanica Centrum <{st.secrets['EMAIL_USER']}>"
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
    st.sidebar.subheader("🔐 Medewerker Portaal")
    res_m = supabase.table("medewerkers").select("*").execute()
    user_list = [u['gebruikersnaam'] for u in res_m.data] if res_m.data else []
    u_sel = st.sidebar.selectbox("Gebruikersnaam", ["Selecteer gebruiker"] + user_list)
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
    st.header("📝 Nieuwe Registratie Dienst Grondzaken")
    
    with st.container():
        col1, col2 = st.columns(2)
        with col1:
            vnaam = st.text_input("Voornaam *")
            anaam = st.text_input("Achternaam *")
            email = st.text_input("E-mailadres *")
        with col2:
            id_nr = st.text_input("ID-Nummer *")
            tel = st.text_input("Telefoonnummer *")
            lad_nr = st.text_input("LAD Nummer (indien van toepassing)")
    
    bericht = st.text_area("Omschrijving van het verzoek *")
    geuploade_bestanden = st.file_uploader("Relevante documentatie uploaden", accept_multiple_files=True)
    
    st.divider()
    st.markdown("### Afspraak inplannen")
    st.info("Indien u een afspraak wenst, gelieve een datum en tijdstip te selecteren (beschikbaar op maandag en woensdag).")
    
    datum = st.date_input("Voorkeursdatum", min_value=datetime.date.today())
    
    if datum.weekday() not in [0, 2]:
        st.warning("Let op: Afspraken op locatie zijn uitsluitend mogelijk op maandag en woensdag.")
    else:
        tijdsblokken = [f"{h:02d}:{m:02d}" for h in range(8, 15) for m in (0, 15, 30, 45) if not (h == 14 and m > 30)]
        tijd_sel = st.selectbox("Beschikbare tijdstippen", tijdsblokken)

        if st.button("Registratie Indienen"):
            if all([vnaam, anaam, email, id_nr, bericht]):
                try:
                    supabase.table("aanvragen").insert({
                        "voornaam": vnaam, "achternaam": anaam, "email": email, "id_nummer": id_nr,
                        "telefoon": tel, "lad_nummer": lad_nr, "afspraak_datum": str(datum),
                        "afspraak_tijd": tijd_sel, "status": "In behandeling", "bericht": bericht
                    }).execute()
                    
                    # Interne notificatie (image_65757b.png)
                    html_msg = f"""
                    <div style='font-family: Arial, sans-serif;'>
                        <h2 style='color: #2c3e50;'>Nieuwe Registratie Ontvangen</h2>
                        <p>Er is een nieuwe aanvraag ingediend door <b>{vnaam} {anaam}</b>.</p>
                        <hr>
                        <p><b>Identificatie:</b> {id_nr}<br>
                        <b>Geplande afspraak:</b> {datum} om {tijd_sel}</p>
                        <p><b>Omschrijving:</b><br>{bericht}</p>
                    </div>
                    """
                    stuur_notificatie(st.secrets['EMAIL_USER'], f"Nieuwe Registratie: {anaam}", html_msg, geuploade_bestanden)
                    
                    st.success("Uw registratie is succesvol verwerkt. Er is een notificatie verzonden naar de betreffende afdeling.")
                except Exception as e:
                    st.error(f"Fout bij opslaan: {e}")
            else:
                st.error("Gelieve alle verplichte velden (gemarkeerd met *) in te vullen.")

elif menu == "📋 Dossierbeheer":
    st.header("📋 Dossierbeheer & Rapportage")
    res = supabase.table("aanvragen").select("*").order('id', desc=True).execute()
    if res.data:
        df = pd.DataFrame(res.data)
        st.dataframe(df[['id', 'voornaam', 'achternaam', 'status', 'afspraak_datum']], use_container_width=True)
        
        sel_id = st.selectbox("Selecteer dossier ID voor verwerking", df['id'].tolist())
        reg = next(item for item in res.data if item['id'] == sel_id)

        st.subheader("Dossier & Rapportage Bijwerken")
        with st.form("update_form"):
            stat = st.selectbox("Actuele Status", ["Bevestigd", "In behandeling", "Afgehandeld", "Geannuleerd", "Verwezen"], 
                               index=["Bevestigd", "In behandeling", "Afgehandeld", "Geannuleerd", "Verwezen"].index(reg['status']))
            
            # Professionele afhandeling van de status (image_65f4c3.png)
            afgehandeld_input = st.selectbox("Dossier volledig afgehandeld?", ["Nee", "Ja"], index=1 if reg.get('behandeld') else 0)
            
            stappen = st.text_area("Vervolgstappen (gecommuniceerd naar cliënt)", value=str(reg.get('volgende_stappen') or ""))
            verslag = st.text_area("Intern verslag (strikt vertrouwelijk)", value=str(reg.get('intern_verslag') or ""))
            mail_tekst = st.text_area("Aanvullende toelichting voor cliënt (e-mail)")

            if st.form_submit_button("Wijzigingen Definitief Opslaan"):
                is_afgehandeld = (afgehandeld_input == "Ja")
                
                supabase.table("aanvragen").update({
                    "status": stat, 
                    "behandeld": is_afgehandeld, 
                    "volgende_stappen": stappen, 
                    "intern_verslag": verslag
                }).eq("id", sel_id).execute()
                
                if mail_tekst:
                    stuur_notificatie(reg['email'], "Update betreffende uw registratie - DGW", f"<p>{mail_tekst}</p>")
                
                st.success("Het dossier is succesvol geactualiseerd.")
                st.rerun()

elif menu == "⚙️ Systeeminstellingen":
    st.header("⚙️ Beheer Medewerkers")
    res_m = supabase.table("medewerkers").select("*").execute()
    if res_m.data:
        for m in res_m.data:
            c1, c2 = st.columns([4, 1])
            c1.info(f"Gebruiker: **{m['gebruikersnaam']}** | Rol: {m['rol']}")
            if c2.button("Verwijderen", key=f"del_{m['id']}"):
                supabase.table("medewerkers").delete().eq("id", m['id']).execute()
                st.rerun()
    
    with st.expander("➕ Nieuwe Medewerker Toevoegen"):
        with st.form("new_user"):
            new_u = st.text_input("Gebruikersnaam")
            new_p = st.text_input("Wachtwoord", type="password")
            if st.form_submit_button("Account Aanmaken"):
                supabase.table("medewerkers").insert({"gebruikersnaam": new_u, "wachtwoord": new_p, "rol": "Medewerker"}).execute()
                st.rerun()

elif menu == "📅 Agenda":
    st.header("📅 Afsprakenoverzicht")
    res = supabase.table("aanvragen").select("*").execute()
    if res.data:
        events = [{"title": f"{r['voornaam']} {r['achternaam']}", "start": r['afspraak_datum']} for r in res.data]
        calendar(events=events)

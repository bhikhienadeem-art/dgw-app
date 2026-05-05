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
st.set_page_config(page_title="Registratie Dienst Grondzaken Wanica Centrum", layout="wide")

# Verbinding met Supabase
supabase = create_client(st.secrets["SUPABASE_URL"], st.secrets["SUPABASE_KEY"])

# Sidebar met Logo en Officiële Benaming
with st.sidebar:
    logo_path = "orgineel logo Centrum.png"
    if os.path.exists(logo_path):
        st.image(logo_path, use_container_width=True)
    
    st.markdown("<h2 style='text-align: center;'>DGW Wanica Centrum</h2>", unsafe_allow_html=True)
    st.divider()

# --- COMMUNICATIE SERVICE ---
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
    except Exception:
        pass

# --- 2. AUTHENTICATIE STATUS & LOGIN ---
if 'logged_in' not in st.session_state:
    st.session_state.update({'logged_in': False, 'role': None, 'user': None})

# Login sectie in Sidebar (Alleen tonen als niet ingelogd)
if not st.session_state.logged_in:
    with st.sidebar:
        st.subheader("🔐 Medewerker Login")
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
                else:
                    st.error("Onjuiste gegevens")
        except Exception:
            st.warning("Database verbinding...")

# --- 3. MENU NAVIGATIE ---
menu_options = ["📝 Nieuwe Registratie"]
if st.session_state.logged_in:
    menu_options += ["📋 Dossierbeheer", "📅 Agenda", "📊 Rapportages", "⚙️ Systeeminstellingen"]
    if st.sidebar.button("🚪 Uitloggen"):
        st.session_state.logged_in = False
        st.rerun()

menu = st.sidebar.radio("Hoofdmenu", menu_options)

# --- 4. PAGINA LOGICA ---

# --- REGISTRATIESCHERM (ONGEWIJZIGD) ---
if menu == "📝 Nieuwe Registratie":
    st.header("📝 Registratie Dienst Grondzaken Wanica Centrum")
    with st.form("registratie_form", clear_on_submit=True):
        col1, col2 = st.columns(2)
        with col1:
            vnaam = st.text_input("Voornaam *")
            anaam = st.text_input("Achternaam *")
            email = st.text_input("E-mailadres *")
        with col2:
            id_nr = st.text_input("ID-Nummer *")
            tel = st.text_input("Telefoonnummer *")
            lad_nr = st.text_input("LAD Nummer")
        
        bericht = st.text_area("Omschrijving van het verzoek *")
        geuploade_bestanden = st.file_uploader("Documentatie uploaden", accept_multiple_files=True)
        
        st.divider()
        st.markdown("### Afspraak inplannen")
        st.info("Indien u een afspraak wenst, gelieve een datum en tijdstip te selecteren (beschikbaar op maandag en woensdag).")
        
        datum = st.date_input("Voorkeursdatum", min_value=datetime.date.today())
        
        tijd_keuze = None
        if datum.weekday() in [0, 2]:
            tijdsblokken = [f"{h:02d}:{m:02d}" for h in range(8, 15) for m in (0, 15, 30, 45) if not (h == 14 and m > 30)]
            res_t = supabase.table("aanvragen").select("afspraak_tijd").eq("afspraak_datum", str(datum)).execute()
            bezet = [r['afspraak_tijd'] for r in res_t.data] if res_t.data else []
            tijd_keuze = st.selectbox("Kies een tijdstip", ["---"] + [t for t in tijdsblokken if t not in bezet])
        else:
            st.warning("Afspraken uitsluitend op maandag en woensdag.")

        if st.form_submit_button("Indienen"):
            if all([vnaam, anaam, email, id_nr, bericht]) and tijd_keuze != "---":
                supabase.table("aanvragen").insert({
                    "voornaam": vnaam, "achternaam": anaam, "email": email, "id_nummer": id_nr,
                    "telefoon": tel, "lad_nummer": lad_nr, "afspraak_datum": str(datum),
                    "afspraak_tijd": tijd_keuze, "status": "In behandeling", "bericht": bericht
                }).execute()
                
                html_msg = f"<h3>Nieuwe Aanvraag</h3><p>Cliënt: {vnaam} {anaam}</p>"
                stuur_notificatie(st.secrets['EMAIL_USER'], f"Nieuwe Registratie: {anaam}", html_msg, geuploade_bestanden)
                st.success("✅ Succesvol geregistreerd!")
            else:
                st.error("Vul alle velden in.")

# --- DOSSIERBEHEER (UITGEBREID OVERZICHT) ---
elif menu == "📋 Dossierbeheer":
    st.header("📋 Dossierbeheer")
    
    # Haal alle aanvragen op uit de database
    res = supabase.table("aanvragen").select("*").order('id', desc=True).execute()
    
    if res.data:
        df = pd.DataFrame(res.data)
        # Toon eerst de beknopte tabel
        st.dataframe(df[['id', 'voornaam', 'achternaam', 'status', 'afspraak_datum']], use_container_width=True)
        
        st.divider()
        
        # Selectie voor detailoverzicht
        sel_id = st.selectbox("Selecteer Dossier ID voor alle details en verwerking", df['id'].tolist())
        reg = next(item for item in res.data if item['id'] == sel_id)

        # Toon ALLE gegevens van de geregistreerde
        st.subheader(f"Details van dossier: {reg['id']}")
        col1, col2 = st.columns(2)
        
        with col1:
            st.write(f"**Naam:** {reg['voornaam']} {reg['achternaam']}")
            st.write(f"**E-mail:** {reg['email']}")
            st.write(f"**Telefoon:** {reg['telefoon']}")
            st.write(f"**ID-Nummer:** {reg['id_nummer']}")
            st.write(f"**LAD Nummer:** {reg.get('lad_nummer') or 'Niet opgegeven'}")
            
        with col2:
            st.write(f"**Afspraakdatum:** {reg['afspraak_datum']}") # cite: image_6432a9.png
            st.write(f"**Afspraaktijd:** {reg['afspraak_tijd']}") # cite: image_642724.png
            st.write(f"**Huidige Status:** {reg['status']}")
            st.write(f"**Omschrijving verzoek:**")
            st.info(reg['bericht'])

        # Formulier voor status-updates en rapportage
        with st.form("update_dossier_uitgebreid"):
            stat = st.selectbox("Status aanpassen", ["Bevestigd", "In behandeling", "Afgehandeld", "Geannuleerd"], 
                               index=["Bevestigd", "In behandeling", "Afgehandeld", "Geannuleerd"].index(reg['status']))
            verslag = st.text_area("Intern Verslag / Rapportage", value=str(reg.get('intern_verslag') or ""))
            
            if st.form_submit_button("Wijzigingen Opslaan"):
                supabase.table("aanvragen").update({
                    "status": stat, 
                    "intern_verslag": verslag
                }).eq("id", sel_id).execute()
                st.success(f"Dossier {sel_id} succesvol bijgewerkt!")
                st.rerun()
    else:
        st.info("Er zijn momenteel geen dossiers geregistreerd.")
    else:
        st.info("Er zijn momenteel geen dossiers geregistreerd.")

# --- AGENDA (HERSTELD) ---
elif menu == "📅 Agenda":
    st.header("📅 Afspraken Agenda")
    res = supabase.table("aanvragen").select("*").execute()
    if res.data:
        events = [{"title": f"{r['voornaam']} {r['achternaam']} ({r['afspraak_tijd']})", "start": r['afspraak_datum']} for r in res.data]
        calendar(events=events)
    else:
        st.info("De agenda is momenteel leeg.")

# --- RAPPORTAGES (HERSTELD) ---
elif menu == "📊 Rapportages":
    st.header("📊 Rapportages & Export")
    res = supabase.table("aanvragen").select("*").execute()
    if res.data:
        df = pd.DataFrame(res.data)
        st.dataframe(df)
        csv = df.to_csv(index=False).encode('utf-8')
        st.download_button("Export Data naar CSV", csv, "dgw_rapportage.csv", "text/csv")

# --- SYSTEEMINSTELLINGEN (HERSTELD) ---
elif menu == "⚙️ Systeeminstellingen":
    st.header("⚙️ Systeeminstellingen")
    st.subheader("Medewerkers Beheren")
    res_m = supabase.table("medewerkers").select("*").execute()
    if res_m.data:
        for m in res_m.data:
            c1, c2 = st.columns([3, 1])
            c1.write(f"👤 **{m['gebruikersnaam']}** ({m['rol']})")
            if c2.button("Verwijder", key=f"del_{m['id']}"):
                supabase.table("medewerkers").delete().eq("id", m['id']).execute()
                st.rerun()
    
    st.divider()
    st.subheader("Nieuwe Medewerker Toevoegen")
    with st.form("add_user"):
        new_u = st.text_input("Nieuwe Gebruikersnaam")
        new_p = st.text_input("Nieuw Wachtwoord", type="password")
        new_r = st.selectbox("Rol", ["Medewerker", "Admin"])
        if st.form_submit_button("Account Toevoegen"):
            supabase.table("medewerkers").insert({"gebruikersnaam": new_u, "wachtwoord": new_p, "rol": new_r}).execute()
            st.success("Medewerker succesvol toegevoegd!")
            st.rerun()

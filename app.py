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
st.set_page_config(page_title="DGW Wanica Centrum", layout="wide")

# Verbinding met Supabase
supabase = create_client(st.secrets["SUPABASE_URL"], st.secrets["SUPABASE_KEY"])

# --- MAIL FUNCTIE ---
def stuur_mail_met_bijlagen(ontvanger, onderwerp, html_inhoud, bestanden=None):
    try:
        msg = MIMEMultipart()
        msg['Subject'] = onderwerp
        msg['From'] = f"DGW Wanica Centrum <{st.secrets['EMAIL_USER']}>"
        msg['To'] = ontvanger
        msg.attach(MIMEText(html_inhoud, 'html'))
        
        if bestanden:
            for f in bestanden:
                part = MIMEApplication(f.read(), Name=f.name)
                part['Content-Disposition'] = f'attachment; filename="{f.name}"'
                msg.attach(part)
                f.seek(0)
        
        with smtplib.SMTP_SSL('smtp.gmail.com', 465) as server:
            server.login(st.secrets["EMAIL_USER"], st.secrets["EMAIL_PASS"])
            server.send_message(msg)
    except Exception as e:
        st.error(f"E-mail fout: {e}")

# --- MAIL TEMPLATES ---
def template_bevestiging(naam, datum, tijd):
    return f"<html><body style='font-family:Arial;'><div style='background:#2e7d32;padding:10px;color:white;'><h2>Bevestiging</h2></div><p>Beste <b>{naam}</b>, uw registratie voor {datum} om {tijd} is ontvangen.</p></body></html>"

def template_intern(data):
    return f"<html><body style='font-family:Arial;'><div style='background:#444;padding:10px;color:white;'><h2>Nieuwe Aanvraag</h2></div><p><b>Cliënt:</b> {data['vnaam']} {data['anaam']}<br><b>ID:</b> {data['id_nr']}<br><b>Bericht:</b> {data['bericht']}</p></body></html>"

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
menu_options = ["📝 Nieuwe Aanvraag DGW"]
if st.session_state.logged_in:
    menu_options += ["📋 Beheer Registraties", "📅 Agenda", "📊 Rapportages", "⚙️ Systeembeheer"]
    if st.sidebar.button("🚪 Uitloggen"):
        st.session_state.logged_in = False
        st.rerun()

menu = st.sidebar.radio("Hoofdmenu", menu_options)

# --- 4. PAGINA'S ---

if menu == "📝 Nieuwe Aanvraag DGW":
    st.header("📝 Nieuwe Registratie Dienst Grondzaken")
    col1, col2 = st.columns(2)
    with col1:
        vnaam = st.text_input("Voornaam *")
        anaam = st.text_input("Achternaam *")
        email = st.text_input("E-mailadres *")
    with col2:
        id_nr = st.text_input("ID-Nummer *")
        tel = st.text_input("Telefoonnummer *")
        lad_nr = st.text_input("LAD Nummer")
    
    bericht = st.text_area("Omschrijving *")
    bestanden = st.file_uploader("Documenten", accept_multiple_files=True)
    datum = st.date_input("Datum", min_value=datetime.date.today())
    
    tijdsblokken = [f"{h:02d}:{m:02d}" for h in range(8, 15) for m in (0, 15, 30, 45) if not (h == 14 and m > 30)]
    tijd = st.selectbox("Tijdstip", tijdsblokken)

    if st.button("Verzenden"):
        if all([vnaam, anaam, email, id_nr, bericht]):
            # Opslaan in database
            supabase.table("aanvragen").insert({
                "voornaam": vnaam, "achternaam": anaam, "email": email, "id_nummer": id_nr,
                "telefoon": tel, "lad_nummer": lad_nr, "afspraak_datum": str(datum),
                "afspraak_tijd": tijd, "status": "In behandeling", "bericht": bericht
            }).execute()
            
            # Mails versturen
            stuur_mail_met_bijlagen(email, "Bevestiging Registratie", template_bevestiging(vnaam, datum, tijd))
            stuur_mail_met_bijlagen(st.secrets['EMAIL_USER'], f"Nieuwe Registratie: {anaam}", 
                                   template_intern({"vnaam":vnaam, "anaam":anaam, "id_nr":id_nr, "bericht":bericht}), bestanden)
            
            st.success("✅ Uw aanvraag is succesvol verzonden!")
        else:
            st.error("Vul alle verplichte velden in.")

elif menu == "📋 Beheer Registraties":
    st.header("📋 Beheer Registraties")
    res = supabase.table("aanvragen").select("*").order('created_at', desc=True).execute()
    if res.data:
        df = pd.DataFrame(res.data)
        st.table(df[['id', 'voornaam', 'achternaam', 'status', 'afspraak_datum']])
        
        sel_id = st.selectbox("Dossier ID selecteren", df['id'].tolist())
        reg = next(item for item in res.data if item['id'] == sel_id)

        st.subheader(f"Dossier Bewerken: {reg['voornaam']} {reg['achternaam']}")
        with st.form("update_form"):
            stat = st.selectbox("Status", ["Bevestigd", "In behandeling", "Afgehandeld", "Geannuleerd", "Verwezen"], 
                               index=["Bevestigd", "In behandeling", "Afgehandeld", "Geannuleerd", "Verwezen"].index(reg['status']))
            
            # FIX: Database verwacht boolean (True/False)
            afgehandeld_keuze = st.selectbox("Dossier volledig afgehandeld?", ["Nee", "Ja"], index=1 if reg.get('behandeld') else 0)
            stappen = st.text_area("Volgende stappen voor cliënt", value=str(reg.get('volgende_stappen') or ""))
            verslag = st.text_area("Intern verslag", value=str(reg.get('intern_verslag') or ""))
            update_mail = st.text_area("Update mail naar cliënt")

            if st.form_submit_button("Wijzigingen Opslaan"):
                is_afgehandeld = True if afgehandeld_keuze == "Ja" else False
                supabase.table("aanvragen").update({
                    "status": stat, 
                    "behandeld": is_afgehandeld, 
                    "volgende_stappen": stappen, 
                    "intern_verslag": verslag
                }).eq("id", sel_id).execute()
                
                if update_mail:
                    stuur_mail_met_bijlagen(reg['email'], "Update uw Dossier", f"<html><body><p>{update_mail}</p></body></html>")
                
                st.success("✅ Dossier bijgewerkt!")
                st.rerun()

elif menu == "📊 Rapportages":
    st.header("📊 Rapportages")
    res = supabase.table("aanvragen").select("*").execute()
    if res.data:
        df_rep = pd.DataFrame(res.data)
        st.dataframe(df_rep[['id', 'voornaam', 'achternaam', 'status', 'afspraak_datum']])
        st.download_button("📥 Exporteer naar CSV", df_rep.to_csv(index=False), "dgw_rapport.csv")

elif menu == "📅 Agenda":
    st.header("📅 Agenda")
    res = supabase.table("aanvragen").select("*").execute()
    if res.data:
        events = [{"title": f"{r['voornaam']} {r['achternaam']}", "start": r['afspraak_datum']} for r in res.data]
        calendar(events=events)

elif menu == "⚙️ Systeembeheer":
    st.header("⚙️ Beheer Medewerkers")
    res_m = supabase.table("medewerkers").select("*").execute()
    if res_m.data:
        for m in res_m.data:
            col1, col2 = st.columns([3, 1])
            col1.write(f"👤 {m['gebruikersnaam']} ({m['rol']})")
            if col2.button("Verwijder", key=f"del_{m['id']}"):
                supabase.table("medewerkers").delete().eq("id", m['id']).execute()
                st.rerun()
    
    with st.expander("➕ Nieuwe Medewerker Toevoegen"):
        with st.form("new_med"):
            u = st.text_input("Gebruikersnaam")
            p = st.text_input("Wachtwoord", type="password")
            r = st.selectbox("Rol", ["Medewerker", "Admin"])
            if st.form_submit_button("Account Aanmaken"):
                supabase.table("medewerkers").insert({"gebruikersnaam": u, "wachtwoord": p, "rol": r}).execute()
                st.rerun()

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

# --- PROFESSIONELE MAIL FUNCTIES ---
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
def template_bevestiging_aanvraag(naam, datum, tijd):
    return f"<html><body style='font-family:Arial;'><h2>Bevestiging Registratie</h2><p>Beste <b>{naam}</b>, uw aanvraag voor {datum} om {tijd} is ontvangen.</p></body></html>"

def template_nieuwe_aanvraag_intern(data):
    return f"<html><body style='font-family:Arial;'><h2>Nieuwe Aanvraag</h2><p><b>Cliënt:</b> {data['vnaam']} {data['anaam']}<br><b>Bericht:</b> {data['bericht']}</p></body></html>"

def template_client_update(naam, status, toelichting, stappen):
    return f"<html><body style='font-family:Arial;'><h2>Dossier Update</h2><p>Beste {naam}, uw status is nu: <b>{status}</b></p><p>{toelichting}</p></body></html>"

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
    st.header("📝 Nieuwe Registratie")
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
    
    if datum.weekday() not in [0, 2]:
        st.warning("Afspraken alleen op Maandag en Woensdag.")
    else:
        # Tijdselectie en opslaan (gelijk aan eerdere versies)
        tijd = st.selectbox("Tijdstip", [f"{h:02d}:{m:02d}" for h in range(8, 15) for m in (0, 15, 30, 45) if not (h == 14 and m > 30)])
        if st.button("Verzenden"):
            supabase.table("aanvragen").insert({"voornaam":vnaam, "achternaam":anaam, "email":email, "id_nummer":id_nr, "afspraak_datum":str(datum), "afspraak_tijd":tijd, "bericht":bericht, "status":"In behandeling"}).execute()
            stuur_mail_met_bijlagen(email, "Bevestiging", template_bevestiging_aanvraag(vnaam, datum, tijd))
            stuur_mail_met_bijlagen(st.secrets['EMAIL_USER'], "Nieuwe Aanvraag", template_nieuwe_aanvraag_intern({"vnaam":vnaam, "anaam":anaam, "bericht":bericht}), bestanden)
            st.success("Verzonden!")

elif menu == "Beheer Registraties":
    st.header("📋 Beheer")
    res = supabase.table("aanvragen").select("*").order('created_at', desc=True).execute()
    if res.data:
        df = pd.DataFrame(res.data)
        st.dataframe(df[['id', 'voornaam', 'achternaam', 'status']])
        sel_id = st.selectbox("Selecteer dossier", df['id'].tolist())
        reg = next(item for item in res.data if item['id'] == sel_id)
        
        with st.expander("🗑️ Dossier Verwijderen"):
            if st.button("Definitief verwijderen"):
                supabase.table("aanvragen").delete().eq("id", sel_id).execute()
                st.rerun()

        with st.form("update"):
            stat = st.selectbox("Status", ["Bevestigd", "In behandeling", "Afgehandeld", "Geannuleerd"], index=0)
            verslag = st.text_area("Intern Verslag", value=str(reg.get('intern_verslag') or ""))
            mail_txt = st.text_area("Mail naar klant")
            if st.form_submit_button("Update"):
                supabase.table("aanvragen").update({"status":stat, "intern_verslag":verslag}).eq("id", sel_id).execute()
                stuur_mail_met_bijlagen(reg['email'], "Dossier Update", template_client_update(reg['voornaam'], stat, mail_txt, ""))
                st.success("Bijgewerkt")
                st.rerun()

elif menu == "Rapportages":
    st.header("📊 Rapportages")
    res = supabase.table("aanvragen").select("*").execute()
    if res.data:
        df_rep = pd.DataFrame(res.data)
        st.dataframe(df_rep)
        st.download_button("Download CSV", df_rep.to_csv(), "rapport.csv")

elif menu == "Agenda":
    st.header("📅 Agenda")
    res = supabase.table("aanvragen").select("*").execute()
    if res.data:
        events = [{"title": f"{r['voornaam']} {r['achternaam']}", "start": r['afspraak_datum']} for r in res.data]
        calendar(events=events)

elif menu == "Systeembeheer":
    st.header("⚙️ Systeembeheer")
    res_m = supabase.table("medewerkers").select("*").execute()
    if res_m.data:
        m_df = pd.DataFrame(res_m.data)
        for i, row in m_df.iterrows():
            c1, c2, c3 = st.columns(3)
            c1.write(row['gebruikersnaam'])
            if c2.button("Wachtwoord reset naar '1234'", key=f"r_{row['id']}"):
                supabase.table("medewerkers").update({"wachtwoord": "1234"}).eq("id", row['id']).execute()
            if c3.button("Verwijder", key=f"d_{row['id']}"):
                supabase.table("medewerkers").delete().eq("id", row['id']).execute()
                st.rerun()
    
    with st.form("add_med"):
        new_u = st.text_input("Nieuwe Gebruiker")
        new_p = st.text_input("Wachtwoord", type="password")
        if st.form_submit_button("Toevoegen"):
            supabase.table("medewerkers").insert({"gebruikersnaam":new_u, "wachtwoord":new_p, "rol":"Medewerker"}).execute()
            st.rerun()

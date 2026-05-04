import streamlit as st
from supabase import create_client, Client
import datetime
import pandas as pd
import smtplib
from email.mime.text import MIMEText
from email.mime.multipart import MIMEMultipart
from email.mime.application import MIMEApplication
from streamlit_calendar import calendar

# --- 1. CONFIGURATIE ---
st.set_page_config(page_title="Registratie Dienst Grondzaken Wanica Centrum", layout="wide")

# Verbinding met Supabase
supabase = create_client(st.secrets["SUPABASE_URL"], st.secrets["SUPABASE_KEY"])

# --- ZIJKANT: LOGO EN TITEL ---
# Hier wordt het logo exact teruggeplaatst zoals in je eerdere werkende versies
with st.sidebar:
    st.image("https://upload.wikimedia.org/wikipedia/commons/thumb/1/12/Coat_of_arms_of_Suriname.svg/800px-Coat_of_arms_of_Suriname.svg.png", width=150)
    st.markdown("<h2 style='text-align: center;'>DGW Wanica Centrum</h2>", unsafe_allow_html=True)
    st.divider()

# --- MAIL FUNCTIE ---
def stuur_mail_compleet(ontvanger, onderwerp, html_inhoud, bestanden=None):
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
    st.header("Registratie Dienst Grondzaken Wanica Centrum")
    
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
    
    # TIJDSLOTS (Maandag en Woensdag)
    if datum.weekday() not in [0, 2]:
        st.warning("⚠️ Afspraken zijn enkel mogelijk op maandag en woensdag.")
    else:
        st.subheader("⏰ Beschikbare Tijden")
        tijdsblokken = [f"{h:02d}:{m:02d}" for h in range(8, 15) for m in (0, 15, 30, 45) if not (h == 14 and m > 30)]
        res_t = supabase.table("aanvragen").select("afspraak_tijd").eq("afspraak_datum", str(datum)).execute()
        bezet = [r['afspraak_tijd'] for r in res_t.data] if res_t.data else []
        
        cols = st.columns(6)
        for i, tijd_slot in enumerate(tijdsblokken):
            is_bezet = tijd_slot in bezet
            if cols[i % 6].button(f"🚫 {tijd_slot}" if is_bezet else tijd_slot, key=f"t_{tijd_slot}", disabled=is_bezet):
                st.session_state.sel_tijd = tijd_slot
        
        if 'sel_tijd' in st.session_state:
            st.info(f"Geselecteerd: **{st.session_state.sel_tijd}**")

    if st.button("Registratie Verzenden"):
        if all([vnaam, anaam, email, id_nr, bericht]) and 'sel_tijd' in st.session_state:
            supabase.table("aanvragen").insert({
                "voornaam": vnaam, "achternaam": anaam, "email": email, "id_nummer": id_nr,
                "telefoon": tel, "lad_nummer": lad_nr, "afspraak_datum": str(datum),
                "afspraak_tijd": st.session_state.sel_tijd, "status": "In behandeling", "bericht": bericht
            }).execute()
            
            # Professionele mail naar cliënt & medewerker
            html_msg = f"<h3>Nieuwe Registratie</h3><p><b>Naam:</b> {vnaam} {anaam}</p><p><b>Tijd:</b> {datum} om {st.session_state.sel_tijd}</p>"
            stuur_mail_compleet(st.secrets['EMAIL_USER'], f"Nieuwe Aanvraag: {anaam}", html_msg, geuploade_bestanden)
            
            st.success("✅ Uw aanvraag is succesvol verzonden!")
            del st.session_state.sel_tijd
        else:
            st.error("Vul alle velden in en kies een tijdstip.")

elif menu == "📋 Beheer Registraties":
    st.header("Beheer Cliëntendossiers")
    res = supabase.table("aanvragen").select("*").order('created_at', desc=True).execute()
    if res.data:
        df = pd.DataFrame(res.data)
        st.dataframe(df[['id', 'voornaam', 'achternaam', 'status', 'afspraak_datum']])
        
        sel_id = st.selectbox("Selecteer Dossier", df['id'].tolist())
        reg = next(item for item in res.data if item['id'] == sel_id)

        with st.form("update_form"):
            stat = st.selectbox("Status", ["Bevestigd", "In behandeling", "Afgehandeld", "Geannuleerd", "Verwezen"], index=0)
            afgehandeld_bool = st.selectbox("Dossier afgehandeld?", ["Nee", "Ja"], index=1 if reg.get('behandeld') else 0)
            verslag = st.text_area("Intern verslag", value=str(reg.get('intern_verslag') or ""))
            
            if st.form_submit_button("Opslaan"):
                supabase.table("aanvragen").update({
                    "status": stat, 
                    "behandeld": (afgehandeld_bool == "Ja"), 
                    "intern_verslag": verslag
                }).eq("id", sel_id).execute()
                st.success("Bijgewerkt!")
                st.rerun()

elif menu == "⚙️ Systeembeheer":
    st.header("Systeembeheer: Medewerkers")
    res_m = supabase.table("medewerkers").select("*").execute()
    if res_m.data:
        for m in res_m.data:
            c1, c2, c3 = st.columns([2, 2, 1])
            c1.write(f"**{m['gebruikersnaam']}**")
            with c2.popover("🔑 Wachtwoord"):
                np = st.text_input("Nieuw wachtwoord", type="password", key=f"pw_{m['id']}")
                if st.button("Update", key=f"btn_{m['id']}"):
                    supabase.table("medewerkers").update({"wachtwoord": np}).eq("id", m['id']).execute()
                    st.success("Wachtwoord gewijzigd!")
            if c3.button("🗑️", key=f"del_{m['id']}"):
                supabase.table("medewerkers").delete().eq("id", m['id']).execute()
                st.rerun()
    
    with st.expander("➕ Medewerker Toevoegen"):
        with st.form("add"):
            un = st.text_input("Gebruikersnaam")
            pw = st.text_input("Wachtwoord", type="password")
            if st.form_submit_button("Aanmaken"):
                supabase.table("medewerkers").insert({"gebruikersnaam": un, "wachtwoord": pw, "rol": "Medewerker"}).execute()
                st.rerun()

# --- Overige pagina's (Agenda & Rapport) ---
elif menu == "📅 Agenda":
    st.header("Agenda")
    res = supabase.table("aanvragen").select("*").execute()
    if res.data:
        calendar([{"title": f"{r['voornaam']} {r['achternaam']}", "start": r['afspraak_datum']} for r in res.data])

elif menu == "📊 Rapportages":
    st.header("Rapportages")
    res = supabase.table("aanvragen").select("*").execute()
    if res.data:
        st.dataframe(pd.DataFrame(res.data))

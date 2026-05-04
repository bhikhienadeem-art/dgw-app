import streamlit as st
from supabase import create_client, Client
import datetime
import pandas as pd
import smtplib
from email.mime.text import MIMEText
from email.mime.multipart import MIMEMultipart
from streamlit_calendar import calendar

# --- 1. INITIALISATIE ---
# Titel overal aangepast naar de gewenste weergave
st.set_page_config(page_title="Registratie Dienst Grondzaken Wanica Centrum", layout="wide")

# Verbinding met Supabase
supabase = create_client(st.secrets["SUPABASE_URL"], st.secrets["SUPABASE_KEY"])

# --- MAIL FUNCTIE ---
def stuur_mail(ontvanger, onderwerp, inhoud):
    try:
        msg = MIMEMultipart()
        msg['Subject'] = onderwerp
        msg['From'] = f"DGW Centrum <{st.secrets['EMAIL_USER']}>"
        msg['To'] = ontvanger
        msg.attach(MIMEText(inhoud + "\n\n---\nDistrictscommissariaat Wanica-Centrum", 'plain'))
        with smtplib.SMTP_SSL('smtp.gmail.com', 465) as server:
            server.login(st.secrets["EMAIL_USER"], st.secrets["EMAIL_PASS"])
            server.send_message(msg)
    except Exception as e:
        st.error(f"Mail fout: {e}")

# --- 2. AUTHENTICATIE ---
if 'logged_in' not in st.session_state:
    st.session_state.update({'logged_in': False, 'role': None, 'user': None})

if not st.session_state.logged_in:
    st.sidebar.subheader("🔐 Inloggen")
    res_m = supabase.table("medewerkers").select("*").execute()
    user_list = [u['gebruikersnaam'] for u in res_m.data] if res_m.data else []
    u_sel = st.sidebar.selectbox("Gebruiker", ["---"] + user_list)
    p_inp = st.sidebar.text_input("Wachtwoord", type="password")
    if st.sidebar.button("Inloggen"):
        user_data = next((u for u in res_m.data if u['gebruikersnaam'] == u_sel), None)
        if user_data and user_data['wachtwoord'] == p_inp:
            st.session_state.update({'logged_in': True, 'role': user_data['rol'], 'user': u_sel})
            st.rerun()

# --- 3. NAVIGATIE ---
menu_options = ["Nieuwe Aanvraag DGW"]
if st.session_state.logged_in:
    menu_options += ["Beheer Registraties", "Agenda", "Rapportages", "Systeembeheer"]
    if st.sidebar.button("🚪 Uitloggen"):
        st.session_state.logged_in = False
        st.rerun()

menu = st.sidebar.radio("Menu", menu_options)

# --- 4. PAGINA'S ---

if menu == "Nieuwe Aanvraag DGW":
    st.header("📝 Registratie Dienst Grondzaken Wanica Centrum") # Titel fix
    
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
    st.file_uploader("Documenten uploaden", accept_multiple_files=True) # Upload knop aanwezig
    
    datum = st.date_input("Kies een datum (Maandag of Woensdag)", min_value=datetime.date.today())
    
    if datum.weekday() not in [0, 2]: # Maandag en Woensdag check
        st.warning("⚠️ Afspraken zijn enkel mogelijk op maandag en woensdag.")
    else:
        st.subheader("⏰ Beschikbare Tijden")
        tijdsblokken = []
        start = datetime.datetime.strptime("08:00", "%H:%M")
        eind = datetime.datetime.strptime("14:30", "%H:%M")
        while start <= eind:
            tijdsblokken.append(start.strftime("%H:%M"))
            start += datetime.timedelta(minutes=15) # 15 minuten intervallen
        
        res_t = supabase.table("aanvragen").select("afspraak_tijd").eq("afspraak_datum", str(datum)).execute()
        bezet = [r['afspraak_tijd'] for r in res_t.data] if res_t.data else []
        
        cols = st.columns(6)
        for i, tijd in enumerate(tijdsblokken):
            is_bezet = tijd in bezet
            if cols[i % 6].button(f"🚫 {tijd}" if is_bezet else tijd, key=f"t_{tijd}", disabled=is_bezet):
                st.session_state.sel_tijd = tijd
        
        if 'sel_tijd' in st.session_state:
            st.info(f"Gekozen tijd: **{st.session_state.sel_tijd}**")

    if st.button("Registratie Verzenden"):
        if all([vnaam, anaam, email, id_nr, bericht]) and 'sel_tijd' in st.session_state:
            supabase.table("aanvragen").insert({
                "voornaam": vnaam, "achternaam": anaam, "email": email, "id_nummer": id_nr,
                "telefoon": tel, "lad_nummer": lad_nr, "afspraak_datum": str(datum),
                "afspraak_tijd": st.session_state.sel_tijd, "status": "In behandeling", "bericht": bericht
            }).execute()
            st.success("✅ Uw aanvraag is succesvol verzonden.")
            if 'sel_tijd' in st.session_state: del st.session_state.sel_tijd
        else:
            st.error("Vul alle verplichte velden in en kies een tijdstip.")

elif menu == "Beheer Registraties":
    st.header("📋 Beheer Registraties")
    res = supabase.table("aanvragen").select("*").order('created_at', desc=True).execute()
    if res.data:
        df = pd.DataFrame(res.data)
        st.dataframe(df[['id', 'voornaam', 'achternaam', 'status']]) # Overzichtstabel
        
        sel_id = st.selectbox("Dossier ID selecteren", df['id'].tolist())
        reg = next(item for item in res.data if item['id'] == sel_id)
        
        st.subheader(f"Dossier Bewerken: {reg['voornaam']} {reg['achternaam']}")
        
        with st.form("update_form"):
            n_status = st.selectbox("Status", ["Bevestigd", "In behandeling", "Afgehandeld", "Geannuleerd", "Verwezen"], 
                                  index=["Bevestigd", "In behandeling", "Afgehandeld", "Geannuleerd", "Verwezen"].index(reg['status']))
            
            # CRUCIALE FIX VOOR BOOLEAN FOUT: 
            # We tonen tekst, maar slaan True/False op in de database.
            huidige_waarde = reg.get('behandeld')
            behandeld_optie = st.selectbox("Dossier volledig afgehandeld?", ["Nee", "Ja"], 
                                          index=1 if huidige_waarde == True else 0)
            
            stappen = st.text_area("Volgende stappen voor cliënt", value=str(reg.get('volgende_stappen') or ""))
            verslag = st.text_area("Intern verslag", value=str(reg.get('intern_verslag') or ""))
            mail_tekst = st.text_area("Toelichting in e-mail", value=str(reg.get('medewerker_toelichting') or ""))
            
            if st.form_submit_button("Wijzigingen Opslaan"):
                # Zet de selectie om naar een echte boolean voor de database
                is_behandeld = True if behandeld_optie == "Ja" else False
                
                try:
                    supabase.table("aanvragen").update({
                        "status": n_status,
                        "behandeld": is_behandeld, # Hier sturen we nu True of False
                        "volgende_stappen": stappen,
                        "intern_verslag": verslag,
                        "medewerker_toelichting": mail_tekst
                    }).eq("id", sel_id).execute()
                    
                    if mail_tekst:
                        stuur_mail(reg['email'], "Update Registratie DGW", mail_tekst)
                    st.success("✅ Dossier succesvol bijgewerkt.")
                    st.rerun()
                except Exception as e:
                    st.error(f"⚠️ Fout bij opslaan: {e}")

elif menu == "Agenda":
    st.header("📅 Afsprakenoverzicht")
    res = supabase.table("aanvragen").select("*").execute()
    if res.data:
        events = [{"title": f"{r['voornaam']} {r['achternaam']}", "start": r['afspraak_datum'], "color": "#2e7d32"} for r in res.data]
        calendar(events=events, options={"initialView": "dayGridMonth"})

elif menu == "Rapportages":
    st.header("📊 Rapportages")
    res = supabase.table("aanvragen").select("*").execute()
    if res.data:
        # Overzicht zoals getoond in image_98d35a.png
        st.dataframe(pd.DataFrame(res.data)[['id', 'voornaam', 'achternaam', 'status', 'afspraak_datum']])

elif menu == "Systeembeheer":
    st.header("⚙️ Systeembeheer")
    with st.expander("➕ Nieuwe Medewerker"):
        with st.form("new_user"):
            u = st.text_input("Gebruikersnaam")
            p = st.text_input("Wachtwoord", type="password")
            r = st.selectbox("Rol", ["Medewerker", "Admin"])
            if st.form_submit_button("Account Aanmaken"):
                supabase.table("medewerkers").insert({"gebruikersnaam": u, "wachtwoord": p, "rol": r}).execute()
                st.success("Gebruiker toegevoegd.")

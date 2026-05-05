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

# --- 1. CONFIGURATIE ---
st.set_page_config(page_title="Registratie Dienst Grondzaken Wanica Centrum", layout="wide")

# Verbinding met Supabase
supabase = create_client(st.secrets["SUPABASE_URL"], st.secrets["SUPABASE_KEY"])

# Sidebar met Logo en Titel
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

# --- 2. AUTHENTICATIE STATUS ---
if 'logged_in' not in st.session_state:
    st.session_state.update({'logged_in': False, 'role': None, 'user': None})

# Login sectie in Sidebar
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
            st.warning("Database verbinding maken...")

# --- 3. MENU NAVIGATIE ---
menu_options = ["📝 Nieuwe Registratie"]
if st.session_state.logged_in:
    menu_options += ["📋 Dossierbeheer", "📅 Agenda", "📊 Rapportages", "⚙️ Systeeminstellingen"]
    if st.sidebar.button("🚪 Uitloggen"):
        st.session_state.logged_in = False
        st.rerun()

menu = st.sidebar.radio("Hoofdmenu", menu_options)

# --- 4. PAGINA LOGICA ---

# --- REGISTRATIE PAGINA (AANGEPASTE TITEL) ---
if menu == "📝 Nieuwe Registratie":
    st.header("Registratie Dienst Grondzaken Wanica centrum") # Aangepast op verzoek
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
        st.info("Voor eventuele afspraak kies een datum en tijd. (afspraak aleen op de maandag en woensdag)")
        
        datum = st.date_input("Kies een datum", min_value=datetime.date.today())
        
        tijd_keuze = None
        if datum.weekday() in [0, 2]: # Maandag en Woensdag
            tijdsblokken = [f"{h:02d}:{m:02d}" for h in range(8, 15) for m in (0, 15, 30, 45) if not (h == 14 and m > 30)]
            res_t = supabase.table("aanvragen").select("afspraak_tijd").eq("afspraak_datum", str(datum)).execute()
            bezet = [r['afspraak_tijd'] for r in res_t.data] if res_t.data else []
            tijd_keuze = st.selectbox("Beschikbare tijdstippen", ["---"] + [t for t in tijdsblokken if t not in bezet])
        else:
            st.warning("Let op: Afspraken zijn uitsluitend mogelijk op maandag en woensdag.")

        if st.form_submit_button("Registratie Indien"):
            if all([vnaam, anaam, email, id_nr, bericht]) and tijd_keuze != "---":
                try:
                    supabase.table("aanvragen").insert({
                        "voornaam": vnaam, "achternaam": anaam, "email": email, "id_nummer": id_nr,
                        "telefoon": tel, "lad_nummer": lad_nr, "afspraak_datum": str(datum),
                        "afspraak_tijd": tijd_keuze, "status": "In behandeling", "bericht": bericht
                    }).execute()
                    st.success("✅ Uw registratie is succesvol verwerkt!")
                except Exception as e:
                    st.error(f"Fout: {e}")
            else:
                st.error("Vul alle verplichte velden in en kies een tijdstip.")

# --- DOSSIERBEHEER (MET NUMMERING VANAF 1) ---
elif menu == "📋 Dossierbeheer":
    st.header("📋 Dossierbeheer")
    res = supabase.table("aanvragen").select("*").order('id', desc=True).execute()
    
    if res.data:
        df = pd.DataFrame(res.data)
        # Voeg een weergave-nummer toe dat bij 1 begint
        df.insert(0, 'Nr.', range(1, len(df) + 1))
        
        st.dataframe(df[['Nr.', 'id', 'voornaam', 'achternaam', 'status', 'afspraak_datum']], 
                     use_container_width=True, hide_index=True)
        st.divider()
        
        sel_id = st.selectbox("Selecteer Dossier ID voor alle details", df['id'].tolist())
        reg = next(item for item in res.data if item['id'] == sel_id)

        st.subheader(f"Details van dossier: {reg['id']}")
        col_x, col_y = st.columns(2)
        with col_x:
            st.write(f"**Naam:** {reg['voornaam']} {reg['achternaam']}")
            st.write(f"**ID-Nummer:** {reg['id_nummer']}")
            st.write(f"**Telefoon:** {reg['telefoon']}")
            st.write(f"**E-mail:** {reg['email']}")
            st.write(f"**LAD Nummer:** {reg.get('lad_nummer') or 'N.v.t.'}")
        with col_y:
            st.write(f"**Afspraakdatum:** {reg['afspraak_datum']}")
            st.write(f"**Afspraaktijd:** {reg['afspraak_tijd']}")
            st.write(f"**Status:** {reg['status']}")
            st.info(f"**Bericht:** {reg['bericht']}")

        with st.form("update_dossier_form"):
            nieuwe_status = st.selectbox("Status aanpassen", ["Bevestigd", "In behandeling", "Afgehandeld", "Geannuleerd"], 
                                       index=["Bevestigd", "In behandeling", "Afgehandeld", "Geannuleerd"].index(reg['status']))
            intern_verslag = st.text_area("Intern Verslag", value=str(reg.get('intern_verslag') or ""))
            if st.form_submit_button("Wijzigingen Opslaan"):
                supabase.table("aanvragen").update({"status": nieuwe_status, "intern_verslag": intern_verslag}).eq("id", sel_id).execute()
                st.success("Dossier bijgewerkt!")
                st.rerun()
    else:
        st.info("Er zijn geen dossiers gevonden.")

# --- OVERIGE PAGINA'S ---
elif menu == "📅 Agenda":
    st.header("📅 Agenda")
    res = supabase.table("aanvragen").select("*").execute()
    if res.data:
        events = [{"title": f"{r['voornaam']} {r['achternaam']}", "start": r['afspraak_datum']} for r in res.data]
        calendar(events=events)

elif menu == "📊 Rapportages":
    st.header("📊 Rapportages")
    res = supabase.table("aanvragen").select("*").execute()
    if res.data:
        df = pd.DataFrame(res.data)
        st.dataframe(df)
        st.download_button("Download CSV", df.to_csv(index=False).encode('utf-8'), "rapport.csv", "text/csv")

elif menu == "⚙️ Systeeminstellingen":
    st.header("⚙️ Systeeminstellingen")
    res_m = supabase.table("medewerkers").select("*").execute()
    if res_m.data:
        for m in res_m.data:
            st.write(f"👤 {m['gebruikersnaam']} ({m['rol']})")
    
    with st.form("add_user"):
        u = st.text_input("Nieuwe Gebruiker")
        p = st.text_input("Wachtwoord", type="password")
        r = st.selectbox("Rol", ["Medewerker", "Admin"])
        if st.form_submit_button("Toevoegen"):
            supabase.table("medewerkers").insert({"gebruikersnaam": u, "wachtwoord": p, "rol": r}).execute()
            st.success("Toegevoegd!")
            st.rerun()

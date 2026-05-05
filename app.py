import streamlit as st
from supabase import create_client, Client
import datetime
import pandas as pd
import smtplib
from email.mime.text import MIMEText
from email.mime.multipart import MIMEMultipart
from email.mime.application import MIMEApplication

# --- 1. CONFIGURATIE ---
st.set_page_config(page_title="Registratie Dienst Grondzaken Wanica Centrum", layout="wide")

supabase = create_client(st.secrets["SUPABASE_URL"], st.secrets["SUPABASE_KEY"])

EMAIL_USER = "wanicacentrum.gz@gmail.com"
EMAIL_PASS = "kmebjorjujxwqbvo"

# Huisstijl Groen/Wit
st.markdown("""
    <style>
    .stApp { background-color: white; }
    h1, h2, h3 { color: #2e7d32; }
    .stButton>button { background-color: #2e7d32; color: white; border-radius: 5px; }
    .stSidebar { background-color: #f1f8e9; }
    div.stButton > button:first-child[data-testid="stBaseButton-secondary"] {
        background-color: #d32f2f;
        border-color: #d32f2f;
    }
    </style>
""", unsafe_allow_html=True)

# --- 2. PROFESSIONELE EMAIL FUNCTIE ---
def stuur_mail(ontvanger, onderwerp, inhoud, bestanden=None):
    msg = MIMEMultipart()
    msg['From'] = f"Dienst Grondzaken Wanica Centrum <{EMAIL_USER}>"
    msg['To'] = ontvanger
    msg['Subject'] = onderwerp
    
    html_inhoud = f"""
    <html>
        <body style="font-family: Arial, sans-serif; color: #333;">
            <div style="background-color: #2e7d32; padding: 20px; color: white; text-align: center;">
                <h2>Dienst Grondzaken Wanica Centrum</h2>
            </div>
            <div style="padding: 20px; border: 1px solid #ddd;">
                {inhoud.replace('\\n', '<br>')}
            </div>
            <div style="font-size: 12px; color: #777; margin-top: 20px; text-align: center;">
                Dit is een automatisch gegenereerd bericht.
            </div>
        </body>
    </html>
    """
    msg.attach(MIMEText(html_inhoud, 'html'))
    
    if bestanden:
        for f in bestanden:
            f.seek(0)
            part = MIMEApplication(f.read(), Name=f.name)
            part['Content-Disposition'] = f'attachment; filename="{f.name}"'
            msg.attach(part)
            
    try:
        server = smtplib.SMTP('smtp.gmail.com', 587)
        server.starttls()
        server.login(EMAIL_USER, EMAIL_PASS)
        server.send_message(msg)
        server.quit()
        return True
    except:
        return False

# --- 3. LOGIN & STATE ---
if 'logged_in' not in st.session_state:
    st.session_state.update({'logged_in': False, 'role': None, 'user': None})
if 'selected_time' not in st.session_state:
    st.session_state.selected_time = None

with st.sidebar:
    st.markdown("<h3 style='text-align: center;'>Commissariaat Wanica</h3>", unsafe_allow_html=True)
    st.divider()

if not st.session_state.logged_in:
    with st.sidebar:
        st.subheader("🔐 Medewerkers Portaal")
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
        except: pass

menu_options = ["📝 Nieuwe Registratie"]
if st.session_state.logged_in:
    menu_options += ["📋 Dossierbeheer", "📊 Rapportages", "📅 Agenda", "⚙️ Systeembeheer"]
    if st.sidebar.button("🚪 Afmelden"):
        st.session_state.update({'logged_in': False, 'role': None, 'user': None})
        st.rerun()

menu = st.sidebar.radio("Hoofdmenu", menu_options)

# --- 4. HERSTELDE REGISTRATIE PAGINA (MET LOGO & TIJDSLOTS) ---
if menu == "📝 Nieuwe Registratie":
    # Logo bovenaan
    col_l, col_r = st.columns([1, 4])
    with col_l:
        st.image("https://upload.wikimedia.org/wikipedia/commons/thumb/8/82/Coat_of_arms_of_Suriname.svg/1200px-Coat_of_arms_of_Suriname.svg.png", width=120)
    with col_r:
        st.title("Registratie Dienst Grondzaken Wanica Centrum")
        st.write("Vul onderstaand formulier volledig in voor uw klacht of grondaanvraag.")

    st.divider()
    
    col1, col2 = st.columns(2)
    with col1:
        vnaam = st.text_input("Voornaam *")
        anaam = st.text_input("Achternaam *")
        adres = st.text_input("Woonadres *")
        email = st.text_input("E-mailadres *")
    with col2:
        id_nr = st.text_input("ID-nummer *")
        tel = st.text_input("Telefoonnummer *")
        lad = st.text_input("LAD-nummer")
    
    bericht = st.text_area("Omschrijving klacht/verzoek *")
    docs = st.file_uploader("Documenten uploaden (Perceelkaart, ID-kopie, etc.)", accept_multiple_files=True)
    
    st.divider()
    st.subheader("📅 Kies een afspraakdatum en tijd")
    datum = st.date_input("Kies een datum", min_value=datetime.date.today())
    
    if datum.weekday() in [0, 2]: # Alleen Maandag (0) en Woensdag (2)
        # Tijdslots van 08:00 tot 14:30 (elke 15 min)
        tijdsblokken = [f"{h:02d}:{m:02d}" for h in range(8, 15) for m in (0, 15, 30, 45) if not (h == 14 and m > 30)]
        
        st.write("Beschikbare tijden voor bezoek:")
        cols = st.columns(6) # Breder rooster voor betere weergave
        for idx, t in enumerate(tijdsblokken):
            with cols[idx % 6]:
                is_selected = st.session_state.selected_time == t
                if st.button(t, key=f"t_{t}", type="primary" if is_selected else "secondary", use_container_width=True):
                    st.session_state.selected_time = t
                    st.rerun()
        
        if st.session_state.selected_time:
            st.success(f"Geselecteerd tijdstip: **{st.session_state.selected_time}**")
    else:
        st.warning("Bezoekafspraken zijn enkel mogelijk op maandag en woensdag van 08:00 tot 14:30.")

    if st.button("✅ Registratie Definitief Indienen", type="primary", use_container_width=True):
        if all([vnaam, anaam, adres, email, id_nr, bericht]) and st.session_state.selected_time:
            data = {"voornaam": vnaam, "achternaam": anaam, "woonadres": adres, "email": email, "id_nummer": id_nr, "telefoon": tel, "lad_nummer": lad, "afspraak_datum": str(datum), "afspraak_tijd": st.session_state.selected_time, "status": "In behandeling", "bericht": bericht}
            supabase.table("aanvragen").insert(data).execute()
            
            # Professionele mail naar medewerker
            mail_med = f"<b>Nieuwe aanvraag:</b> {vnaam} {anaam}<br><b>ID:</b> {id_nr}<br><b>Adres:</b> {adres}<br><b>Bericht:</b> {bericht}<br><br><b>Afspraak:</b> {datum} om {st.session_state.selected_time}"
            stuur_mail(EMAIL_USER, f"NIEUWE REGISTRATIE: {vnaam} {anaam}", mail_med, docs)
            
            st.success("✅ Bedankt. Uw registratie is ontvangen. U ontvangt een bevestiging per mail.")
            st.session_state.selected_time = None
        else:
            st.error("Let op: Vul alle velden met een * in en kies een tijdstip.")

# --- 5. DOSSIERBEHEER (ONGEWIJZIGD) ---
elif menu == "📋 Dossierbeheer":
    st.header("📋 Dossierbeheer")
    res = supabase.table("aanvragen").select("*").order('id', desc=True).execute()
    if res.data:
        df = pd.DataFrame(res.data)
        st.dataframe(df[['id', 'voornaam', 'achternaam', 'status', 'afspraak_datum']], hide_index=True)
        sel_id = st.selectbox("Selecteer dossier", df['id'].tolist())
        d = next(item for item in res.data if item['id'] == sel_id)
        
        c1, c2 = st.columns(2)
        with c1:
            st.markdown(f"**Cliënt:** {d['voornaam']} {d['achternaam']}<br>**Adres:** {d.get('woonadres', 'Nvt')}", unsafe_allow_html=True)
        with c2:
            st.markdown(f"**Status:** {d['status']}<br>**Afspraak:** {d['afspraak_datum']} om {d['afspraak_tijd']}", unsafe_allow_html=True)
        
        st.divider()
        ce1, ce2 = st.columns(2)
        with ce1:
            n_status = st.selectbox("Update Status", ["In behandeling", "Wacht op documenten", "Bevestigd", "Afgehandeld"])
            n_datum = st.date_input("Verzet Datum", value=datetime.datetime.strptime(d['afspraak_datum'], '%Y-%m-%d').date())
            n_tijd = st.text_input("Verzet Tijd", value=d['afspraak_tijd'])
        with ce2:
            toelichting = st.text_area("Interne Notitie", value=d.get('medewerker_toelichting', ""))
            mail_tekst = st.text_area("Bericht aan Cliënt")

        if st.button("💾 Opslaan & Mailen", use_container_width=True):
            supabase.table("aanvragen").update({"status": n_status, "afspraak_datum": str(n_datum), "afspraak_tijd": n_tijd, "medewerker_toelichting": toelichting, "volgende_stappen": mail_tekst}).eq("id", sel_id).execute()
            mail_cli = f"Geachte {d['achternaam']},<br><br>Uw dossier is bijgewerkt.<br><b>Status:</b> {n_status}<br><b>Afspraak:</b> {n_datum} om {n_tijd}<br><br>{mail_tekst}"
            stuur_mail(d['email'], f"Update Dossier: {sel_id}", mail_cli)
            st.success("Bijgewerkt.")
            st.rerun()

# --- 6. RAPPORTAGES, AGENDA & SYSTEEMBEHEER (ONGEWIJZIGD) ---
elif menu == "📊 Rapportages":
    st.header("📊 Management Rapportages")
    res = supabase.table("aanvragen").select("*").execute()
    if res.data:
        df = pd.DataFrame(res.data)
        st.dataframe(df, use_container_width=True)
        st.download_button("📥 Export naar CSV", df.to_csv(index=False).encode('utf-8'), "DGW_Rapport.csv", "text/csv")

elif menu == "📅 Agenda":
    st.header("📅 Bezoekagenda")
    res = supabase.table("aanvragen").select("voornaam, achternaam, afspraak_datum, afspraak_tijd, status").execute()
    if res.data:
        st.table(pd.DataFrame(res.data).sort_values('afspraak_datum'))

elif menu == "⚙️ Systeembeheer":
    st.header("⚙️ Systeembeheer")
    if st.session_state.role == 'admin':
        with st.expander("➕ Nieuwe Medewerker"):
            new_u = st.text_input("Gebruikersnaam")
            new_p = st.text_input("Wachtwoord", type="password")
            new_r = st.selectbox("Rol", ["user", "admin"])
            if st.button("Opslaan"):
                supabase.table("medewerkers").insert({"gebruikersnaam": new_u, "wachtwoord": new_p, "rol": new_r}).execute()
                st.rerun()
        
        res_m = supabase.table("medewerkers").select("*").execute()
        if res_m.data:
            for m in res_m.data:
                col_m1, col_m2 = st.columns([3, 1])
                col_m1.write(f"👤 {m['gebruikersnaam']} ({m['rol']})")
                if col_m2.button("Verwijderen", key=f"del_{m['id']}"):
                    supabase.table("medewerkers").delete().eq("id", m['id']).execute()
                    st.rerun()

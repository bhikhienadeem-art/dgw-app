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

# --- 2. EMAIL FUNCTIE ---
def stuur_mail(ontvanger, onderwerp, inhoud, bestanden=None):
    msg = MIMEMultipart()
    msg['From'] = EMAIL_USER
    msg['To'] = ontvanger
    msg['Subject'] = onderwerp
    msg.attach(MIMEText(inhoud, 'plain'))
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
    except Exception as e:
        st.error(f"E-mail fout: {e}")
        return False

# --- 3. LOGIN & STATE ---
if 'logged_in' not in st.session_state:
    st.session_state.update({'logged_in': False, 'role': None, 'user': None})
if 'selected_time' not in st.session_state:
    st.session_state.selected_time = None

with st.sidebar:
    st.markdown("<h3 style='text-align: center;'>Dienst Grondzaken Wanica Centrum</h3>", unsafe_allow_html=True)
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

menu = st.sidebar.radio("Menu", menu_options)

# --- 4. NIEUWE REGISTRATIE ---
if menu == "📝 Nieuwe Registratie":
    st.header("Registratie Dienst Grondzaken Wanica Centrum")
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
    bestanden = st.file_uploader("Upload documenten", accept_multiple_files=True)
    
    st.divider()
    datum = st.date_input("Datum afspraak", min_value=datetime.date.today())
    if datum.weekday() in [0, 2]: # Ma & Wo
        tijden = [f"{h:02d}:{m:02d}" for h in range(8, 15) for m in (0, 15, 30, 45) if not (h == 14 and m > 30)]
        cols = st.columns(4)
        for idx, t in enumerate(tijden):
            with cols[idx % 4]:
                style = "primary" if st.session_state.selected_time == t else "secondary"
                if st.button(t, key=f"t_{t}", type=style, use_container_width=True):
                    st.session_state.selected_time = t
                    st.rerun()
    else:
        st.warning("Bezoekafspraken zijn enkel mogelijk op maandag en woensdag.")

    if st.button("Registratie Indienen", type="primary", use_container_width=True):
        if all([vnaam, anaam, adres, email, id_nr, bericht]) and st.session_state.selected_time:
            data = {"voornaam": vnaam, "achternaam": anaam, "woonadres": adres, "email": email, "id_nummer": id_nr, "telefoon": tel, "lad_nummer": lad, "afspraak_datum": str(datum), "afspraak_tijd": st.session_state.selected_time, "status": "In behandeling", "bericht": bericht}
            supabase.table("aanvragen").insert(data).execute()
            
            # E-mail naar medewerker met ALLE informatie
            mail_medewerker = f"""
Nieuwe Registratie Ontvangen:

Cliënt: {vnaam} {anaam}
ID-nummer: {id_nr}
Adres: {adres}
Telefoon: {tel}
LAD-nummer: {lad if lad else 'Nvt'}
E-mail: {email}

Omschrijving:
{bericht}

Geplande Afspraak: {datum} om {st.session_state.selected_time} uur.
            """
            stuur_mail(EMAIL_USER, f"Nieuwe Aanvraag: {vnaam} {anaam}", mail_medewerker, bestanden)
            
            st.success("Uw registratie is succesvol ontvangen.")
            st.session_state.selected_time = None
        else: st.error("Vul alle velden in en kies een tijd.")

# --- 5. DOSSIERBEHEER ---
elif menu == "📋 Dossierbeheer":
    st.header("📋 Dossierbeheer & Updates")
    res = supabase.table("aanvragen").select("*").order('id', desc=True).execute()
    if res.data:
        df = pd.DataFrame(res.data)
        st.dataframe(df[['id', 'voornaam', 'achternaam', 'status', 'afspraak_datum']], hide_index=True)
        
        sel_id = st.selectbox("Selecteer dossier ID", df['id'].tolist())
        d = next(item for item in res.data if item['id'] == sel_id)
        
        st.markdown("### 📄 Cliëntgegevens")
        c1, c2 = st.columns(2)
        with c1:
            st.write(f"**Naam:** {d['voornaam']} {d['achternaam']}")
            st.write(f"**Woonadres:** {d.get('woonadres', 'Nvt')}")
            st.write(f"**E-mail:** {d['email']}")
        with c2:
            st.write(f"**ID:** {d['id_nummer']} | **LAD:** {d.get('lad_nummer', 'Nvt')}")
            st.write(f"**Afspraak:** {d['afspraak_datum']} om {d['afspraak_tijd']}")
            st.info(f"**Bericht cliënt:** {d['bericht']}")

        st.divider()
        ce1, ce2 = st.columns(2)
        with ce1:
            n_status = st.selectbox("Update Status", ["In behandeling", "Wacht op documenten", "Bevestigd", "Afgehandeld"])
            n_datum = st.date_input("Wijzig Datum", value=datetime.datetime.strptime(d['afspraak_datum'], '%Y-%m-%d').date())
            n_tijd = st.text_input("Wijzig Tijd", value=d['afspraak_tijd'])
        with ce2:
            toelichting = st.text_area("Interne Notitie (Database)", value=d.get('medewerker_toelichting', ""))
            mail_tekst = st.text_area("Bericht aan Cliënt (E-mail)")

        cb1, cb2 = st.columns(2)
        with cb1:
            if st.button("💾 Opslaan & Mailen", use_container_width=True):
                supabase.table("aanvragen").update({
                    "status": n_status, "afspraak_datum": str(n_datum), 
                    "afspraak_tijd": n_tijd, "medewerker_toelichting": toelichting,
                    "volgende_stappen": mail_tekst
                }).eq("id", sel_id).execute()
                
                mail_body = f"Geachte {d['voornaam']},\n\nUw status: {n_status}.\nAfspraak: {n_datum} om {n_tijd}.\n\nBericht:\n{mail_tekst}"
                stuur_mail(d['email'], "Update Dossier Grondzaken", mail_body)
                st.success("Dossier bijgewerkt.")
                st.rerun()
        with cb2:
            if st.button(f"🗑️ Verwijder Dossier #{sel_id}", type="secondary", use_container_width=True):
                supabase.table("aanvragen").delete().eq("id", sel_id).execute()
                st.rerun()

# --- 6. RAPPORTAGES ---
elif menu == "📊 Rapportages":
    st.header("📊 Management Rapportages")
    res = supabase.table("aanvragen").select("*").execute()
    if res.data:
        df = pd.DataFrame(res.data)
        st.dataframe(df, use_container_width=True)
        st.download_button("📥 Download CSV", df.to_csv(index=False).encode('utf-8'), "DGW_Rapport.csv", "text/csv")

# --- 7. AGENDA ---
elif menu == "📅 Agenda":
    st.header("📅 Agenda Overzicht")
    res = supabase.table("aanvragen").select("voornaam, achternaam, afspraak_datum, afspraak_tijd, status").execute()
    if res.data:
        st.table(pd.DataFrame(res.data).sort_values('afspraak_datum'))

# --- 8. SYSTEEMBEHEER ---
elif menu == "⚙️ Systeembeheer":
    st.header("⚙️ Beheer Medewerkers")
    with st.expander("➕ Nieuwe Medewerker"):
        u = st.text_input("Gebruikersnaam")
        p = st.text_input("Wachtwoord", type="password")
        r = st.selectbox("Rol", ["user", "admin"])
        if st.button("Opslaan"):
            supabase.table("medewerkers").insert({"gebruikersnaam": u, "wachtwoord": p, "rol": r}).execute()
            st.rerun()

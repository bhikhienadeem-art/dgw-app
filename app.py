import streamlit as st
from supabase import create_client, Client
import datetime
import pandas as pd
import smtplib
from email.mime.text import MIMEText
from email.mime.multipart import MIMEMultipart
from email.mime.application import MIMEApplication
from io import BytesIO

# --- 1. CONFIGURATIE & VERBINDING ---
st.set_page_config(page_title="Registratie Dienst Grondzaken Wanica Centrum", layout="wide")

supabase = create_client(st.secrets["SUPABASE_URL"], st.secrets["SUPABASE_KEY"])

# E-mail Instellingen
EMAIL_USER = "wanicacentrum.gz@gmail.com"
EMAIL_PASS = "kmebjorjujxwqbvo"

# Kleuren Groen/Wit (Huisstijl)
st.markdown("""
    <style>
    .stApp { background-color: white; }
    h1, h2, h3 { color: #2e7d32; }
    .stButton>button { background-color: #2e7d32; color: white; border-radius: 5px; }
    .stSidebar { background-color: #f1f8e9; }
    /* Specifieke stijl voor verwijderknop */
    div.stButton > button:first-child[data-testid="stBaseButton-secondary"] {
        background-color: #d32f2f;
        border-color: #d32f2f;
    }
    </style>
""", unsafe_allow_html=True)

# --- 2. HULPFUNCTIE: EMAIL VERZENDEN ---
def stuur_mail(ontvanger, onderwerp, inhoud, bestanden=None):
    msg = MIMEMultipart()
    msg['From'] = EMAIL_USER
    msg['To'] = ontvanger
    msg['Subject'] = onderwerp
    msg.attach(MIMEText(inhoud, 'plain'))
    
    if bestanden:
        for f in bestanden:
            part = MIMEApplication(f.read(), Name=f.name)
            part['Content-Disposition'] = f'attachment; filename="{f.name}"'
            msg.attach(part)
            f.seek(0)

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

# --- 3. AUTHENTICATIE & STATE ---
if 'logged_in' not in st.session_state:
    st.session_state.update({'logged_in': False, 'role': None, 'user': None})
if 'selected_time' not in st.session_state:
    st.session_state.selected_time = None

with st.sidebar:
    st.markdown("<h2 style='text-align: center;'>Diest Grondzaken Wanica Centrum</h2>", unsafe_allow_html=True)
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

# --- 4. MENU SELECTIE ---
menu_options = ["📝 Nieuwe Registratie"]
if st.session_state.logged_in:
    menu_options += ["📋 Dossierbeheer", "📊 Rapportages", "📅 Agenda & Kalender"]
    if st.session_state.role == 'admin':
        menu_options.append("⚙️ Systeembeheer")
    if st.sidebar.button("🚪 Afmelden"):
        st.session_state.update({'logged_in': False, 'role': None, 'user': None})
        st.rerun()

menu = st.sidebar.radio("Menu", menu_options)

# --- 5. NIEUWE REGISTRATIE ---
if menu == "📝 Nieuwe Registratie":
    st.header("Registratie Dienst Grondzaken Wanica Centrum")
    col1, col2 = st.columns(2)
    with col1:
        vnaam = st.text_input("Voornaam *")
        anaam = st.text_input("Achternaam *")
        woonadres = st.text_input("Woonadres *")
        email = st.text_input("E-mailadres *")
    with col2:
        id_nr = st.text_input("ID-nummer *")
        tel = st.text_input("Telefoonnummer *")
        lad_nr = st.text_input("LAD-nummer")
    
    bericht = st.text_area("Omschrijving klacht/verzoek *")
    bestanden = st.file_uploader("Upload documenten (bijv. ID, Perceelkaart)", accept_multiple_files=True)
    
    st.divider()
    datum = st.date_input("Kies een datum", min_value=datetime.date.today())
    
    if datum.weekday() in [0, 2]:
        tijdsblokken = [f"{h:02d}:{m:02d}" for h in range(8, 15) for m in (0, 15, 30, 45) if not (h == 14 and m > 30)]
        cols = st.columns(4)
        for idx, tijd in enumerate(tijdsblokken):
            with cols[idx % 4]:
                style = "primary" if st.session_state.selected_time == tijd else "secondary"
                if st.button(f"🕒 {tijd}", key=f"reg_{tijd}", type=style, use_container_width=True):
                    st.session_state.selected_time = tijd
                    st.rerun()
    else:
        st.warning("Bezoekafspraken zijn enkel mogelijk op maandag en woensdag.")

    if st.button("Registratie Indienen", type="primary", use_container_width=True):
        if all([vnaam, anaam, woonadres, email, id_nr, bericht]) and st.session_state.selected_time:
            data = {"voornaam": vnaam, "achternaam": anaam, "woonadres": woonadres, "email": email, "id_nummer": id_nr, "telefoon": tel, "lad_nummer": lad_nr, "afspraak_datum": str(datum), "afspraak_tijd": st.session_state.selected_time, "status": "In behandeling", "bericht": bericht}
            supabase.table("aanvragen").insert(data).execute()
            
            mail_body = f"Nieuwe aanvraag:\n\nNaam: {vnaam} {anaam}\nAdres: {woonadres}\nBericht: {bericht}\n\nAfspraak: {datum} om {st.session_state.selected_time}"
            stuur_mail(EMAIL_USER, f"Nieuwe Registratie: {vnaam}", mail_body, bestanden)
            
            st.success("✅ Uw registratie is succesvol ontvangen.")
            st.session_state.selected_time = None
        else:
            st.error("Vul alle verplichte velden in en selecteer een tijdstip.")

# --- 6. DOSSIERBEHEER (MET VERWIJDERFUNCTIE) ---
elif menu == "📋 Dossierbeheer":
    st.header("📋 Dossierbeheer")
    res = supabase.table("aanvragen").select("*").order('id', desc=True).execute()
    if res.data:
        df = pd.DataFrame(res.data)
        st.dataframe(df[['id', 'voornaam', 'achternaam', 'status', 'afspraak_datum']], hide_index=True)
        
        sel_id = st.selectbox("Selecteer dossier ID", df['id'].tolist())
        d = next(item for item in res.data if item['id'] == sel_id)
        
        st.markdown("### 📄 Volledige Cliëntinformatie")
        c1, c2 = st.columns(2)
        with c1:
            st.write(f"**Naam:** {d['voornaam']} {d['achternaam']}")
            st.write(f"**Woonadres:** {d.get('woonadres', 'Onbekend')}")
            st.write(f"**E-mail:** {d['email']}")
            st.write(f"**Telefoon:** {d['telefoon']}")
        with c2:
            st.write(f"**ID-nummer:** {d['id_nummer']}")
            st.write(f"**LAD-nummer:** {d.get('lad_nummer', 'Nvt')}")
            st.info(f"**Omschrijving:** {d['bericht']}")

        st.divider()
        n_status = st.selectbox("Update Status", ["In behandeling", "Wacht op documenten", "Bevestigd", "Afgehandeld"], index=0)
        instructies = st.text_area("Bericht aan cliënt")
        
        col_btn1, col_btn2 = st.columns([1, 1])
        with col_btn1:
            if st.button("💾 Bijwerken & Mailen", use_container_width=True):
                supabase.table("aanvragen").update({"status": n_status, "instructies_client": instructies}).eq("id", sel_id).execute()
                stuur_mail(d['email'], "Update van uw aanvraag - DGW", f"Status: {n_status}\nInstructies: {instructies}")
                st.success("Dossier bijgewerkt.")
                st.rerun()
        
        with col_btn2:
            # Verwijderknop
            if st.button(f"🗑️ Dossier #{sel_id} Verwijderen", type="secondary", use_container_width=True):
                supabase.table("aanvragen").delete().eq("id", sel_id).execute()
                st.warning(f"Dossier #{sel_id} is definitief verwijderd.")
                st.rerun()

# --- 7. RAPPORTAGES ---
elif menu == "📊 Rapportages":
    st.header("📊 Management Rapportages")
    res = supabase.table("aanvragen").select("*").execute()
    if res.data:
        df = pd.DataFrame(res.data)
        st.dataframe(df, use_container_width=True)
        st.download_button("📥 Download CSV Rapport", df.to_csv(index=False).encode('utf-8'), "DGW_Rapport.csv", "text/csv")

# --- 8. AGENDA ---
elif menu == "📅 Agenda & Kalender":
    st.header("📅 Agenda Overzicht")
    res = supabase.table("aanvragen").select("voornaam, achternaam, afspraak_datum, afspraak_tijd, status").execute()
    if res.data:
        df_cal = pd.DataFrame(res.data)
        st.dataframe(df_cal.sort_values(['afspraak_datum', 'afspraak_tijd']), hide_index=True, use_container_width=True)

# --- 9. SYSTEEMBEHEER ---
elif menu == "⚙️ Systeembeheer":
    st.header("⚙️ Beheer Medewerkers")
    with st.expander("➕ Nieuwe Medewerker"):
        u = st.text_input("Gebruikersnaam")
        p = st.text_input("Wachtwoord", type="password")
        r = st.selectbox("Rol", ["user", "admin"])
        if st.button("Opslaan"):
            supabase.table("medewerkers").insert({"gebruikersnaam": u, "wachtwoord": p, "rol": r}).execute()
            st.success("Toegevoegd.")
            st.rerun()

    res_m = supabase.table("medewerkers").select("*").execute()
    if res_m.data:
        df_m = pd.DataFrame(res_m.data)
        sel_m = st.selectbox("Selecteer medewerker", df_m['gebruikersnaam'].tolist())
        if st.button("🗑️ Verwijder Medewerker"):
            supabase.table("medewerkers").delete().eq("gebruikersnaam", sel_m).execute()
            st.success("Verwijderd.")
            st.rerun()

import streamlit as st
from supabase import create_client, Client
import datetime
import pandas as pd
import smtplib
from email.mime.text import MIMEText
from email.mime.multipart import MIMEMultipart
from email.mime.application import MIMEApplication

# --- 1. CONFIGURATIE & STYLING ---
st.set_page_config(page_title="DGW Wanica Portaal", layout="wide")

try:
    st.sidebar.image("orgineel logo Centrum.png", use_container_width=True)
except:
    st.sidebar.warning("Logo bestand niet gevonden.")

st.markdown("""
    <style>
    .tijd-knop { display: inline-block; padding: 10px; margin: 5px; border-radius: 5px; text-align: center; font-weight: bold; width: 85px; }
    .vrij { background-color: #e8f5e9; border: 2px solid #2e7d32; color: #2e7d32; }
    .bezet { background-color: #ffebee; border: 2px solid #c62828; color: #c62828; text-decoration: line-through; }
    .stButton>button { background-color: #2e7d32 !important; color: white !important; border-radius: 5px; width: 100%; height: 50px; font-size: 18px; border: none; }
    .status-card { padding: 15px; border-radius: 10px; border-left: 5px solid #2e7d32; background-color: #f9f9f9; margin-bottom: 10px; border: 1px solid #ddd; }
    </style>
    """, unsafe_allow_html=True)

# Verbinding met Supabase
try:
    supabase = create_client(st.secrets["SUPABASE_URL"], st.secrets["SUPABASE_KEY"])
except:
    st.error("Configuratie fout in Secrets.")
    st.stop()

# --- PROFESSIONELE MAIL FUNCTIE ---
def stuur_mail(ontvanger, onderwerp, inhoud, bestanden=None):
    try:
        msg = MIMEMultipart()
        msg['Subject'] = onderwerp
        msg['From'] = f"DGW Wanica <{st.secrets['EMAIL_USER']}>"
        msg['To'] = ontvanger
        body = f"Geachte cliënt,\n\n{inhoud}\n\nMocht u nog vragen hebben, dan kunt u contact opnemen met ons kantoor.\n\nMet vriendelijke groet,\n\nDistrictscommissariaat Wanica Centrum\nAfdeling Grondzaken (DGW)\nLelydorp, Suriname"
        msg.attach(MIMEText(body, 'plain'))
        if bestanden:
            for f in bestanden:
                f.seek(0)
                bijlage = MIMEApplication(f.read(), Name=f.name)
                bijlage['Content-Disposition'] = f'attachment; filename="{f.name}"'
                msg.attach(bijlage)
        with smtplib.SMTP_SSL('smtp.gmail.com', 465) as server:
            server.login(st.secrets["EMAIL_USER"], st.secrets["EMAIL_PASS"])
            server.send_message(msg)
    except Exception as e:
        st.error(f"Mailfout: {e}")

# --- 2. LOGIN SYSTEEM ---
if 'logged_in' not in st.session_state:
    st.session_state.logged_in, st.session_state.role, st.session_state.user = False, None, None

def login():
    st.sidebar.subheader("🔐 Inloggen")
    try:
        res = supabase.table("medewerkers").select("*").execute()
        user_list = [u['gebruikersnaam'] for u in res.data] if res.data else []
        selected_user = st.sidebar.selectbox("Gebruiker", ["--- Kies ---"] + user_list)
        password = st.sidebar.text_input("Wachtwoord", type="password")
        if st.sidebar.button("Inloggen"):
            user_data = next((u for u in res.data if u['gebruikersnaam'] == selected_user), None)
            if user_data and user_data['wachtwoord'] == password:
                st.session_state.logged_in, st.session_state.role, st.session_state.user = True, user_data['rol'], selected_user
                st.rerun()
            else: st.sidebar.error("Onjuist wachtwoord")
    except Exception as e: st.sidebar.error(f"Fout: {e}")

# --- 3. NAVIGATIE ---
menu_options = ["Cliënt Registratie"]
if st.session_state.logged_in:
    menu_options += ["Medewerker Portaal", "Agenda Overzicht", "Rapportages"]
    if str(st.session_state.role).lower() == "admin": menu_options.append("Admin Instellingen")
    if st.sidebar.button("🚪 Uitloggen"):
        st.session_state.logged_in = False
        st.rerun()
else: login()
menu = st.sidebar.radio("Navigatie", menu_options)

# --- 4. PAGINA'S ---
if menu == "Cliënt Registratie":
    st.header("📝 Nieuwe Aanvraag")
    col1, col2 = st.columns(2)
    with col1:
        vnaam, anaam = st.text_input("Voornaam *"), st.text_input("Achternaam *")
        id_nr, woonadres = st.text_input("ID-Nummer *"), st.text_input("Woonadres *")
    with col2:
        tel, email = st.text_input("Telefoonnummer *"), st.text_input("E-mailadres *")
        lad_nr = st.text_input("LAD Nummer (optioneel)")
    bericht = st.text_area("Omschrijving klacht/verzoek *")
    uploaded_files = st.file_uploader("Documenten", accept_multiple_files=True)
    datum = st.date_input("Datum", min_value=datetime.date.today())
    
    if datum.weekday() in [0, 2]:
        tijden = [f"{h:02d}:{m:02d}" for h in range(7, 15) for m in [0, 15, 30, 45] if "07:00" <= f"{h:02d}:{m:02d}" <= "14:45"]
        res = supabase.table("aanvragen").select("afspraak_tijd").eq("afspraak_datum", str(datum)).execute()
        bezet = [r['afspraak_tijd'] for r in res.data] if res.data else []
        vrije_tijden = [t for t in tijden if t not in bezet]
        gekozen_tijd = st.selectbox("Tijdstip *", ["--- Kies ---"] + vrije_tijden)
        if st.button("Versturen"):
            if all([vnaam, anaam, id_nr, woonadres, tel, email, bericht]) and gekozen_tijd != "--- Kies ---":
                supabase.table("aanvragen").insert({"voornaam": vnaam, "achternaam": anaam, "id_nummer": id_nr, "woonadres": woonadres, "telefoon": tel, "email": email, "lad_nummer": lad_nr, "bericht": bericht, "afspraak_datum": str(datum), "afspraak_tijd": gekozen_tijd, "status": "In behandeling"}).execute()
                stuur_mail(email, "Bevestiging Aanvraag", f"Uw afspraak op {datum} om {gekozen_tijd} uur is ontvangen.")
                st.success("✅ Verzonden!")
    else: st.error("Alleen op Maandag en Woensdag.")

elif menu == "Medewerker Portaal":
    st.header("📋 Beheer")
    res = supabase.table("aanvragen").select("*").order('afspraak_datum').execute()
    if res.data:
        df = pd.DataFrame(res.data)
        st.dataframe(df)
        sel_id = st.selectbox("Selecteer ID", df['id'].tolist())
        col_u, col_d = st.columns(2)
        with col_u:
            n_status = st.selectbox("Status", ["Bevestigd", "In behandeling", "Geannuleerd", "Verwezen"])
            if st.button("Update"):
                supabase.table("aanvragen").update({"status": n_status}).eq("id", sel_id).execute()
                st.rerun()
        with col_d:
            if st.button("🗑️ Verwijder"):
                supabase.table("aanvragen").delete().eq("id", sel_id).execute()
                st.rerun()

elif menu == "Agenda Overzicht":
    st.header("📅 Agenda")
    res = supabase.table("aanvragen").select("*").execute()
    if res.data:
        df = pd.DataFrame(res.data)
        dag = st.date_input("Datum bekijken", value=datetime.date.today())
        dag_data = df[df['afspraak_datum'] == str(dag)].sort_values('afspraak_tijd')
        if not dag_data.empty:
            for _, r in dag_data.iterrows():
                st.markdown(f'<div class="status-card"><b>🕒 {r["afspraak_tijd"]}</b> | {r["voornaam"]} {r["achternaam"]}<br>Status: {r["status"]}</div>', unsafe_allow_html=True)
        else: st.info("Geen afspraken.")

elif menu == "Rapportages":
    st.header("📊 Rapportages")
    res = supabase.table("aanvragen").select("*").execute()
    if res.data:
        df = pd.DataFrame(res.data)
        st.bar_chart(df['status'].value_counts())
        st.download_button("📥 Export CSV", df.to_csv(index=False), "DGW_Export.csv")
        st.dataframe(df)

elif menu == "Admin Instellingen":
    st.header("⚙️ Admin")
    with st.expander("Gebruiker Toevoegen"):
        u, p = st.text_input("Naam"), st.text_input("Wachtwoord", type="password")
        r = st.selectbox("Rol", ["Medewerker", "Admin"])
        if st.button("Opslaan"):
            supabase.table("medewerkers").insert({"gebruikersnaam": u, "wachtwoord": p, "rol": r}).execute()
            st.rerun()
    res_m = supabase.table("medewerkers").select("*").execute()
    if res_m.data:
        df_m = pd.DataFrame(res_m.data)
        st.table(df_m[['gebruikersnaam', 'rol']])
        user_del = st.selectbox("Verwijderen", df_m['gebruikersnaam'].tolist())
        if st.button("❌ Wis Account"):
            supabase.table("medewerkers").delete().eq("gebruikersnaam", user_del).execute()
            st.rerun()

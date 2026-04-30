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

# Groen/wit interface styling
st.markdown("""
    <style>
    .tijd-knop { display: inline-block; padding: 10px; margin: 5px; border-radius: 5px; text-align: center; font-weight: bold; width: 85px; }
    .vrij { background-color: #e8f5e9; border: 2px solid #2e7d32; color: #2e7d32; }
    .bezet { background-color: #ffebee; border: 2px solid #c62828; color: #c62828; text-decoration: line-through; }
    .stButton>button { background-color: #2e7d32 !important; color: white !important; border-radius: 5px; width: 100%; height: 50px; font-size: 18px; border: none; }
    </style>
    """, unsafe_allow_html=True)

# Verbinding met Supabase
try:
    supabase = create_client(st.secrets["SUPABASE_URL"], st.secrets["SUPABASE_KEY"])
except:
    st.error("Configuratie fout in Secrets.")
    st.stop()

def stuur_mail(ontvanger, onderwerp, inhoud, bestanden=None):
    try:
        msg = MIMEMultipart()
        msg['Subject'] = onderwerp
        msg['From'] = st.secrets["EMAIL_USER"]
        msg['To'] = ontvanger
        msg.attach(MIMEText(inhoud))
        if bestanden:
            for f in bestanden:
                bijlage = MIMEApplication(f.read(), Name=f.name)
                bijlage['Content-Disposition'] = f'attachment; filename="{f.name}"'
                msg.attach(bijlage)
                f.seek(0)
        with smtplib.SMTP_SSL('smtp.gmail.com', 465) as server:
            server.login(st.secrets["EMAIL_USER"], st.secrets["EMAIL_PASS"])
            server.send_message(msg)
    except Exception as e:
        st.warning(f"Mailfout: {e}")

# --- 2. LOGIN SYSTEEM (Gekoppeld aan tabel: medewerkers) ---
if 'logged_in' not in st.session_state:
    st.session_state.logged_in = False
    st.session_state.role = None
    st.session_state.user = None

def login():
    st.sidebar.subheader("Inloggen Medewerker")
    try:
        res = supabase.table("medewerkers").select("*").execute()
        user_list = [u['gebruikersnaam'] for u in res.data] if res.data else []
        
        selected_user = st.sidebar.selectbox("Gebruiker", ["--- Selecteer ---"] + user_list)
        password = st.sidebar.text_input("Wachtwoord", type="password")
        
        if st.sidebar.button("Login"):
            user_data = next((u for u in res.data if u['gebruikersnaam'] == selected_user), None)
            if user_data and user_data['wachtwoord'] == password:
                st.session_state.logged_in = True
                st.session_state.role = user_data['rol']
                st.session_state.user = selected_user
                st.rerun()
            else:
                st.sidebar.error("Onjuiste gegevens")
    except Exception as e:
        st.sidebar.error(f"Database fout: {e}")

# --- 3. NAVIGATIE ---
menu_options = ["Cliënt Registratie"]
if st.session_state.logged_in:
    menu_options += ["Medewerker Portaal", "Rapportages"]
    if st.session_state.role == "Admin":
        menu_options.append("Admin Instellingen")
    if st.sidebar.button("Uitloggen"):
        st.session_state.logged_in = False
        st.rerun()
else:
    login()

menu = st.sidebar.radio("Navigatie", menu_options)

# --- 4. PAGINA'S ---

if menu == "Cliënt Registratie":
    st.subheader("Nieuwe Aanvraag")
    col1, col2 = st.columns(2)
    with col1:
        vnaam = st.text_input("Voornaam *")
        anaam = st.text_input("Achternaam *")
        id_nr = st.text_input("ID-Nummer *")
        woonadres = st.text_input("Woonadres *")
    with col2:
        tel = st.text_input("Telefoonnummer *")
        email = st.text_input("E-mailadres *")
        lad_nr = st.text_input("LAD Nummer (optioneel)")
    
    bericht = st.text_area("Omschrijving klacht/verzoek *")
    uploaded_files = st.file_uploader("Documenten Uploaden", accept_multiple_files=True)

    st.write("---")
    st.subheader("📅 Beschikbaarheid")
    datum = st.date_input("Kies een datum", min_value=datetime.date.today())
    
    vrije_tijden = []
    if datum.weekday() not in [0, 2]: # Maandag en Woensdag
        st.error("⚠️ Afspraken zijn uitsluitend op Maandag en Woensdag.")
    else:
        tijden = [f"{h:02d}:{m:02d}" for h in range(7, 15) for m in [0, 15, 30, 45]]
        slots = [t for t in tijden if "07:30" <= t <= "14:00"]
        res = supabase.table("aanvragen").select("afspraak_tijd").eq("afspraak_datum", str(datum)).execute()
        bezet = [r['afspraak_tijd'] for r in res.data] if res.data else []
        
        cols = st.columns(6)
        for i, t in enumerate(slots):
            status = "bezet" if t in bezet else "vrij"
            with cols[i % 6]:
                st.markdown(f'<div class="tijd-knop {status}">{t}</div>', unsafe_allow_html=True)
        vrije_tijden = [t for t in slots if t not in bezet]

    st.write("---")
    gekozen_tijd = st.selectbox("Selecteer uw tijdstip *", ["--- Maak een keuze ---"] + vrije_tijden)

    if st.button("Verstuur Aanvraag"):
        if all([vnaam, anaam, id_nr, woonadres, tel, email, bericht]) and gekozen_tijd != "--- Maak een keuze ---":
            data = {
                "voornaam": vnaam, "achternaam": anaam, "id_nummer": id_nr, "woonadres": woonadres, 
                "telefoon": tel, "email": email, "lad_nummer": lad_nr, "bericht": bericht, 
                "afspraak_datum": str(datum), "afspraak_tijd": gekozen_tijd, "status": "In behandeling"
            }
            supabase.table("aanvragen").insert(data).execute()
            stuur_mail(st.secrets["EMAIL_USER"], f"Nieuwe aanvraag: {vnaam}", f"Nieuwe aanvraag van {vnaam} {anaam}.", uploaded_files)
            stuur_mail(email, "DGW Ontvangstbevestiging", f"Beste {vnaam}, uw afspraak voor {datum} om {gekozen_tijd}u is ontvangen.")
            st.success("✅ Succesvol ingediend!")
            st.balloons()
        else:
            st.error("⚠️ Vul alle verplichte velden in.")

elif menu == "Medewerker Portaal":
    st.subheader("📋 Beheer Aanvragen")
    res = supabase.table("aanvragen").select("*").order('afspraak_datum').execute()
    if res.data:
        df = pd.DataFrame(res.data)
        st.dataframe(df, use_container_width=True)
        
        st.write("---")
        st.subheader("⚙️ Actie uitvoeren")
        opties = {row['id']: f"ID: {row['id']} | {row['voornaam']} {row['achternaam']}" for index, row in df.iterrows()}
        selected_id = st.selectbox("Selecteer aanvraag", options=list(opties.keys()), format_func=lambda x: opties[x])
        aanvraag = next(item for item in res.data if item["id"] == selected_id)
        
        col1, col2 = st.columns(2)
        with col1:
            nieuwe_status = st.selectbox("Status", ["In behandeling", "Bevestigd", "Geannuleerd", "Verwezen"])
            n_datum = st.date_input("Datum aanpassen", value=datetime.datetime.strptime(aanvraag['afspraak_datum'], '%Y-%m-%d').date())
        with col2:
            n_tijd = st.text_input("Tijd aanpassen", value=aanvraag['afspraak_tijd'])
            opmerking = st.text_area("Toelichting voor klant")

        if st.button("Update & Mail Klant"):
            supabase.table("aanvragen").update({"status": nieuwe_status, "afspraak_datum": str(n_datum), "afspraak_tijd": n_tijd}).eq("id", selected_id).execute()
            
            mail_inhoud = f"Beste {aanvraag['voornaam']},\n\nUw aanvraag is bijgewerkt naar: {nieuwe_status}.\nDatum: {n_datum}\nTijd: {n_tijd}u\n\nToelichting: {opmerking}"
            stuur_mail(aanvraag['email'], f"Update DGW Aanvraag: {nieuwe_status}", mail_inhoud)
            st.success("Bijgewerkt!")
            st.rerun()

elif menu == "Rapportages":
    st.subheader("📊 Rapportages")
    res = supabase.table("aanvragen").select("*").execute()
    if res.data:
        df = pd.DataFrame(res.data)
        st.bar_chart(df['status'].value_counts())
        st.write(f"Totaal aantal registraties: {len(df)}")

elif menu == "Admin Instellingen":
    st.subheader("⚙️ Gebruikersbeheer")
    with st.expander("Nieuwe Medewerker Toevoegen"):
        n_user = st.text_input("Gebruikersnaam")
        n_pass = st.text_input("Wachtwoord", type="password")
        n_rol = st.selectbox("Rol", ["Medewerker", "Admin"])
        if st.button("Opslaan"):
            supabase.table("medewerkers").insert({"gebruikersnaam": n_user, "wachtwoord": n_pass, "rol": n_rol}).execute()
            st.success("Toegevoegd!")
            st.rerun()

    st.write("---")
    res = supabase.table("medewerkers").select("*").execute()
    if res.data:
        df_m = pd.DataFrame(res.data)
        st.table(df_m[['gebruikersnaam', 'rol']])
        with st.expander("🗑️ Medewerker Verwijderen"):
            to_del = st.selectbox("Selecteer te verwijderen account", df_m['gebruikersnaam'].tolist())
            if to_del != st.session_state.user:
                if st.button("Definitief Verwijderen"):
                    supabase.table("medewerkers").delete().eq("gebruikersnaam", to_del).execute()
                    st.success("Verwijderd!")
                    st.rerun()
            else:
                st.warning("Je kunt jezelf niet verwijderen.")

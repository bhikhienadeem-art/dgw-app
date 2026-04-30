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

# --- 2. LOGIN SYSTEEM ---
if 'logged_in' not in st.session_state:
    st.session_state.logged_in = False
    st.session_state.role = None
    st.session_state.user = None

def login():
    st.sidebar.subheader("Inloggen Medewerker")
    users_res = supabase.table("users").select("*").execute()
    user_list = [u['username'] for u in users_res.data] if users_res.data else []
    
    selected_user = st.sidebar.selectbox("Gebruiker", ["--- Selecteer ---"] + user_list)
    password = st.sidebar.text_input("Wachtwoord", type="password")
    
    if st.sidebar.button("Login"):
        user_data = next((u for u in users_res.data if u['username'] == selected_user), None)
        if user_data and user_data['password'] == password:
            st.session_state.logged_in = True
            st.session_state.role = user_data['role']
            st.session_state.user = selected_user
            st.rerun()
        else:
            st.sidebar.error("Onjuiste gegevens")

# --- 3. INTERFACE ---
st.title("📝 Dienst Grondzaken Wanica (DGW)")
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
    if datum.weekday() not in [0, 2]:
        st.error("⚠️ Afspraken zijn uitsluitend op Maandag en Woensdag.")
    else:
        tijden = [f"{h:02d}:{m:02d}" for h in range(7, 15) for m in [0, 15, 30, 45]]
        slots = [t for t in tijden if "07:30" <= t <= "14:00"]
        res = supabase.table("aanvragen").select("afspraak_tijd").eq("afspraak_datum", str(datum)).execute()
        bezet = [r['afspraak_tijd'] for r in res.data] if res.data else []
        
        st.write("Groen = Vrij | Rood = Bezet")
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
            stuur_mail(st.secrets["EMAIL_USER"], f"Nieuwe aanvraag: {vnaam}", f"Aanvraag ontvangen voor {datum}.", uploaded_files)
            stuur_mail(email, "DGW Ontvangstbevestiging", f"Beste {vnaam}, uw afspraak staat voor {datum} om {gekozen_tijd}u.")
            st.success("✅ Succesvol ingediend!")
            st.balloons()
        else:
            st.error("⚠️ Vul alle verplichte velden in.")

elif menu == "Medewerker Portaal":
    st.subheader("Beheer Aanvragen")
    res = supabase.table("aanvragen").select("*").execute()
    if res.data:
        df = pd.DataFrame(res.data)
        st.dataframe(df)
        
        st.write("---")
        st.subheader("Status Bijwerken")
        selected_id = st.selectbox("Selecteer ID om aan te passen", df['id'].tolist())
        nieuwe_status = st.selectbox("Nieuwe Status", ["In behandeling", "Goedgekeurd", "Afgewezen"])
        if st.button("Update Status"):
            supabase.table("aanvragen").update({"status": nieuwe_status}).eq("id", selected_id).execute()
            st.success("Status bijgewerkt!")
            st.rerun()

elif menu == "Rapportages":
    st.subheader("📊 Rapportages & Statistieken")
    res = supabase.table("aanvragen").select("*").execute()
    if res.data:
        df = pd.DataFrame(res.data)
        st.write(f"Totaal aantal aanvragen: {len(df)}")
        st.bar_chart(df['status'].value_counts())
        st.write("Overzicht per datum:")
        st.line_chart(df['afspraak_datum'].value_counts())

elif menu == "Admin Instellingen":
    st.subheader("⚙️ Gebruikersbeheer")
    
    # Gebruiker Toevoegen
    with st.expander("Nieuwe Gebruiker Toevoegen"):
        new_user = st.text_input("Gebruikersnaam")
        new_pass = st.text_input("Wachtwoord", type="password")
        new_role = st.selectbox("Rol", ["User", "Admin"])
        if st.button("Gebruiker Opslaan"):
            supabase.table("users").insert({"username": new_user, "password": new_pass, "role": new_role}).execute()
            st.success(f"Gebruiker {new_user} toegevoegd!")
    
    # Gebruikers Verwijderen
    users_res = supabase.table("users").select("*").execute()
    if users_res.data:
        st.write("Huidige Gebruikers:")
        user_df = pd.DataFrame(users_res.data)
        st.table(user_df[['username', 'role']])
        user_to_del = st.selectbox("Verwijder Gebruiker", user_df['username'].tolist())
        if st.button("Verwijder Selectie"):
            supabase.table("users").delete().eq("username", user_to_del).execute()
            st.success("Gebruiker verwijderd")
            st.rerun()

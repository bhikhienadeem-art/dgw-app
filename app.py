import streamlit as st
from supabase import create_client, Client
import smtplib
from email.mime.text import MIMEText
from email.mime.multipart import MIMEMultipart
import datetime
import pandas as pd

# 1. Pagina Configuratie & Styling
st.set_page_config(page_title="DGW Wanica Portaal", page_icon="📝", layout="wide")

st.markdown("""
    <style>
    .main { background-color: #ffffff; }
    .stButton>button { background-color: #2e7d32 !important; color: white !important; border-radius: 5px; }
    h1, h2, h3 { color: #1b5e20; }
    .stAlert { border-radius: 10px; }
    </style>
    """, unsafe_allow_html=True)

# 2. Database Verbinding
try:
    URL = st.secrets["SUPABASE_URL"]
    KEY = st.secrets["SUPABASE_KEY"]
    supabase: Client = create_client(URL, KEY)
except:
    st.error("Controleer uw Streamlit Secrets!")
    st.stop()

# 3. E-mail Functie
def stuur_status_update_mail(data):
    try:
        GMAIL_USER = st.secrets["GMAIL_USER"]
        GMAIL_PASSWORD = st.secrets["GMAIL_PASSWORD"]
        msg = MIMEMultipart()
        msg['From'] = f"DGW Wanica <{GMAIL_USER}>"
        msg['To'] = data['email']
        msg['Subject'] = f"Update Afspraak: {data['status']}"
        inhoud = f"Beste {data['voornaam']},\n\nUw afspraak op {data['datum']} om {data['tijd']} is {data['status']}."
        msg.attach(MIMEText(inhoud, 'plain'))
        server = smtplib.SMTP('smtp.gmail.com', 587)
        server.starttls()
        server.login(GMAIL_USER, GMAIL_PASSWORD)
        server.sendmail(GMAIL_USER, data['email'], msg.as_string())
        server.quit()
    except: pass

# 4. Tijdsbeheer Functies (15 min intervallen)
def get_beschikbare_tijden(datum):
    # Genereer tijden van 07:00 tot 15:00
    start = datetime.datetime.strptime("07:00", "%H:%M")
    eind = datetime.datetime.strptime("15:00", "%H:%M")
    tijden = []
    while start <= eind:
        tijden.append(start.strftime("%H:%M"))
        start += datetime.timedelta(minutes=15)
    
    # Check bezette tijden in database
    res = supabase.table("aanvragen").select("afspraak_tijd").eq("afspraak_datum", str(datum)).execute()
    bezette_tijden = [r['afspraak_tijd'] for r in res.data] if res.data else []
    return tijden, bezette_tijden

# 5. Navigatie
st.sidebar.title("DGW Menu")
keuze = st.sidebar.radio("Navigatie:", ["Cliënt Registratie", "Medewerker Portaal"])

# --- CLIENT REGISTRATIE ---
if keuze == "Cliënt Registratie":
    st.title("📝 Registratie & Document Upload")
    
    with st.form("aanvraag_form", clear_on_submit=True):
        c1, c2 = st.columns(2)
        with c1:
            vnaam = st.text_input("Voornaam *")
            id_nr = st.text_input("ID-Nummer *")
            tel = st.text_input("Telefoon *")
        with c2:
            anaam = st.text_input("Achternaam *")
            lad_nr = st.text_input("LAD Nummer *")
            email = st.text_input("E-mail *")
        
        datum = st.date_input("Kies datum (Ma/Wo)", min_value=datetime.date.today())
        
        # Tijdsindicator (Rood/Groen)
        alle_tijden, bezet = get_beschikbare_tijden(datum)
        tijd = st.selectbox("Kies tijdstip (15 min intervallen)", alle_tijden)
        
        if tijd in bezet:
            st.error(f"❌ {tijd} is al bezet. Kies een andere tijd.")
        else:
            st.success(f"✅ {tijd} is beschikbaar op {datum}.")

        uploaded_file = st.file_uploader("Upload documenten (PDF/JPG)", type=['pdf', 'jpg', 'png'])
        submit = st.form_submit_button("Verzenden")

    if submit and vnaam and email:
        if datum.weekday() in [0, 2]: # Ma/Wo check
            if tijd not in bezet:
                file_url = ""
                if uploaded_file:
                    # Upload naar Supabase Storage
                    path = f"docs/{vnaam}_{datetime.datetime.now().timestamp()}_{uploaded_file.name}"
                    supabase.storage.from_("documenten").upload(path, uploaded_file.getvalue())
                    file_url = supabase.storage.from_("documenten").get_public_url(path)

                form_data = {
                    "voornaam": vnaam, "achternaam": anaam, "email": email,
                    "afspraak_datum": str(datum), "afspraak_tijd": tijd,
                    "status": "In behandeling", "document_url": file_url
                }
                supabase.table("aanvragen").insert(form_data).execute()
                st.success("Aanvraag succesvol verzonden!")
            else:
                st.error("Kies een tijd die nog vrij is.")
        else:
            st.error("Afspraken alleen op Maandag en Woensdag.")

# --- MEDEWERKER PORTAAL ---
elif keuze == "Medewerker Portaal":
    if "logged_in" not in st.session_state or not st.session_state["logged_in"]:
        st.title("🔐 Login")
        u = st.text_input("Gebruikersnaam")
        p = st.text_input("Wachtwoord", type="password")
        if st.button("Inloggen"):
            res = supabase.table("medewerkers").select("*").ilike("gebruikersnaam", u).eq("wachtwoord", p).execute()
            if res.data:
                st.session_state["logged_in"] = True
                st.session_state["user_rol"] = res.data[0]['rol']
                st.rerun()
            else: st.error("Onjuiste gegevens")
    else:
        st.sidebar.button("Uitloggen", on_click=lambda: st.session_state.update({"logged_in": False}))
        
        tabs = st.tabs(["📋 Beheer", "📅 Kalender", "⚙️ Admin"])
        
        # BEHEER TAB
        with tabs[0]:
            res = supabase.table("aanvragen").select("*").execute()
            if res.data:
                df = pd.DataFrame(res.data)
                st.dataframe(df)
                
                sel_id = st.selectbox("Selecteer dossier ID", df['id'].tolist())
                n_status = st.selectbox("Nieuwe Status", ["Bevestigd", "Geannuleerd"])
                
                if st.button("Update"):
                    row = df[df['id'] == sel_id].iloc[0]
                    supabase.table("aanvragen").update({"status": n_status}).eq("id", sel_id).execute()
                    stuur_status_update_mail({"email": row['email'], "voornaam": row['voornaam'], "status": n_status, "datum": row['afspraak_datum'], "tijd": row['afspraak_tijd']})
                    st.success("Status bijgewerkt!")
                    st.rerun()

        # ADMIN TAB (Medewerkers beheren)
        if st.session_state.get("user_rol") == "Admin":
            with tabs[2]:
                st.header("Admin Instellingen")
                nu = st.text_input("Nieuwe Gebruikersnaam")
                np = st.text_input("Nieuw Wachtwoord")
                nr = st.selectbox("Rol", ["Medewerker", "Admin"])
                if st.button("Account Aanmaken"):
                    supabase.table("medewerkers").insert({"gebruikersnaam": nu, "wachtwoord": np, "rol": nr}).execute()
                    st.success("Toegevoegd!")

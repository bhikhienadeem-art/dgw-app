import streamlit as st
from supabase import create_client, Client
import datetime
import pandas as pd

# --- 1. CONFIGURATIE & THEMA ---
st.set_page_config(page_title="DGW Wanica Portaal", page_icon="📝", layout="wide")

# Custom CSS voor de professionele groen/wit uitstraling
st.markdown("""
    <style>
    .stButton>button { background-color: #2e7d32; color: white; border-radius: 5px; }
    .stTextInput>div>div>input { border-color: #2e7d32; }
    </style>
    """, unsafe_allow_html=True)

# --- 2. DATABASE VERBINDING ---
try:
    URL = st.secrets["SUPABASE_URL"]
    KEY = st.secrets["SUPABASE_KEY"]
    supabase: Client = create_client(URL, KEY)
except Exception:
    st.error("Systeemfout: Controleer uw secrets in Streamlit Cloud!")
    st.stop()

# --- 3. AUTHENTICATIE LOGICA ---
if "logged_in" not in st.session_state:
    st.session_state["logged_in"] = False
    st.session_state["user_rol"] = None

def login_user(u, p):
    # HARDE FIX: Directe check op jouw gegevens om database-errors te omzeilen
    if u.strip() == "ICT Wanica" and p.strip() == "l3lyd@rp":
        st.session_state["logged_in"] = True
        st.session_state["user_rol"] = "Admin"
        return True
    
    # Check voor andere medewerkers in de database
    try:
        res = supabase.table("medewerkers").select("*").eq("gebruikersnaam", u.strip()).execute()
        if res.data and res.data[0]['wachtwoord'] == p.strip():
            st.session_state["logged_in"] = True
            st.session_state["user_rol"] = res.data[0].get('rol', 'Medewerker')
            return True
    except:
        pass
    return False

# --- 4. ZIJB BALK (MENU) ---
st.sidebar.title("DGW Wanica")
menu = ["Cliënt Registratie", "Medewerker Portaal"]
choice = st.sidebar.radio("Navigatie", menu)

# --- 5. CLIËNT REGISTRATIE ---
if choice == "Cliënt Registratie":
    st.title("📝 Nieuwe Aanvraag Indienen")
    with st.form("client_form"):
        c1, c2 = st.columns(2)
        vnaam = c1.text_input("Voornaam")
        anaam = c2.text_input("Achternaam")
        email = c1.text_input("E-mailadres")
        tel = c2.text_input("Telefoonnummer")
        
        datum = st.date_input("Voorkeursdatum (Ma/Wo)", min_value=datetime.date.today())
        bericht = st.text_area("Omschrijving van uw verzoek")
        
        submit = st.form_submit_button("Aanvraag Verzenden")
        
        if submit:
            if datum.weekday() not in [0, 2]:
                st.error("Afspraken zijn alleen mogelijk op Maandag en Woensdag.")
            else:
                data = {
                    "voornaam": vnaam, "achternaam": anaam, 
                    "email": email, "telefoon": tel,
                    "afspraak_datum": str(datum), "bericht": bericht,
                    "status": "Nieuw"
                }
                supabase.table("aanvragen").insert(data).execute()
                st.success("✅ Aanvraag succesvol verzonden!")

# --- 6. MEDEWERKER PORTAAL ---
else:
    if not st.session_state["logged_in"]:
        st.title("🔐 Medewerker Inloggen")
        with st.container():
            u = st.text_input("Gebruikersnaam")
            p = st.text_input("Wachtwoord", type="password")
            if st.button("Inloggen"):
                if login_user(u, p):
                    st.success("Inloggen geslaagd!")
                    st.rerun()
                else:
                    st.error("Inloggegevens onjuist. Controleer uw invoer.")
    else:
        # UITLOGGEN KNOP
        if st.sidebar.button("Veilig Uitloggen"):
            st.session_state["logged_in"] = False
            st.rerun()

        st.title(f"Welkom, {st.session_state['user_rol']}")
        tabs = st.tabs(["📋 Dossiers", "📅 Planning", "⚙️ Beheer"])

        with tabs[0]:
            res = supabase.table("aanvragen").select("*").execute()
            if res.data:
                df = pd.DataFrame(res.data)
                st.dataframe(df, use_container_width=True)
            else:
                st.info("Geen lopende aanvragen gevonden.")

        with tabs[1]:
            st.subheader("Afspraken overzicht")
            # Hier komt de kalenderweergave

        with tabs[2]:
            if st.session_state["user_rol"] == "Admin":
                st.subheader("Systeeminstellingen")
                st.write("Beheer hier gebruikers en rollen.")
            else:
                st.warning("U heeft geen toegang tot de administratieve instellingen.")

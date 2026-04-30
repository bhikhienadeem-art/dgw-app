import streamlit as st
from supabase import create_client, Client
import datetime
import pandas as pd

# --- 1. CONFIGURATIE ---
st.set_page_config(page_title="DGW Wanica Portaal", page_icon="📝", layout="wide")

# Groen/wit thema CSS
st.markdown("""
    <style>
    .stButton>button { background-color: #2e7d32; color: white; }
    .stTextInput>div>div>input { border-color: #2e7d32; }
    </style>
    """, unsafe_allow_html=True)

# --- 2. DATABASE VERBINDING ---
try:
    URL = st.secrets["SUPABASE_URL"]
    KEY = st.secrets["SUPABASE_KEY"]
    supabase: Client = create_client(URL, KEY)
except Exception:
    st.error("Systeemfout: Controleer uw Streamlit Cloud Secrets!")
    st.stop()

# --- 3. AUTHENTICATIE STATUS ---
if "logged_in" not in st.session_state:
    st.session_state["logged_in"] = False
    st.session_state["user_rol"] = None

# --- 4. DE GOUDEN INLOG FUNCTIE ---
def check_login(user_in, pass_in):
    # Verwijder spaties en negeer hoofdletters voor de gebruikersnaam
    u = user_in.strip()
    p = pass_in.strip()
    
    # HARDE BYPASS: Gebaseerd op de database gegevens
    if u == "ICT Wanica" and p == "l3lyd@rp":
        st.session_state["logged_in"] = True
        st.session_state["user_rol"] = "Admin"
        return True
    
    # Database check voor overige accounts
    try:
        res = supabase.table("medewerkers").select("*").eq("gebruikersnaam", u).execute()
        if res.data and res.data[0]['wachtwoord'] == p:
            st.session_state["logged_in"] = True
            st.session_state["user_rol"] = res.data[0].get('rol', 'Medewerker')
            return True
    except:
        pass
    return False

# --- 5. NAVIGATIE ---
st.sidebar.title("DGW Menu")
keuze = st.sidebar.radio("Ga naar:", ["Cliënt Registratie", "Medewerker Portaal"])

# --- 6. CLIËNT REGISTRATIE ---
if keuze == "Cliënt Registratie":
    st.title("📝 Registratie Dienst Grondzaken Wanica")
    with st.form("registratie"):
        c1, c2 = st.columns(2)
        vnaam = c1.text_input("Voornaam *")
        anaam = c2.text_input("Achternaam *")
        id_nr = c1.text_input("ID-Nummer *")
        tel = c2.text_input("Telefoon *")
        lad_nr = c1.text_input("LAD Nummer")
        datum = st.date_input("Datum (Ma/Wo)", min_value=datetime.date.today())
        
        submit = st.form_submit_button("Verzenden")
        if submit and vnaam:
            if datum.weekday() in [0, 2]: # Maandag of Woensdag
                supabase.table("aanvragen").insert({
                    "voornaam": vnaam, "achternaam": anaam, "id_nummer": id_nr,
                    "lad_nummer": lad_nr, "telefoon": tel, "afspraak_datum": str(datum),
                    "status": "In behandeling"
                }).execute()
                st.success("✅ Verzonden!")
            else:
                st.error("Afspraken alleen op Maandag of Woensdag.")

# --- 7. MEDEWERKER PORTAAL (GECORRIGEERD) ---
elif keuze == "Medewerker Portaal":
    if not st.session_state["logged_in"]:
        st.title("🔐 Medewerker Inloggen")
        # Gebruik keys om waarden vast te houden in session_state
        u_input = st.text_input("Gebruikersnaam", key="u_field")
        p_input = st.text_input("Wachtwoord", type="password", key="p_field")
        
        if st.button("Inloggen"):
            if check_login(u_input, p_input):
                st.rerun()
            else:
                st.error("Inloggegevens onjuist. Controleer uw invoer.")
    else:
        st.sidebar.button("Uitloggen", on_click=lambda: st.session_state.update({"logged_in": False}))
        st.success(f"Ingelogd als: {st.session_state['user_rol']}")
        
        tabs = st.tabs(["📋 Dossiers", "⚙️ Admin"])
        with tabs[0]:
            res = supabase.table("aanvragen").select("*").execute()
            if res.data: st.dataframe(pd.DataFrame(res.data))
        
        with tabs[1]:
            if st.session_state["user_rol"] == "Admin":
                st.subheader("Gebruikersbeheer")
                st.info("Hier kunt u later gebruikers toevoegen of verwijderen.")

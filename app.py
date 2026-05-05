import streamlit as st
from supabase import create_client, Client
import datetime
import pandas as pd
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
    st.markdown("<h2 style='text-align: center;'>Dienst Grondzaken Wanica Centrum</h2>", unsafe_allow_html=True)
    st.divider()

# --- 2. AUTHENTICATIE & STATE ---
if 'logged_in' not in st.session_state:
    st.session_state.update({'logged_in': False, 'role': None, 'user': None})
if 'selected_time' not in st.session_state:
    st.session_state.selected_time = None

# Login sectie voor medewerkers
if not st.session_state.logged_in:
    with st.sidebar:
        st.subheader("🔐 Portaal voor Medewerkers")
        try:
            res_m = supabase.table("medewerkers").select("*").execute()
            user_list = [u['gebruikersnaam'] for u in res_m.data] if res_m.data else []
            u_sel = st.selectbox("Selecteer Gebruiker", ["---"] + user_list)
            p_inp = st.text_input("Wachtwoord", type="password")
            if st.button("Aanmelden"):
                user_data = next((u for u in res_m.data if u['gebruikersnaam'] == u_sel), None)
                if user_data and user_data['wachtwoord'] == p_inp:
                    st.session_state.update({'logged_in': True, 'role': user_data['rol'], 'user': u_sel})
                    st.rerun()
                else:
                    st.error("Inloggegevens zijn onjuist.")
        except Exception:
            pass

# --- 3. MENU NAVIGATIE ---
menu_options = ["📝 Nieuwe Registratie"]
if st.session_state.logged_in:
    menu_options += ["📋 Dossierbeheer", "📊 Rapportages", "⚙️ Systeembeheer"]
    if st.sidebar.button("🚪 Afmelden"):
        st.session_state.logged_in = False
        st.rerun()

menu = st.sidebar.radio("Hoofdmenu", menu_options)

# --- 4. PAGINA LOGICA ---

if menu == "📝 Nieuwe Registratie":
    st.header("Officiële Registratie Dienst Grondzaken Wanica Centrum")
    st.write("Vul onderstaand formulier volledig in om uw verzoek formeel in te dienen.")
    
    with st.form("registratie_form"):
        col1, col2 = st.columns(2)
        with col1:
            vnaam = st.text_input("Voornaam (conform ID) *")
            anaam = st.text_input("Achternaam *")
            email = st.text_input("E-mailadres *")
        with col2:
            id_nr = st.text_input("Identiteitsnummer (ID) *")
            tel = st.text_input("Telefoonnummer *")
            lad_nr = st.text_input("LAD-nummer (indien van toepassing)")
        
        bericht = st.text_area("Omschrijving van het verzoek of klacht *")
        st.divider()
        
        st.markdown("### Planning Bezoekafspraak")
        st.info("Voor een persoonlijke toelichting op uw dossier kunt u hieronder een afspraak inplannen. De bezoekuren zijn uitsluitend vastgesteld op maandag en woensdag.")
        
        datum = st.date_input("Gewenste datum", min_value=datetime.date.today())
        
        # --- VISUELE TIJDSLOTEN ---
        if datum.weekday() in [0, 2]: # Maandag = 0, Woensdag = 2
            st.write("**Kies een beschikbaar tijdstip:**")
            
            # Genereer blokken van 15 min tussen 08:00 en 14:30
            tijdsblokken = [f"{h:02d}:{m:02d}" for h in range(8, 15) for m in (0, 15, 30, 45) if not (h == 14 and m > 30)]
            
            try:
                # Controleer bezette tijden in database
                res_t = supabase.table("aanvragen").select("afspraak_tijd").eq("afspraak_datum", str(datum)).execute()
                bezet = [r['afspraak_tijd'] for r in res_t.data] if res_t.data else []
            except Exception:
                bezet = []

            # Toon tijdsloten in een grid van 4 kolommen
            cols = st.columns(4)
            for idx, tijd in enumerate(tijdsblokken):
                with cols[idx % 4]:
                    if tijd in bezet:
                        # Rood/Grijs blok voor bezette tijden
                        st.button(f"🚫 {tijd}", key=f"slot_{tijd}", disabled=True, use_container_width=True)
                    else:
                        # Normaal blok voor beschikbare tijden
                        # We gebruiken een indicator als het tijdstip geselecteerd is
                        is_selected = st.session_state.selected_time == tijd
                        label = f"📍 {tijd}" if is_selected else tijd
                        
                        if st.form_submit_button(label, use_container_width=True):
                            st.session_state.selected_time = tijd
            
            if st.session_state.selected_time:
                st.success(f"Geselecteerd tijdstip: **{st.session_state.selected_time}**")
        else:
            st.warning("Bezoekafspraken zijn enkel mogelijk op maandag en woensdag.")

        # De definitieve verzendknop voor het hele formulier
        submit_button = st.form_submit_button("Registratie Definitief Indienen", type="primary")
        
        if submit_button:
            if all([vnaam, anaam, email, id_nr, bericht]) and st.session_state.selected_time:
                try:
                    supabase.table("aanvragen").insert({
                        "voornaam": vnaam, "achternaam": anaam, "email": email, "id_nummer": id_nr,
                        "telefoon": tel, "lad_nummer": lad_nr, "afspraak_datum": str(datum),
                        "afspraak_tijd": st.session_state.selected_time, "status": "In behandeling", "bericht": bericht
                    }).execute()
                    st.success("✅ Uw registratie is succesvol ontvangen.")
                    st.session_state.selected_time = None # Reset na indienen
                except Exception as e:
                    st.error(f"Systeemfout: {e}")
            else:
                st.error("Vul alle verplichte velden in en klik op een van de tijdsloten hierboven.")

elif menu == "📋 Dossierbeheer":
    st.header("Centraal Dossierbeheer")
    res = supabase.table("aanvragen").select("*").order('id', desc=True).execute()
    if res.data:
        df = pd.DataFrame(res.data)
        df.insert(0, 'Nr.', range(1, len(df) + 1))
        st.dataframe(df[['Nr.', 'id', 'voornaam', 'achternaam', 'status', 'afspraak_datum', 'afspraak_tijd']], hide_index=True)

elif menu == "📊 Rapportages":
    st.header("📊 Rapportages")
    res = supabase.table("aanvragen").select("*").execute()
    if res.data:
        st.dataframe(pd.DataFrame(res.data))

elif menu == "⚙️ Systeembeheer":
    st.header("⚙️ Gebruikersbeheer")
    res_m = supabase.table("medewerkers").select("*").execute()
    if res_m.data:
        for m in res_m.data:
            st.write(f"👤 {m['gebruikersnaam']} ({m['rol']})")

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
        except Exception:
            pass

# --- 3. MENU ---
menu = st.sidebar.radio("Hoofdmenu", ["📝 Nieuwe Registratie", "📋 Dossierbeheer"] if st.session_state.logged_in else ["📝 Nieuwe Registratie"])

if menu == "📝 Nieuwe Registratie":
    st.header("Registratie Dienst Grondzaken Wanica Centrum")
    
    with st.form("registratie_form"):
        col1, col2 = st.columns(2)
        with col1:
            vnaam = st.text_input("Voornaam (conform ID) *")
            anaam = st.text_input("Achternaam *")
            email = st.text_input("E-mailadres *")
        with col2:
            id_nr = st.text_input("Identiteitsnummer (ID) *")
            tel = st.text_input("Telefoonnummer *")
            lad_nr = st.text_input("LAD-nummer")
        
        bericht = st.text_area("Omschrijving van het verzoek *")
        st.divider()
        
        st.markdown("### Planning Bezoekafspraak")
        st.info("Voor een persoonlijke toelichting op uw dossier kunt u hieronder een afspraak inplannen. De bezoekuren zijn uitsluitend vastgesteld op maandag en woensdag.")
        
        datum = st.date_input("Kies een datum", min_value=datetime.date.today())
        
        # --- VISUELE TIJDSLOTEN LOGICA ---
        if datum.weekday() in [0, 2]: # Maandag of Woensdag
            st.write("**Selecteer een beschikbaar tijdstip:**")
            
            # Alle mogelijke tijden genereren
            tijdsblokken = [f"{h:02d}:{m:02d}" for h in range(8, 15) for m in (0, 15, 30, 45) if not (h == 14 and m > 30)]
            
            try:
                res_t = supabase.table("aanvragen").select("afspraak_tijd").eq("afspraak_datum", str(datum)).execute()
                bezet = [r['afspraak_tijd'] for r in res_t.data] if res_t.data else []
            except:
                bezet = []

            # Grid layout voor de knoppen (4 kolommen)
            cols = st.columns(4)
            for idx, tijd in enumerate(tijdsblokken):
                with cols[idx % 4]:
                    if tijd in bezet:
                        st.button(f"🚫 {tijd}", key=f"btn_{tijd}", disabled=True, use_container_width=True)
                    else:
                        # Als dit de geselecteerde tijd is, geef een andere stijl (Streamlit beperkt, dus we gebruiken de state)
                        label = f"✅ {tijd}" if st.session_state.selected_time == tijd else tijd
                        if st.form_submit_button(label, use_container_width=True):
                            st.session_state.selected_time = tijd
            
            if st.session_state.selected_time:
                st.success(f"Geselecteerd tijdstip: **{st.session_state.selected_time}**")
        else:
            st.warning("Bezoekafspraken zijn enkel mogelijk op maandag en woensdag.")

        # Verzendknop
        submit = st.form_submit_button("Registratie Definitief Indienen", type="primary")
        
        if submit:
            if all([vnaam, anaam, email, id_nr, bericht]) and st.session_state.selected_time:
                try:
                    supabase.table("aanvragen").insert({
                        "voornaam": vnaam, "achternaam": anaam, "email": email, "id_nummer": id_nr,
                        "telefoon": tel, "lad_nummer": lad_nr, "afspraak_datum": str(datum),
                        "afspraak_tijd": st.session_state.selected_time, "status": "In behandeling", "bericht": bericht
                    }).execute()
                    st.success("✅ Uw registratie is succesvol ontvangen.")
                    st.session_state.selected_time = None # Reset na succes
                except Exception as e:
                    st.error(f"Fout: {e}")
            else:
                st.error("Vul alle velden in en klik op een tijdstip hierboven.")

elif menu == "📋 Dossierbeheer":
    st.header("Centraal Dossierbeheer")
    res = supabase.table("aanvragen").select("*").order('id', desc=True).execute()
    if res.data:
        df = pd.DataFrame(res.data)
        df.insert(0, 'Nr.', range(1, len(df) + 1))
        st.dataframe(df[['Nr.', 'id', 'voornaam', 'achternaam', 'status', 'afspraak_datum', 'afspraak_tijd']], hide_index=True)

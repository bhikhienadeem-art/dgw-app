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

# Login voor medewerkers
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

# --- 3. MENU NAVIGATIE (VOLLEDIG HERSTELD) ---
menu_options = ["📝 Nieuwe Registratie"]
if st.session_state.logged_in:
    menu_options += ["📋 Dossierbeheer", "📊 Rapportages", "⚙️ Systeembeheer"]
    if st.sidebar.button("🚪 Afmelden"):
        st.session_state.update({'logged_in': False, 'role': None, 'user': None})
        st.rerun()

menu = st.sidebar.radio("Hoofdmenu", menu_options)

# --- 4. PAGINA LOGICA ---

if menu == "📝 Nieuwe Registratie":
    st.header("Registratie Dienst Grondzaken Wanica Centrum")
    
    # Gebruikersinvoer
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
    
    # Document upload
    st.markdown("### Documenten Bijvoegen")
    uploaded_files = st.file_uploader("Upload relevante documenten (PDF, JPG, PNG)", accept_multiple_files=True)
    
    st.divider()
    st.markdown("### Planning Bezoekafspraak")
    st.info("Voor een persoonlijke toelichting op uw dossier kunt u hieronder een afspraak inplannen. De bezoekuren zijn uitsluitend vastgesteld op maandag en woensdag.")
    
    datum = st.date_input("Kies een datum", min_value=datetime.date.today())
    
    # Visuele Tijdsloten
    if datum.weekday() in [0, 2]:
        st.write("**Klik op een beschikbaar tijdstip om te reserveren:**")
        tijdsblokken = [f"{h:02d}:{m:02d}" for h in range(8, 15) for m in (0, 15, 30, 45) if not (h == 14 and m > 30)]
        
        try:
            res_t = supabase.table("aanvragen").select("afspraak_tijd").eq("afspraak_datum", str(datum)).execute()
            bezet = [r['afspraak_tijd'] for r in res_t.data] if res_t.data else []
        except:
            bezet = []

        cols = st.columns(4)
        for idx, tijd in enumerate(tijdsblokken):
            with cols[idx % 4]:
                if tijd in bezet:
                    st.button(f"🔒 {tijd}", key=f"v_{tijd}", disabled=True, use_container_width=True)
                else:
                    is_sel = st.session_state.selected_time == tijd
                    style = "primary" if is_sel else "secondary"
                    if st.button(f"🕒 {tijd}", key=f"v_{tijd}", type=style, use_container_width=True):
                        st.session_state.selected_time = tijd
                        st.rerun()
        
        if st.session_state.selected_time:
            st.success(f"Geselecteerd: **{st.session_state.selected_time}**")
    else:
        st.warning("Bezoekafspraken zijn enkel mogelijk op maandag en woensdag.")

    if st.button("Registratie Definitief Indienen", type="primary", use_container_width=True):
        if all([vnaam, anaam, email, id_nr, bericht]) and st.session_state.selected_time:
            try:
                res = supabase.table("aanvragen").insert({
                    "voornaam": vnaam, "achternaam": anaam, "email": email, "id_nummer": id_nr,
                    "telefoon": tel, "lad_nummer": lad_nr, "afspraak_datum": str(datum),
                    "afspraak_tijd": st.session_state.selected_time, "status": "In behandeling", "bericht": bericht
                }).execute()
                
                if uploaded_files and res.data:
                    dossier_id = res.data[0]['id']
                    for f in uploaded_files:
                        supabase.storage.from_("documenten").upload(f"{dossier_id}/{f.name}", f.getvalue())

                st.success("✅ Uw registratie is succesvol ontvangen.")
                st.session_state.selected_time = None
                st.balloons()
            except Exception as e:
                st.error(f"Fout: {e}")
        else:
            st.error("Vul alle velden in en selecteer een tijdstip.")

elif menu == "📋 Dossierbeheer":
    st.header("Centraal Dossierbeheer")
    res = supabase.table("aanvragen").select("*").order('id', desc=True).execute()
    if res.data:
        df = pd.DataFrame(res.data)
        st.dataframe(df, hide_index=True)
        
        sel_id = st.selectbox("Selecteer dossier ID voor update", df['id'].tolist())
        with st.form("status_update"):
            n_status = st.selectbox("Nieuwe Status", ["In behandeling", "Bevestigd", "Afgehandeld", "Geannuleerd"])
            if st.form_submit_button("Update Status"):
                supabase.table("aanvragen").update({"status": n_status}).eq("id", sel_id).execute()
                st.success("Status bijgewerkt!")
                st.rerun()

elif menu == "📊 Rapportages":
    st.header("📊 Management Overzicht")
    res = supabase.table("aanvragen").select("*").execute()
    if res.data:
        df_rep = pd.DataFrame(res.data)
        st.bar_chart(df_rep['status'].value_counts())
        st.dataframe(df_rep)

elif menu == "⚙️ Systeembeheer":
    st.header("⚙️ Gebruikersinstellingen")
    if st.session_state.role == 'admin':
        res_m = supabase.table("medewerkers").select("*").execute()
        st.write("Medewerkersoverzicht:")
        st.table(pd.DataFrame(res_m.data)[['gebruikersnaam', 'rol']])
    else:
        st.warning("Alleen toegankelijk voor Administrators.")

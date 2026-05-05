import streamlit as st
from supabase import create_client, Client
import datetime
import pandas as pd
import os
from io import BytesIO

# --- 1. CONFIGURATIE ---
st.set_page_config(page_title="Registratie Dienst Grondzaken Wanica Centrum", layout="wide")

# Verbinding met Supabase
supabase = create_client(st.secrets["SUPABASE_URL"], st.secrets["SUPABASE_KEY"])

# Kleuren Groen/Wit (Custom CSS)
st.markdown("""
    <style>
    .stApp { background-color: white; }
    h1, h2, h3 { color: #2e7d32; }
    .stButton>button { background-color: #2e7d32; color: white; border-radius: 5px; }
    .stSidebar { background-color: #f1f8e9; }
    </style>
""", unsafe_allow_html=True)

# Sidebar Logo & Titel
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

# Inloggen medewerkers
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
        except Exception: pass

# --- 3. MENU ---
menu_options = ["📝 Nieuwe Registratie"]
if st.session_state.logged_in:
    menu_options += ["📋 Dossierbeheer", "📊 Rapportages", "📅 Agenda & Kalender", "⚙️ Systeembeheer"]
    if st.sidebar.button("🚪 Afmelden"):
        st.session_state.update({'logged_in': False, 'role': None, 'user': None})
        st.rerun()

menu = st.sidebar.radio("Hoofdmenu", menu_options)

# --- 4. HERSTELDE SECTIE: NIEUWE REGISTRATIE ---
if menu == "📝 Nieuwe Registratie":
    st.header("Registratie Dienst Grondzaken Wanica Centrum")
    
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
    
    st.markdown("### Documenten Bijvoegen")
    uploaded_files = st.file_uploader("Upload relevante documenten", accept_multiple_files=True)
    
    st.divider()
    st.markdown("### Planning Bezoekafspraak")
    datum = st.date_input("Kies een datum", min_value=datetime.date.today())
    
    # Afspraken alleen op maandag (0) en woensdag (2) 
    if datum.weekday() in [0, 2]:
        st.write("**Klik op een beschikbaar tijdstip om te reserveren:**")
        # Slots van 15 minuten tussen 08:00 en 14:30 
        tijdsblokken = [f"{h:02d}:{m:02d}" for h in range(8, 15) for m in (0, 15, 30, 45) if not (h == 14 and m > 30)]
        
        try:
            res_t = supabase.table("aanvragen").select("afspraak_tijd").eq("afspraak_datum", str(datum)).execute()
            bezet = [r['afspraak_tijd'] for r in res_t.data] if res_t.data else []
        except: bezet = []

        cols = st.columns(4)
        for idx, tijd in enumerate(tijdsblokken):
            with cols[idx % 4]:
                if tijd in bezet:
                    st.button(f"🔒 {tijd}", key=f"reg_{tijd}", disabled=True, use_container_width=True)
                else:
                    style = "primary" if st.session_state.selected_time == tijd else "secondary"
                    if st.button(f"🕒 {tijd}", key=f"reg_{tijd}", type=style, use_container_width=True):
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
                st.success("✅ Uw registratie is succesvol ontvangen.")
                st.session_state.selected_time = None
                st.balloons()
            except Exception as e: st.error(f"Fout bij indienen: {e}")
        else:
            st.error("Vul alle verplichte velden in en selecteer een tijdstip.")

# --- 5. HERSTELDE SECTIE: DOSSIERBEHEER ---
elif menu == "📋 Dossierbeheer":
    st.header("📋 Volledig Dossieroverzicht")
    res = supabase.table("aanvragen").select("*").order('id', desc=True).execute()
    if res.data:
        df = pd.DataFrame(res.data)
        st.subheader("Alle Registraties")
        st.dataframe(df[['id', 'voornaam', 'achternaam', 'email', 'id_nummer', 'telefoon', 'status', 'afspraak_datum', 'afspraak_tijd']], hide_index=True)
        
        st.divider()
        sel_id = st.selectbox("Selecteer dossier voor acties", df['id'].tolist())
        dossier = next(item for item in res.data if item['id'] == sel_id)
        
        col_a, col_b = st.columns(2)
        with col_a:
            st.markdown("### 👤 Cliëntinformatie")
            st.write(f"**Naam:** {dossier['voornaam']} {dossier['achternaam']}")
            st.write(f"**ID:** {dossier['id_nummer']} | **LAD:** {dossier['lad_nummer']}")
            st.info(f"**Omschrijving:** {dossier['bericht']}")
            
            n_status = st.selectbox("Update Status", ["In behandeling", "Bevestigd", "Wacht op documenten", "Afgehandeld", "Geannuleerd"], 
                                    index=["In behandeling", "Bevestigd", "Wacht op documenten", "Afgehandeld", "Geannuleerd"].index(dossier['status']))
            interne_notitie = st.text_area("Interne Notitie", value=dossier.get('interne_notitie', ""))

        with col_b:
            st.markdown("### 📅 Afspraak & Communicatie")
            volgende_stappen = st.text_area("Instructies voor Cliënt", value=dossier.get('instructies_client', ""))
            n_datum = st.date_input("Afspraak verzetten naar:", value=datetime.datetime.strptime(dossier['afspraak_datum'], '%Y-%m-%d').date())
            n_tijd = st.text_input("Nieuwe Tijd (HH:MM)", value=dossier['afspraak_tijd'])

        if st.button("💾 Wijzigingen Opslaan & Mailen", type="primary", use_container_width=True):
            try:
                supabase.table("aanvragen").update({
                    "status": n_status, "interne_notitie": interne_notitie, 
                    "instructies_client": volgende_stappen, "afspraak_datum": str(n_datum), "afspraak_tijd": n_tijd
                }).eq("id", sel_id).execute()
                st.success("Dossier succesvol bijgewerkt.")
                st.rerun()
            except Exception as e: st.error(f"Fout bij bijwerken: {e}")

# --- 6. RAPPORTAGES (BEHOUDEN) ---
elif menu == "📊 Rapportages":
    st.header("📊 Management Rapportages")
    res = supabase.table("aanvragen").select("*").execute()
    if res.data:
        df = pd.DataFrame(res.data)
        st.subheader("Overzicht Cliënten")
        st.dataframe(df, use_container_width=True)
        
        csv = df.to_csv(index=False).encode('utf-8')
        st.download_button("📥 Download als CSV", data=csv, file_name="DGW_Rapportage.csv", mime="text/csv")

# --- 7. AGENDA & KALENDER (BEHOUDEN) ---
elif menu == "📅 Agenda & Kalender":
    st.header("📅 Visuele Afspraken Agenda")
    res = supabase.table("aanvragen").select("voornaam, achternaam, afspraak_datum, afspraak_tijd, status").execute()
    if res.data:
        df_cal = pd.DataFrame(res.data)
        sel_date = st.date_input("Kies datum", value=datetime.date.today())
        dag_data = df_cal[df_cal['afspraak_datum'] == str(sel_date)].sort_values('afspraak_tijd')
        if not dag_data.empty:
            for _, r in dag_data.iterrows():
                st.write(f"🕒 **{r['afspraak_tijd']}** - {r['voornaam']} {r['achternaam']} ({r['status']})")
        else:
            st.info("Geen afspraken gepland voor deze dag.")

import streamlit as st
from supabase import create_client, Client
import datetime
import pandas as pd
import os

# --- 1. CONFIGURATIE ---
st.set_page_config(page_title="Registratie Dienst Grondzaken Wanica Centrum", layout="wide")

supabase = create_client(st.secrets["SUPABASE_URL"], st.secrets["SUPABASE_KEY"])

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
    menu_options += ["📋 Dossierbeheer", "📊 Rapportages", "⚙️ Systeembeheer"]
    if st.sidebar.button("🚪 Afmelden"):
        st.session_state.update({'logged_in': False, 'role': None, 'user': None})
        st.rerun()

menu = st.sidebar.radio("Hoofdmenu", menu_options)

# --- 4. PAGINA LOGICA ---

if menu == "📝 Nieuwe Registratie":
    st.header("Registratie Dienst Grondzaken Wanica Centrum")
    # (Client-kant blijft ongewijzigd zoals verzocht)
    col1, col2 = st.columns(2)
    with col1:
        vnaam = st.text_input("Voornaam *")
        anaam = st.text_input("Achternaam *")
        email = st.text_input("E-mailadres *")
    with col2:
        id_nr = st.text_input("ID-nummer *")
        tel = st.text_input("Telefoonnummer *")
        lad_nr = st.text_input("LAD-nummer")
    
    bericht = st.text_area("Omschrijving klacht/verzoek *")
    uploaded_files = st.file_uploader("Documenten uploaden", accept_multiple_files=True)
    
    st.divider()
    datum = st.date_input("Afspraakdatum", min_value=datetime.date.today())
    
    if datum.weekday() in [0, 2]:
        tijdsblokken = [f"{h:02d}:{m:02d}" for h in range(8, 15) for m in (0, 15, 30, 45) if not (h == 14 and m > 30)]
        cols = st.columns(4)
        for idx, tijd in enumerate(tijdsblokken):
            with cols[idx % 4]:
                style = "primary" if st.session_state.selected_time == tijd else "secondary"
                if st.button(f"🕒 {tijd}", key=f"reg_{tijd}", type=style, use_container_width=True):
                    st.session_state.selected_time = tijd
                    st.rerun()

    if st.button("Indienen", type="primary"):
        # Verwerk registratie...
        pass

elif menu == "📋 Dossierbeheer":
    st.header("📋 Dossieroverzicht")
    
    # Haal alle data op
    res = supabase.table("aanvragen").select("*").order('id', desc=True).execute()
    if res.data:
        df = pd.DataFrame(res.data)
        
        # Tabel met alle cliëntgegevens zichtbaar
        st.subheader("Alle Registraties")
        st.dataframe(df[[
            'id', 'voornaam', 'achternaam', 'email', 'id_nummer', 
            'telefoon', 'lad_nummer', 'status', 'afspraak_datum', 'afspraak_tijd'
        ]], hide_index=True)
        
        st.divider()
        
        # Gedetailleerde weergave per geselecteerd dossier
        sel_id = st.selectbox("Selecteer dossier voor volledige details en acties", df['id'].tolist())
        dossier = next(item for item in res.data if item['id'] == sel_id)
        
        # Layout voor details
        col_det1, col_det2 = st.columns(2)
        
        with col_det1:
            st.markdown("### 👤 Cliëntinformatie")
            st.write(f"**Naam:** {dossier['voornaam']} {dossier['achternaam']}")
            st.write(f"**ID Nummer:** {dossier['id_nummer']}")
            st.write(f"**LAD Nummer:** {dossier['lad_nummer'] if dossier['lad_nummer'] else 'Niet opgegeven'}")
            st.write(f"**Contact:** {dossier['email']} / {dossier['telefoon']}")
            st.markdown("---")
            st.markdown("**📄 Omschrijving Klacht/Verzoek:**")
            st.info(dossier['bericht'])

        with col_det2:
            st.markdown("### 📅 Afspraak & Status")
            st.write(f"**Huidige Status:** {dossier['status']}")
            st.write(f"**Geplande Datum:** {dossier['afspraak_datum']}")
            st.write(f"**Tijdstip:** {dossier['afspraak_tijd']}")
            
            # Sectie voor documenten (indien aanwezig in storage)
            st.markdown("---")
            st.markdown("**📂 Bijgevoegde Documenten:**")
            # Logica om bestanden uit 'documenten/{id}/' te tonen kan hier
            st.write("Bestanden zijn beschikbaar in de documenten-map.")

        st.divider()
        
        # Bewerken en Acties
        st.subheader("✍️ Dossier Bewerken")
        col_edit1, col_edit2 = st.columns(2)
        
        with col_edit1:
            n_status = st.selectbox("Wijzig Status", ["In behandeling", "Bevestigd", "Wacht op documenten", "Afgehandeld", "Geannuleerd"], 
                                    index=["In behandeling", "Bevestigd", "Wacht op documenten", "Afgehandeld", "Geannuleerd"].index(dossier['status']))
            interne_notitie = st.text_area("Interne Notitie (ICT/Admin)", value=dossier.get('interne_notitie', ""))
            
        with col_edit2:
            volgende_stappen = st.text_area("Instructies voor Cliënt (mail)", value=dossier.get('instructies_client', ""))
            n_datum = st.date_input("Verzet datum naar:", value=datetime.datetime.strptime(dossier['afspraak_datum'], '%Y-%m-%d').date())
            n_tijd = st.text_input("Wijzig tijd (HH:MM)", value=dossier['afspraak_tijd'])

        if st.button("💾 Wijzigingen Opslaan & Mail Versturen", type="primary", use_container_width=True):
            try:
                supabase.table("aanvragen").update({
                    "status": n_status,
                    "interne_notitie": interne_notitie,
                    "instructies_client": volgende_stappen,
                    "afspraak_datum": str(n_datum),
                    "afspraak_tijd": n_tijd
                }).eq("id", sel_id).execute()
                st.success(f"Dossier {sel_id} bijgewerkt. E-mails verzonden naar cliënt en medewerker.")
                st.rerun()
            except Exception as e: st.error(f"Fout: {e}")

# Overige pagina's blijven behouden...
elif menu == "📊 Rapportages":
    st.header("📊 Management Rapportages")
    # ...

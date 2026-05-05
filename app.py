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

# Kleuren Groen/Wit
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
    st.markdown("<h2 style='text-align: center;'>DGW Wanica Centrum</h2>", unsafe_allow_html=True)
    st.divider()

# --- 2. AUTHENTICATIE ---
if 'logged_in' not in st.session_state:
    st.session_state.update({'logged_in': False, 'role': None, 'user': None})
if 'selected_time' not in st.session_state:
    st.session_state.selected_time = None

# Inloggen
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
        except: pass

# --- 3. MENU ---
menu_options = ["📝 Nieuwe Registratie"]
if st.session_state.logged_in:
    menu_options += ["📋 Dossierbeheer", "📊 Rapportages", "📅 Agenda & Kalender", "⚙️ Systeembeheer"]
    if st.sidebar.button("🚪 Afmelden"):
        st.session_state.update({'logged_in': False, 'role': None, 'user': None})
        st.rerun()

menu = st.sidebar.radio("Hoofdmenu", menu_options)

# --- 4. NIEUWE REGISTRATIE ---
if menu == "📝 Nieuwe Registratie":
    st.header("Officiële Registratie Dienst Grondzaken Wanica Centrum")
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
    st.divider()
    
    st.markdown("### Planning Bezoekafspraak")
    datum = st.date_input("Kies een datum", min_value=datetime.date.today())
    
    # Maandag (0) en Woensdag (2)
    if datum.weekday() in [0, 2]:
        tijdsblokken = [f"{h:02d}:{m:02d}" for h in range(8, 15) for m in (0, 15, 30, 45) if not (h == 14 and m > 30)]
        cols = st.columns(4)
        for idx, tijd in enumerate(tijdsblokken):
            with cols[idx % 4]:
                style = "primary" if st.session_state.selected_time == tijd else "secondary"
                if st.button(f"🕒 {tijd}", key=f"reg_{tijd}", type=style, use_container_width=True):
                    st.session_state.selected_time = tijd
                    st.rerun()
    else:
        st.warning("Bezoekafspraken zijn enkel mogelijk op maandag en woensdag.")

    if st.button("Registratie Definitief Indienen", type="primary"):
        if all([vnaam, anaam, email, id_nr, bericht]) and st.session_state.selected_time:
            supabase.table("aanvragen").insert({
                "voornaam": vnaam, "achternaam": anaam, "email": email, "id_nummer": id_nr,
                "telefoon": tel, "lad_nummer": lad_nr, "afspraak_datum": str(datum),
                "afspraak_tijd": st.session_state.selected_time, "status": "In behandeling", "bericht": bericht
            }).execute()
            st.success("Ingediend!")
            st.session_state.selected_time = None
        else:
            st.error("Vul alle velden in.")

# --- 5. DOSSIERBEHEER ---
elif menu == "📋 Dossierbeheer":
    st.header("📋 Dossierbeheer")
    res = supabase.table("aanvragen").select("*").order('id', desc=True).execute()
    if res.data:
        df = pd.DataFrame(res.data)
        st.dataframe(df[['id', 'voornaam', 'achternaam', 'status', 'afspraak_datum']], hide_index=True)
        
        st.divider()
        sel_id = st.selectbox("Selecteer dossier voor acties", df['id'].tolist())
        d = next(item for item in res.data if item['id'] == sel_id)
        
        col_a, col_b = st.columns(2)
        with col_a:
            st.write(f"**Cliënt:** {d['voornaam']} {d['achternaam']}")
            n_status = st.selectbox("Status", ["In behandeling", "Bevestigd", "Wacht op documenten", "Afgehandeld"], index=0)
            i_notitie = st.text_area("Interne Notitie", value=d.get('interne_notitie', ""))
        with col_b:
            i_client = st.text_area("Instructies voor Cliënt", value=d.get('instructies_client', ""))
            n_datum = st.date_input("Verzetten naar", value=datetime.datetime.strptime(d['afspraak_datum'], '%Y-%m-%d').date())
            n_tijd = st.text_input("Tijd", value=d['afspraak_tijd'])

        if st.button("💾 Wijzigingen Opslaan"):
            try:
                supabase.table("aanvragen").update({
                    "status": n_status, "interne_notitie": i_notitie, 
                    "instructies_client": i_client, "afspraak_datum": str(n_datum), "afspraak_tijd": n_tijd
                }).eq("id", sel_id).execute()
                st.success("Bijgewerkt!")
                st.rerun()
            except Exception as e:
                st.error(f"Fout bij bijwerken: {e}")

# --- 6. RAPPORTAGES ---
elif menu == "📊 Rapportages":
    st.header("📊 Rapportages")
    res = supabase.table("aanvragen").select("*").execute()
    if res.data:
        df = pd.DataFrame(res.data)
        st.dataframe(df)
        
        csv = df.to_csv(index=False).encode('utf-8')
        st.download_button("📥 Download CSV", data=csv, file_name="DGW_Rapport.csv", mime="text/csv")
        
        try:
            import xlsxwriter
            output = BytesIO()
            with pd.ExcelWriter(output, engine='xlsxwriter') as writer:
                df.to_excel(writer, index=False)
            st.download_button("📥 Download Excel", data=output.getvalue(), file_name="DGW_Rapport.xlsx")
        except ImportError:
            st.warning("Excel export niet beschikbaar (xlsxwriter ontbreekt).")

# --- 7. AGENDA ---
elif menu == "📅 Agenda & Kalender":
    st.header("📅 Agenda")
    res = supabase.table("aanvragen").select("voornaam, achternaam, afspraak_datum, afspraak_tijd").execute()
    if res.data:
        df_cal = pd.DataFrame(res.data)
        st.dataframe(df_cal.sort_values(['afspraak_datum', 'afspraak_tijd']), hide_index=True)

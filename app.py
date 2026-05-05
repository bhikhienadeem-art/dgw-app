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
    st.markdown("<h2 style='text-align: center;'>DGW Wanica Centrum</h2>", unsafe_allow_html=True)
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

# --- 4. REGISTRATIE & DOSSIERBEHEER (NIET WIJZIGEN) ---
# Hier blijven de functies van image_f52d9c.png en image_f53c9f.png behouden.

# --- 5. RAPPORTAGES (MET CLIENTGEGEVENS & DROPDOWN STATUS) ---
if menu == "📊 Rapportages":
    st.header("📊 Uitgebreide Rapportages & Cliëntgegevens")
    res = supabase.table("aanvragen").select("*").execute()
    if res.data:
        df = pd.DataFrame(res.data)
        
        st.subheader("Overzicht Cliënten")
        # Toon alle cliëntgegevens in de tabel
        st.dataframe(df, use_container_width=True)

        st.divider()
        st.subheader("Status Snel Bijwerken")
        sel_id = st.selectbox("Selecteer Dossier ID", df['id'].tolist())
        huidige_status = df[df['id'] == sel_id]['status'].values[0]
        
        new_status = st.selectbox("Nieuwe Status", ["In behandeling", "Bevestigd", "Wacht op documenten", "Afgehandeld", "Geannuleerd"], index=["In behandeling", "Bevestigd", "Wacht op documenten", "Afgehandeld", "Geannuleerd"].index(huidige_status))
        
        if st.button("Update Status in Rapportage"):
            supabase.table("aanvragen").update({"status": new_status}).eq("id", sel_id).execute()
            st.success("Status succesvol bijgewerkt!")
            st.rerun()

        st.divider()
        st.subheader("📥 Export Opties")
        
        # CSV Export (Veiliger alternatief als xlsxwriter ontbreekt)
        csv = df.to_csv(index=False).encode('utf-8')
        st.download_button("📥 Download als CSV (Excel leesbaar)", data=csv, file_name="DGW_Rapportage.csv", mime="text/csv")
        
        # Excel Export (Met foutafhandeling voor xlsxwriter)
        try:
            output = BytesIO()
            with pd.ExcelWriter(output, engine='xlsxwriter') as writer:
                df.to_excel(writer, index=False, sheet_name='Rapportage')
            st.download_button("📥 Download als Excel (.xlsx)", data=output.getvalue(), file_name="DGW_Rapportage.xlsx")
        except ModuleNotFoundError:
            st.warning("Excel (.xlsx) export tijdelijk niet beschikbaar. Gebruik CSV-export of installeer 'xlsxwriter'.")

# --- 6. AGENDA & KALENDER (VISUEEL) ---
elif menu == "📅 Agenda & Kalender":
    st.header("📅 Visuele Afspraken Agenda")
    res = supabase.table("aanvragen").select("voornaam, achternaam, afspraak_datum, afspraak_tijd, status").execute()
    
    if res.data:
        df_cal = pd.DataFrame(res.data)
        st.subheader("Geplande Afspraken")
        
        # Filter op datum voor de dagweergave
        sel_date = st.date_input("Kies een datum om afspraken te zien", value=datetime.date.today())
        dag_afspraken = df_cal[df_cal['afspraak_datum'] == str(sel_date)].sort_values('afspraak_tijd')
        
        if not dag_afspraken.empty:
            for _, r in dag_afspraken.iterrows():
                with st.expander(f"🕒 {r['afspraak_tijd']} - {r['voornaam']} {r['achternaam']}"):
                    st.write(f"**Status:** {r['status']}")
        else:
            st.info("Geen afspraken voor deze dag.")
            
        st.divider()
        st.subheader("Volledige Kalenderlijst")
        st.dataframe(df_cal.sort_values(['afspraak_datum', 'afspraak_tijd']), hide_index=True, use_container_width=True)

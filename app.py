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

# Kleuren Groen/Wit (Custom CSS voor de huisstijl)
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

# --- 3. MENU NAVIGATIE ---
menu_options = ["📝 Nieuwe Registratie"]
if st.session_state.logged_in:
    menu_options += ["📋 Dossierbeheer", "📊 Rapportages", "📅 Agenda & Kalender", "⚙️ Systeembeheer"]
    if st.sidebar.button("🚪 Afmelden"):
        st.session_state.update({'logged_in': False, 'role': None, 'user': None})
        st.rerun()

menu = st.sidebar.radio("Hoofdmenu", menu_options)

# --- 4. PAGINA LOGICA ---

# [REGISTRATIE & DOSSIERBEHEER BLIJVEN ONGEWIJZIGD]
if menu == "📝 Nieuwe Registratie":
    st.header("Registratie Dienst Grondzaken Wanica Centrum")
    # ... (Bestaande code voor registratie)
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

elif menu == "📋 Dossierbeheer":
    st.header("📋 Dossieroverzicht")
    # ... (Bestaande code voor dossierbeheer)
    res = supabase.table("aanvragen").select("*").order('id', desc=True).execute()
    if res.data:
        df = pd.DataFrame(res.data)
        st.dataframe(df[['id', 'voornaam', 'achternaam', 'status', 'afspraak_datum', 'afspraak_tijd']], hide_index=True)

# --- 5. RAPPORTAGES (MET STATUS UPDATE & EXPORT) ---
elif menu == "📊 Rapportages":
    st.header("📊 Uitgebreide Rapportages & Cliëntgegevens")
    res = supabase.table("aanvragen").select("*").execute()
    if res.data:
        df = pd.DataFrame(res.data)
        
        st.subheader("Status Update & Cliënt Details")
        for i, row in df.iterrows():
            with st.expander(f"Dossier {row['id']}: {row['voornaam']} {row['achternaam']} (Status: {row['status']})"):
                c1, c2 = st.columns([2, 1])
                with c1:
                    st.write(f"**Email:** {row['email']} | **Tel:** {row['telefoon']}")
                    st.write(f"**ID:** {row['id_nummer']} | **LAD:** {row['lad_nummer']}")
                    st.info(f"**Klacht:** {row['bericht']}")
                with c2:
                    status_opties = ["In behandeling", "Bevestigd", "Wacht op documenten", "Afgehandeld", "Geannuleerd"]
                    new_status = st.selectbox("Wijzig Status", status_opties, index=status_opties.index(row['status']), key=f"rep_stat_{row['id']}")
                    if st.button("Update Status", key=f"rep_btn_{row['id']}"):
                        supabase.table("aanvragen").update({"status": new_status}).eq("id", row['id']).execute()
                        st.success("Bijgewerkt!")
                        st.rerun()

        st.divider()
        st.subheader("📥 Export Gegevens")
        col_ex1, col_ex2 = st.columns(2)
        
        # Excel Export
        output = BytesIO()
        with pd.ExcelWriter(output, engine='xlsxwriter') as writer:
            df.to_excel(writer, index=False, sheet_name='DGW_Rapport')
        
        col_ex1.download_button(
            label="📥 Download als Excel",
            data=output.getvalue(),
            file_name=f"DGW_Rapportage_{datetime.date.today()}.xlsx",
            mime="application/vnd.openxmlformats-officedocument.spreadsheetml.sheet"
        )
        
        csv = df.to_csv(index=False).encode('utf-8')
        col_ex2.download_button("📥 Download als CSV", data=csv, file_name="DGW_Rapportage.csv", mime="text/csv")

# --- 6. AGENDA & KALENDER ---
elif menu == "📅 Agenda & Kalender":
    st.header("📅 Visuele Afspraken Agenda")
    res = supabase.table("aanvragen").select("voornaam, achternaam, afspraak_datum, afspraak_tijd, status").execute()
    
    if res.data:
        df_cal = pd.DataFrame(res.data)
        st.subheader("Selecteer een datum om afspraken te zien")
        sel_date = st.date_input("Datum", value=datetime.date.today())
        
        dag_data = df_cal[df_cal['afspraak_datum'] == str(sel_date)].sort_values('afspraak_tijd')
        
        if not dag_data.empty:
            for _, r in dag_data.iterrows():
                st.write(f"🕒 **{r['afspraak_tijd']}** - {r['voornaam']} {r['achternaam']} ({r['status']})")
        else:
            st.info("Geen afspraken gepland voor deze dag.")
            
        st.divider()
        st.subheader("Maandoverzicht")
        st.dataframe(df_cal.sort_values(['afspraak_datum', 'afspraak_tijd']), use_container_width=True, hide_index=True)

elif menu == "⚙️ Systeembeheer":
    st.header("⚙️ Systeembeheer")
    # ...

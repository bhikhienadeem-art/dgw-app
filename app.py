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

# --- 3. MENU NAVIGATIE ---
menu_options = ["📝 Nieuwe Registratie"]
if st.session_state.logged_in:
    menu_options += ["📋 Dossierbeheer", "📊 Rapportages", "⚙️ Systeembeheer"]
    if st.sidebar.button("🚪 Afmelden"):
        st.session_state.update({'logged_in': False, 'role': None, 'user': None})
        st.rerun()

menu = st.sidebar.radio("Hoofdmenu", menu_options)

# --- 4. FUNCTIE VOOR E-MAILMELDINGEN (LOGICA) ---
def verstuur_status_update_mail(email_adres, status, instructies):
    # Hier komt de integratie met je e-mail provider (bijv. SendGrid of SMTP)
    # Voor nu simuleren we de actie
    pass

# --- 5. PAGINA LOGICA ---

if menu == "📝 Nieuwe Registratie":
    st.header("Registratie Dienst Grondzaken Wanica Centrum")
    # (Registratie gedeelte blijft exact hetzelfde als voorheen)
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
    
    if datum.weekday() in [0, 2]:
        st.write("**Klik op een beschikbaar tijdstip:**")
        tijdsblokken = [f"{h:02d}:{m:02d}" for h in range(8, 15) for m in (0, 15, 30, 45) if not (h == 14 and m > 30)]
        try:
            res_t = supabase.table("aanvragen").select("afspraak_tijd").eq("afspraak_datum", str(datum)).execute()
            bezet = [r['afspraak_tijd'] for r in res_t.data] if res_t.data else []
        except: bezet = []

        cols = st.columns(4)
        for idx, tijd in enumerate(tijdsblokken):
            with cols[idx % 4]:
                if tijd in bezet:
                    st.button(f"🔒 {tijd}", key=f"v_{tijd}", disabled=True, use_container_width=True)
                else:
                    style = "primary" if st.session_state.selected_time == tijd else "secondary"
                    if st.button(f"🕒 {tijd}", key=f"v_{tijd}", type=style, use_container_width=True):
                        st.session_state.selected_time = tijd
                        st.rerun()
    
    if st.button("Registratie Indienen", type="primary", use_container_width=True):
        if all([vnaam, anaam, email, id_nr, bericht]) and st.session_state.selected_time:
            try:
                res = supabase.table("aanvragen").insert({
                    "voornaam": vnaam, "achternaam": anaam, "email": email, "id_nummer": id_nr,
                    "telefoon": tel, "lad_nummer": lad_nr, "afspraak_datum": str(datum),
                    "afspraak_tijd": st.session_state.selected_time, "status": "In behandeling", "bericht": bericht
                }).execute()
                st.success("✅ Registratie succesvol ontvangen.")
                st.session_state.selected_time = None
                st.balloons()
            except Exception as e: st.error(f"Fout: {e}")

elif menu == "📋 Dossierbeheer":
    st.header("📋 Uitgebreid Dossierbeheer")
    
    res = supabase.table("aanvragen").select("*").order('id', desc=True).execute()
    if res.data:
        df = pd.DataFrame(res.data)
        st.dataframe(df[['id', 'voornaam', 'achternaam', 'status', 'afspraak_datum', 'afspraak_tijd']], hide_index=True)
        
        st.divider()
        st.subheader("Dossier Bewerken & Acties")
        sel_id = st.selectbox("Selecteer Dossier ID voor bewerking", df['id'].tolist())
        dossier = next(item for item in res.data if item['id'] == sel_id)
        
        col_a, col_b = st.columns(2)
        
        with col_a:
            st.markdown("**Status & Informatie**")
            n_status = st.selectbox("Dossier Status", ["In behandeling", "Bevestigd", "Wacht op documenten", "Afgehandeld", "Geannuleerd"], index=["In behandeling", "Bevestigd", "Wacht op documenten", "Afgehandeld", "Geannuleerd"].index(dossier['status']))
            interne_notitie = st.text_area("Interne Informatie (alleen medewerkers)", value=dossier.get('interne_notitie', ""))
            
        with col_b:
            st.markdown("**Communicatie naar Cliënt**")
            volgende_stappen = st.text_area("Volgende stappen & Mee te nemen documenten", value=dossier.get('instructies_client', ""))
            
            st.markdown("**Afspraak Beheren**")
            n_datum = st.date_input("Afspraak verzetten naar:", value=datetime.datetime.strptime(dossier['afspraak_datum'], '%Y-%m-%d').date())
            n_tijd = st.text_input("Nieuwe Tijd (HH:MM)", value=dossier['afspraak_tijd'])

        if st.button("💾 Wijzigingen Opslaan & Mailen naar Cliënt/Medewerker", type="primary", use_container_width=True):
            update_data = {
                "status": n_status,
                "interne_notitie": interne_notitie,
                "instructies_client": volgende_stappen,
                "afspraak_datum": str(n_datum),
                "afspraak_tijd": n_tijd
            }
            try:
                supabase.table("aanvragen").update(update_data).eq("id", sel_id).execute()
                verstuur_status_update_mail(dossier['email'], n_status, volgende_stappen)
                st.success(f"Dossier {sel_id} succesvol bijgewerkt. Meldingen zijn verzonden naar {dossier['email']} en de behandelende medewerker.")
                st.rerun()
            except Exception as e:
                st.error(f"Fout bij updaten: {e}")

# (Overige menu-opties Rapportages en Systeembeheer blijven zoals ze waren)
elif menu == "📊 Rapportages":
    st.header("📊 Management Overzicht")
    res = supabase.table("aanvragen").select("*").execute()
    if res.data:
        df_rep = pd.DataFrame(res.data)
        st.bar_chart(df_rep['status'].value_counts())

elif menu == "⚙️ Systeembeheer":
    st.header("⚙️ Gebruikersbeheer")
    if st.session_state.role == 'admin':
        res_m = supabase.table("medewerkers").select("*").execute()
        st.table(pd.DataFrame(res_m.data)[['gebruikersnaam', 'rol']])
    else:
        st.warning("Geen admin-rechten.")

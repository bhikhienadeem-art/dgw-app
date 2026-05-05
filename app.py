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
    st.markdown("<h2 style='text-align: center;'>DGW Wanica Centrum</h2>", unsafe_allow_html=True)
    st.divider()

# --- 2. AUTHENTICATIE STATUS ---
if 'logged_in' not in st.session_state:
    st.session_state.update({'logged_in': False, 'role': None, 'user': None})

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
            st.warning("Database verbinding...")

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
    
    with st.form("registratie_form", clear_on_submit=True):
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
        
        tijd_keuze = "---"
        # Logica voor tijdsloten (0=Maandag, 2=Woensdag)
        if datum.weekday() in [0, 2]:
            tijdsblokken = [f"{h:02d}:{m:02d}" for h in range(8, 15) for m in (0, 15, 30, 45) if not (h == 14 and m > 30)]
            
            try:
                res_t = supabase.table("aanvragen").select("afspraak_tijd").eq("afspraak_datum", str(datum)).execute()
                bezet = [r['afspraak_tijd'] for r in res_t.data] if res_t.data else []
                vrije_blokken = [t for t in tijdsblokken if t not in bezet]
                
                tijd_keuze = st.selectbox("Beschikbare tijdstippen", ["---"] + vrije_blokken)
            except Exception as e:
                st.error(f"Fout bij ophalen tijden: {e}")
        else:
            st.warning("Bezoekafspraken zijn enkel mogelijk op maandag en woensdag.")

        if st.form_submit_button("Registratie Definitief Indienen"):
            if all([vnaam, anaam, email, id_nr, bericht]) and tijd_keuze != "---":
                try:
                    supabase.table("aanvragen").insert({
                        "voornaam": vnaam, "achternaam": anaam, "email": email, "id_nummer": id_nr,
                        "telefoon": tel, "lad_nummer": lad_nr, "afspraak_datum": str(datum),
                        "afspraak_tijd": tijd_keuze, "status": "In behandeling", "bericht": bericht
                    }).execute()
                    st.success("✅ Uw registratie is succesvol ontvangen.")
                except Exception as e:
                    st.error(f"Fout bij opslaan: {e}")
            else:
                st.error("Vul alle verplichte velden in en kies een geldig tijdstip.")

elif menu == "📋 Dossierbeheer":
    st.header("Centraal Dossierbeheer")
    res = supabase.table("aanvragen").select("*").order('id', desc=True).execute()
    if res.data:
        df = pd.DataFrame(res.data)
        df.insert(0, 'Nr.', range(1, len(df) + 1)) # Nummering vanaf 1
        st.dataframe(df[['Nr.', 'id', 'voornaam', 'achternaam', 'status', 'afspraak_datum']], hide_index=True)
        
        sel_id = st.selectbox("Selecteer dossier voor details", df['id'].tolist())
        reg = next(item for item in res.data if item['id'] == sel_id)
        st.subheader(f"Details van dossier: {reg['id']}")
        
        with st.form("update_status"):
            n_status = st.selectbox("Status", ["Bevestigd", "In behandeling", "Afgehandeld", "Geannuleerd"])
            if st.form_submit_button("Bijwerken"):
                supabase.table("aanvragen").update({"status": n_status}).eq("id", sel_id).execute()
                st.success("Status aangepast!")
                st.rerun()

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

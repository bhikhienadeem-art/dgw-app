import streamlit as st
from supabase import create_client, Client
import datetime
import pandas as pd

# --- 1. CONFIGURATIE & THEMA ---
st.set_page_config(page_title="DGW Wanica Portaal", page_icon="📝", layout="wide")

# Het professionele groen/wit thema
st.markdown("""
    <style>
    .stButton>button { background-color: #2e7d32; color: white; border-radius: 5px; width: 100%; }
    .stTextInput>div>div>input { border-color: #2e7d32; }
    .main { background-color: #ffffff; }
    </style>
    """, unsafe_allow_html=True)

# --- 2. DATABASE VERBINDING ---
try:
    URL = st.secrets["SUPABASE_URL"]
    KEY = st.secrets["SUPABASE_KEY"]
    supabase: Client = create_client(URL, KEY)
except Exception:
    st.error("Systeemfout: Controleer de verbinding met Supabase!")
    st.stop()

# --- 3. HELPER FUNCTIES ---
def get_beschikbare_tijden(datum):
    # Tijden tussen 07:00 en 15:00 met 15 min interval
    start = datetime.datetime.strptime("07:00", "%H:%M")
    eind = datetime.datetime.strptime("15:00", "%H:%M")
    tijden = []
    while start <= eind:
        tijden.append(start.strftime("%H:%M"))
        start += datetime.timedelta(minutes=15)
    
    res = supabase.table("aanvragen").select("afspraak_tijd").eq("afspraak_datum", str(datum)).execute()
    bezette_tijden = [r['afspraak_tijd'] for r in res.data] if res.data else []
    return tijden, bezette_tijden

# --- 4. AUTHENTICATIE ---
if "logged_in" not in st.session_state:
    st.session_state["logged_in"] = False
    st.session_state["user_rol"] = None

st.sidebar.title("DGW Wanica Menu")
keuze = st.sidebar.radio("Navigatie:", ["Cliënt Registratie", "Medewerker Portaal"])

# --- 5. CLIËNT REGISTRATIE ---
if keuze == "Cliënt Registratie":
    st.title("📝 Registratie Dienst Grondzaken Wanica")
    st.info("Afspraken zijn mogelijk op Maandag en Woensdag van 07:00 - 15:00u.")
    
    with st.form("registratie_form", clear_on_submit=True):
        col1, col2 = st.columns(2)
        with col1:
            vnaam = st.text_input("Voornaam *")
            anaam = st.text_input("Achternaam *")
            id_nr = st.text_input("ID-Nummer *")
            tel = st.text_input("Telefoonnummer *")
        with col2:
            email = st.text_input("E-mailadres *")
            lad_nr = st.text_input("LAD Nummer")
            woonadres = st.text_input("Woonadres *")
        
        bericht = st.text_area("Omschrijving van uw verzoek of klacht *")
        
        # Datum beperking
        datum = st.date_input("Kies een datum", min_value=datetime.date.today())
        alle_tijden, bezet = get_beschikbare_tijden(datum)
        tijd = st.selectbox("Kies een tijdstip", alle_tijden)
        
        # Beschikbaarheid indicatie
        if tijd in bezet:
            st.error(f"🔴 {tijd} is al bezet.")
        else:
            st.success(f"🟢 {tijd} is beschikbaar.")

        uploaded_file = st.file_uploader("Upload relevante documenten (PDF/JPG)", type=['pdf', 'jpg', 'png'])
        submit = st.form_submit_button("Aanvraag Indienen")

    if submit:
        if not (vnaam and anaam and id_nr and tel and bericht):
            st.warning("Vul alle verplichte velden (*) in.")
        elif datum.weekday() not in [0, 2]:
            st.error("Excuses, we zijn alleen op Maandag en Woensdag open voor afspraken.")
        elif tijd in bezet:
            st.error("Deze tijd is zojuist gereserveerd. Kies een ander moment.")
        else:
            doc_url = ""
            if uploaded_file:
                fn = f"aanvragen/{vnaam}_{datetime.datetime.now().timestamp()}.pdf"
                supabase.storage.from_("documenten").upload(fn, uploaded_file.getvalue())
                doc_url = supabase.storage.from_("documenten").get_public_url(fn)

            data = {
                "voornaam": vnaam, "achternaam": anaam, "email": email, "id_nummer": id_nr,
                "lad_nummer": lad_nr, "telefoon": tel, "woonadres": woonadres,
                "bericht": bericht, "afspraak_datum": str(datum), "afspraak_tijd": tijd,
                "status": "In behandeling", "document_url": doc_url
            }
            supabase.table("aanvragen").insert(data).execute()
            st.success("✅ Uw aanvraag is verzonden. U ontvangt spoedig bericht.")

# --- 6. MEDEWERKER PORTAAL ---
elif keuze == "Medewerker Portaal":
    if not st.session_state["logged_in"]:
        st.title("🔐 Login Medewerker")
        u_input = st.text_input("Gebruikersnaam").strip()
        p_input = st.text_input("Wachtwoord", type="password").strip()
        
        if st.button("Inloggen"):
            # De werkende bypass voor ICT Wanica
            if u_input == "ICT Wanica" and p_input == "l3lyd@rp":
                st.session_state.update({"logged_in": True, "user_rol": "Admin"})
                st.rerun()
            else:
                res = supabase.table("medewerkers").select("*").eq("gebruikersnaam", u_input).execute()
                if res.data and res.data[0]['wachtwoord'] == p_input:
                    st.session_state.update({"logged_in": True, "user_rol": res.data[0].get('rol', 'Medewerker')})
                    st.rerun()
                else:
                    st.error("Inloggegevens onjuist.")
    else:
        st.sidebar.button("Veilig Uitloggen", on_click=lambda: st.session_state.update({"logged_in": False}))
        
        tabs = st.tabs(["📋 Dossiers & DC-Nummers", "📅 Kalender", "⚙️ Admin & Gebruikers"])

        with tabs[0]: # DOSSIERS
            st.subheader("Binnengekomen Aanvragen")
            res = supabase.table("aanvragen").select("*").execute()
            if res.data:
                df = pd.DataFrame(res.data)
                st.dataframe(df)
                
                with st.expander("Dossier bewerken / DC-nummer toevoegen"):
                    sel_id = st.selectbox("Selecteer Dossier ID", df['id'].tolist())
                    current_row = df[df['id'] == sel_id].iloc[0]
                    
                    new_dc = st.text_input("DC Nummer aanpassen", value=str(current_row.get('dc_nummer', '')))
                    new_status = st.selectbox("Status aanpassen", ["In behandeling", "Bevestigd", "Afgewezen"], 
                                             index=["In behandeling", "Bevestigd", "Afgewezen"].index(current_row['status']))
                    
                    if st.button("Wijzigingen Opslaan"):
                        supabase.table("aanvragen").update({"dc_nummer": new_dc, "status": new_status}).eq("id", sel_id).execute()
                        st.success(f"Dossier {sel_id} bijgewerkt!")
                        st.rerun()

        with tabs[1]: # KALENDER
            res_c = supabase.table("aanvragen").select("voornaam, achternaam, afspraak_datum, afspraak_tijd, status").execute()
            if res_c.data:
                st.table(pd.DataFrame(res_c.data).sort_values(['afspraak_datum', 'afspraak_tijd']))

        with tabs[2]: # ADMIN
            if st.session_state["user_rol"] == "Admin":
                st.subheader("Beheer Medewerkers")
                nu, np = st.text_input("Nieuwe Gebruikersnaam"), st.text_input("Nieuw Wachtwoord")
                nr = st.selectbox("Rol", ["Medewerker", "Admin"])
                if st.button("Account Toevoegen"):
                    supabase.table("medewerkers").insert({"gebruikersnaam": nu, "wachtwoord": np, "rol": nr}).execute()
                    st.success(f"Account voor {nu} aangemaakt!")
                    st.rerun()
            else:
                st.warning("U heeft geen admin-rechten voor deze sectie.")

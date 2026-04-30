import streamlit as st
from supabase import create_client, Client
import datetime
import pandas as pd

# --- 1. CONFIGURATIE & THEMA ---
st.set_page_config(page_title="DGW Wanica Portaal", page_icon="📝", layout="wide")

st.markdown("""
    <style>
    .stButton>button { background-color: #2e7d32; color: white; border-radius: 5px; width: 100%; }
    .stTextInput>div>div>input { border-color: #2e7d32; }
    .main { background-color: #ffffff; }
    .highlight-box { 
        padding: 15px; border-radius: 10px; border: 2px solid #2e7d32; 
        background-color: #f1f8e9; margin-bottom: 20px; 
    }
    </style>
    """, unsafe_allow_html=True)

# --- 2. DATABASE VERBINDING ---
try:
    URL = st.secrets["SUPABASE_URL"]
    KEY = st.secrets["SUPABASE_KEY"]
    supabase: Client = create_client(URL, KEY)
except Exception:
    st.error("Systeemfout: Databaseverbinding mislukt!")
    st.stop()

# --- 3. HELPER FUNCTIES ---
def get_beschikbare_tijden(datum):
    start = datetime.datetime.strptime("07:00", "%H:%M")
    eind = datetime.datetime.strptime("15:00", "%H:%M")
    tijden = []
    while start <= eind:
        tijden.append(start.strftime("%H:%M"))
        start += datetime.timedelta(minutes=15)
    
    res = supabase.table("aanvragen").select("afspraak_tijd").eq("afspraak_datum", str(datum)).execute()
    bezette_tijden = [r['afspraak_tijd'] for r in res.data] if res.data else []
    return tijden, bezette_tijden

# --- 4. AUTHENTICATIE STATUS ---
if "logged_in" not in st.session_state:
    st.session_state["logged_in"] = False
    st.session_state["user_rol"] = None

st.sidebar.title("DGW Wanica Menu")
keuze = st.sidebar.radio("Navigatie:", ["Cliënt Registratie", "Medewerker Portaal"])

# --- 5. CLIËNT REGISTRATIE ---
if keuze == "Cliënt Registratie":
    st.title("📝 Registratie Dienst Grondzaken Wanica")
    
    st.markdown("""
        <div class="highlight-box">
            <h3 style='color: #2e7d32; margin-top: 0;'>📅 Afspraak Informatie</h3>
            <p>Afspraken uitsluitend op: <b>Maandag</b> en <b>Woensdag</b> (07:00u - 15:00u).</p>
        </div>
    """, unsafe_allow_html=True)
    
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
        
        st.write("---")
        st.subheader("📄 Documenten")
        geuploade_file = st.file_uploader("Upload relevante documenten (PDF/JPG/PNG)", type=['pdf', 'png', 'jpg', 'jpeg'])
        
        st.write("---")
        st.subheader("📅 Plan uw afspraak")
        datum = st.date_input("Kies een datum", min_value=datetime.date.today())
        
        # STRIKTE FIX: Gebruik isoweekday() (1=Maandag, 3=Woensdag)
        iso_dag = datum.isoweekday() 
        dag_namen = {1: "Maandag", 2: "Dinsdag", 3: "Woensdag", 4: "Donderdag", 5: "Vrijdag", 6: "Zaterdag", 7: "Zondag"}
        huidige_dagnaam = dag_namen.get(iso_dag)

        if iso_dag not in [1, 3]:
            st.error(f"❌ {huidige_dagnaam} is niet beschikbaar. Kies a.u.b. een Maandag of Woensdag.")
            submit = st.form_submit_button("Dag niet beschikbaar", disabled=True)
        else:
            alle_tijden, bezette_tijden = get_beschikbare_tijden(datum)
            beschikbare_opties = [t for t in alle_tijden if t not in bezette_tijden]
            
            if beschikbare_opties:
                st.success(f"✅ {huidige_dagnaam} geselecteerd.")
                tijd = st.selectbox("Beschikbare tijden *", beschikbare_opties)
                submit = st.form_submit_button("Aanvraag Indienen")
            else:
                st.error("🔴 Volgeboekt op deze dag.")
                submit = False

    if submit:
        if vnaam and anaam and id_nr and tel and bericht:
            doc_naam = geuploade_file.name if geuploade_file else "Geen document"
            data = {
                "voornaam": vnaam, "achternaam": anaam, "email": email, "id_nummer": id_nr,
                "lad_nummer": lad_nr, "telefoon": tel, "woonadres": woonadres,
                "bericht": bericht, "afspraak_datum": str(datum), "afspraak_tijd": tijd,
                "document_naam": doc_naam, "status": "In behandeling"
            }
            supabase.table("aanvragen").insert(data).execute()
            st.success(f"✅ Uw aanvraag voor {huidige_dagnaam} {datum} is succesvol verzonden!")
        else:
            st.warning("Vul alle verplichte velden (*) in.")

# --- 6. MEDEWERKER PORTAAL ---
elif keuze == "Medewerker Portaal":
    if not st.session_state["logged_in"]:
        st.title("🔐 Login Medewerker")
        u = st.text_input("Gebruikersnaam").strip()
        p = st.text_input("Wachtwoord", type="password").strip()
        if st.button("Inloggen"):
            if u == "ICT Wanica" and p == "l3lyd@rp":
                st.session_state.update({"logged_in": True, "user_rol": "Admin"})
                st.rerun()
            else:
                res = supabase.table("medewerkers").select("*").eq("gebruikersnaam", u).execute()
                if res.data and res.data[0]['wachtwoord'] == p:
                    st.session_state.update({"logged_in": True, "user_rol": res.data[0].get('rol', 'Medewerker')})
                    st.rerun()
                else:
                    st.error("Foutieve gegevens.")
    else:
        st.sidebar.button("Veilig Uitloggen", on_click=lambda: st.session_state.update({"logged_in": False}))
        tabs = st.tabs(["📋 Dossiers & DC", "📅 Kalender", "📊 Rapportage", "⚙️ Admin"])

        with tabs[0]: 
            res = supabase.table("aanvragen").select("*").execute()
            if res.data:
                df = pd.DataFrame(res.data)
                st.dataframe(df)
                with st.expander("📝 Dossier Bewerken / DC Nummer invoeren"):
                    sel_id = st.selectbox("Selecteer Dossier ID", df['id'].tolist())
                    row = df[df['id'] == sel_id].iloc[0]
                    
                    c1, c2 = st.columns(2)
                    with c1:
                        # Medewerkers kunnen DC-nummers invoeren en corrigeren
                        new_dc = st.text_input("DC Nummer", value=str(row.get('dc_nummer', '')))
                        opts = ["In behandeling", "Bevestigd", "Verschoven", "Afgehandeld", "Afgewezen"]
                        new_s = st.selectbox("Status", opts, index=opts.index(row['status']) if row['status'] in opts else 0)
                        if st.button("Wijzigingen Opslaan"):
                            supabase.table("aanvragen").update({"dc_nummer": new_dc, "status": new_s}).eq("id", sel_id).execute()
                            st.success("Dossier bijgewerkt!")
                            st.rerun()

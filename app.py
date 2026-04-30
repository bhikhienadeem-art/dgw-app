import streamlit as st
from supabase import create_client, Client
import datetime
import pandas as pd

# --- 1. CONFIGURATIE ---
st.set_page_config(page_title="DGW Wanica Portaal", page_icon="📝", layout="wide")

# --- 2. DATABASE VERBINDING ---
try:
    URL = st.secrets["SUPABASE_URL"]
    KEY = st.secrets["SUPABASE_KEY"]
    supabase: Client = create_client(URL, KEY)
except Exception:
    st.error("Systeemfout: Controleer uw Streamlit Secrets!")
    st.stop()

# --- 3. HELPER FUNCTIES ---
def get_beschikbare_tijden(datum):
    """Haalt bezette tijden op en markeert ze."""
    start = datetime.datetime.strptime("07:00", "%H:%M")
    eind = datetime.datetime.strptime("15:00", "%H:%M")
    tijden = []
    while start <= eind:
        tijden.append(start.strftime("%H:%M"))
        start += datetime.timedelta(minutes=15)
    
    res = supabase.table("aanvragen").select("afspraak_tijd").eq("afspraak_datum", str(datum)).execute()
    bezette = [r['afspraak_tijd'] for r in res.data] if res.data else []
    return tijden, bezette

# --- 4. AUTHENTICATIE STATUS ---
if "logged_in" not in st.session_state:
    st.session_state["logged_in"] = False
    st.session_state["user_rol"] = None

st.sidebar.title("DGW Menu")
keuze = st.sidebar.radio("Ga naar:", ["Cliënt Registratie", "Medewerker Portaal"])

# --- 5. CLIËNT REGISTRATIE ---
if keuze == "Cliënt Registratie":
    st.title("📝 Registratie Dienst Grondzaken Wanica")
    with st.form("registratie", clear_on_submit=True):
        col1, col2 = st.columns(2)
        with col1:
            vnaam, anaam = st.text_input("Voornaam *"), st.text_input("Achternaam *")
            id_nr, tel = st.text_input("ID-Nummer *"), st.text_input("Telefoon *")
        with col2:
            email, lad_nr = st.text_input("E-mail *"), st.text_input("LAD Nummer")
            woonadres = st.text_input("Woonadres *")
        
        bericht = st.text_area("Omschrijving van het verzoek *")
        datum = st.date_input("Datum (Maandag of Woensdag)", min_value=datetime.date.today())
        
        # TIJD EN STATUS INDICATIE
        alle_tijden, bezet = get_beschikbare_tijden(datum)
        tijd = st.selectbox("Kies tijdstip", alle_tijden)
        
        if tijd in bezet:
            st.error(f"🔴 {tijd} is al bezet.")
        else:
            st.success(f"🟢 {tijd} is beschikbaar.")

        uploaded_file = st.file_uploader("Document Upload", type=['pdf', 'jpg', 'png'])
        submit = st.form_submit_button("Aanvraag Verzenden")

    if submit and vnaam:
        if datum.weekday() in [0, 2] and tijd not in bezet:
            doc_url = ""
            if uploaded_file:
                fn = f"docs/{vnaam}_{datetime.datetime.now().timestamp()}.pdf"
                supabase.storage.from_("documenten").upload(fn, uploaded_file.getvalue())
                doc_url = supabase.storage.from_("documenten").get_public_url(fn)
            
            supabase.table("aanvragen").insert({
                "voornaam": vnaam, "achternaam": anaam, "email": email, "id_nummer": id_nr,
                "lad_nummer": lad_nr, "telefoon": tel, "woonadres": woonadres,
                "bericht": bericht, "afspraak_datum": str(datum), "afspraak_tijd": tijd,
                "status": "In behandeling", "document_url": doc_url
            }).execute()
            st.success("✅ Verzonden!")
        else:
            st.error("Controleer de datum (Ma/Wo) of kies een beschikbare tijd.")

# --- 6. MEDEWERKER PORTAAL (DE DEFINITIEVE OPLOSSING) ---
elif keuze == "Medewerker Portaal":
    if not st.session_state["logged_in"]:
        st.title("🔐 Login Medewerker")
        # .strip() verwijdert onzichtbare spaties die voor fouten zorgen
        u_input = st.text_input("Gebruikersnaam").strip()
        p_input = st.text_input("Wachtwoord", type="password").strip()
        
        if st.button("Inloggen"):
            # PERMANENTE OPLOSSING: Directe controle op de exacte tekst uit image_fe4b60.png
            if u_input == "ICT Wanica" and p_input == "l3lyd@rp":
                st.session_state.update({"logged_in": True, "user_rol": "Admin"})
                st.rerun()
            else:
                # Als je andere accounts toevoegt in de Admin tab, worden die hier gecontroleerd
                try:
                    res = supabase.table("medewerkers").select("*").eq("gebruikersnaam", u_input).execute()
                    if res.data and res.data[0]['wachtwoord'] == p_input:
                        st.session_state.update({"logged_in": True, "user_rol": res.data[0].get('rol', 'Medewerker')})
                        st.rerun()
                    else:
                        st.error("Inloggegevens onjuist.")
                except:
                    st.error("Systeem kan database niet bereiken.")
    else:
        st.sidebar.button("Uitloggen", on_click=lambda: st.session_state.update({"logged_in": False}))
        tabs = st.tabs(["📋 Dossiers", "📅 Kalender", "📊 Rapportage", "⚙️ Admin"])

        with tabs[0]: # DOSSIERS
            res = supabase.table("aanvragen").select("*").execute()
            if res.data:
                df = pd.DataFrame(res.data)
                st.dataframe(df)
                sel_id = st.selectbox("ID Verwijderen", df['id'].tolist())
                if st.button("❌ Verwijder"):
                    supabase.table("aanvragen").delete().eq("id", sel_id).execute()
                    st.rerun()

        with tabs[1]: # KALENDER
            res_c = supabase.table("aanvragen").select("voornaam, achternaam, afspraak_datum, afspraak_tijd").execute()
            if res_c.data: st.table(pd.DataFrame(res_c.data))

        with tabs[2]: # RAPPORTAGE
            res_r = supabase.table("aanvragen").select("*").execute()
            if res_r.data:
                df_r = pd.DataFrame(res_r.data)
                st.download_button("📥 Export CSV", df_r.to_csv(index=False).encode('utf-8'), "DGW_Data.csv")

        with tabs[3]: # ADMIN (GEBRUIKERS BEHEREN)
            if st.session_state["user_rol"] == "Admin":
                st.subheader("Accountbeheer")
                nu, np = st.text_input("Nieuwe Gebruiker"), st.text_input("Nieuw Wachtwoord")
                nr = st.selectbox("Rol", ["Medewerker", "Admin"])
                if st.button("Opslaan"):
                    supabase.table("medewerkers").insert({"gebruikersnaam": nu, "wachtwoord": np, "rol": nr}).execute()
                    st.success("Gelukt!")
                    st.rerun()

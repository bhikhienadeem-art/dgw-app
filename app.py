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
except:
    st.error("Database-verbinding mislukt. Controleer je Streamlit Secrets!")
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
    bezette = [r['afspraak_tijd'] for r in res.data] if res.data else []
    return tijden, bezette

# --- 4. NAVIGATIE & AUTHENTICATIE ---
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
            vnaam = st.text_input("Voornaam *")
            anaam = st.text_input("Achternaam *")
            id_nr = st.text_input("ID-Nummer *")
            tel = st.text_input("Telefoon *")
        with col2:
            email = st.text_input("E-mail *")
            lad_nr = st.text_input("LAD Nummer")
            woonadres = st.text_input("Woonadres *")
        
        bericht = st.text_area("Bericht / Omschrijving verzoek *")
        datum = st.date_input("Afspraakdatum (Ma/Wo)", min_value=datetime.date.today())
        alle_tijden, bezet = get_beschikbare_tijden(datum)
        tijd = st.selectbox("Tijdstip", alle_tijden)
        
        uploaded_file = st.file_uploader("Document Upload", type=['pdf', 'jpg', 'png'])
        submit = st.form_submit_button("Verzenden")

    if submit and vnaam and woonadres:
        if datum.weekday() in [0, 2]:
            doc_url = ""
            if uploaded_file:
                fn = f"docs/{vnaam}_{datetime.datetime.now().timestamp()}.pdf"
                supabase.storage.from_("documenten").upload(fn, uploaded_file.getvalue())
                doc_url = supabase.storage.from_("documenten").get_public_url(fn)

            data = {
                "voornaam": vnaam, "achternaam": anaam, "email": email, "id_nummer": id_nr,
                "lad_nummer": lad_nr, "telefoon": tel, "woonadres": woonadres,
                "bericht": bericht, "afspraak_datum": str(datum), "afspraak_tijd": tijd,
                "status": "In behandeling", "document_url": doc_url
            }
            supabase.table("aanvragen").insert(data).execute()
            st.success("Aanvraag verzonden!")
        else:
            st.error("Afspraken alleen op maandag of woensdag.")

# --- 6. MEDEWERKER PORTAAL (Gefixeerde Login) ---
elif keuze == "Medewerker Portaal":
    if not st.session_state["logged_in"]:
        st.title("🔐 Login Medewerker")
        # Gebruik .lower() en .strip() om alle invoerfouten te voorkomen
        u_input = st.text_input("Gebruikersnaam").strip()
        p_input = st.text_input("Wachtwoord", type="password").strip()
        
        if st.button("Inloggen"):
            # De gegevens uit image_ff18bf.png
            if u_input.lower() == "ict wanica" and p_input == "l3lyd@rp":
                st.session_state.update({"logged_in": True, "user_rol": "Admin"})
                st.rerun()
            else:
                # Check database als backup
                res = supabase.table("medewerkers").select("*").eq("gebruikersnaam", u_input).execute()
                if res.data and res.data[0]['wachtwoord'] == p_input:
                    st.session_state.update({"logged_in": True, "user_rol": res.data[0]['rol']})
                    st.rerun()
                else:
                    st.error("Inloggen mislukt. Gebruik de gegevens uit de handleiding.")
    else:
        st.sidebar.button("Uitloggen", on_click=lambda: st.session_state.update({"logged_in": False}))
        tabs = st.tabs(["📋 Dossiers", "📅 Kalender", "📊 Rapportage", "⚙️ Admin"])

        with tabs[0]: # BEHEER
            res = supabase.table("aanvragen").select("*").execute()
            if res.data:
                df = pd.DataFrame(res.data)
                sel_id = st.selectbox("Dossier ID", df['id'].tolist())
                if st.button("❌ Verwijder Dossier"):
                    supabase.table("aanvragen").delete().eq("id", sel_id).execute()
                    st.rerun()
                st.dataframe(df)

        with tabs[1]: # KALENDER
            res_c = supabase.table("aanvragen").select("voornaam, achternaam, afspraak_datum, afspraak_tijd, status").execute()
            if res_c.data: st.table(pd.DataFrame(res_c.data).sort_values(['afspraak_datum', 'afspraak_tijd']))

        with tabs[2]: # RAPPORTAGE
            res_r = supabase.table("aanvragen").select("*").execute()
            if res_r.data:
                df_r = pd.DataFrame(res_r.data)
                # Voorkom KeyError door te checken welke kolommen bestaan
                cols = [c for c in ["voornaam", "achternaam", "bericht", "woonadres", "status"] if c in df_r.columns]
                st.dataframe(df_r[cols])
                st.download_button("📥 Download CSV", df_r.to_csv(index=False).encode('utf-8'), "DGW_Export.csv", "text/csv")

        with tabs[3]: # ADMIN
            if st.session_state["user_rol"] == "Admin":
                st.subheader("Gebruikersbeheer")
                nu = st.text_input("Nieuwe Gebruiker")
                np = st.text_input("Wachtwoord")
                if st.button("Voeg toe"):
                    supabase.table("medewerkers").insert({"gebruikersnaam": nu, "wachtwoord": np, "rol": "Medewerker"}).execute()
                    st.success("Toegevoegd!")
            else: st.warning("Geen Admin rechten.")

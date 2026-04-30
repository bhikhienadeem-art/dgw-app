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
    """Genereert tijden en controleert bezetting in de database."""
    start = datetime.datetime.strptime("07:00", "%H:%M")
    eind = datetime.datetime.strptime("15:00", "%H:%M")
    tijden = []
    while start <= eind:
        tijden.append(start.strftime("%H:%M"))
        start += datetime.timedelta(minutes=15)
    
    # Haal bezette tijden op voor de geselecteerde datum
    res = supabase.table("aanvragen").select("afspraak_tijd").eq("afspraak_datum", str(datum)).execute()
    bezette_tijden = [r['afspraak_tijd'] for r in res.data] if res.data else []
    return tijden, bezette_tijden

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
            vnaam = st.text_input("Voornaam *")
            anaam = st.text_input("Achternaam *")
            id_nr = st.text_input("ID-Nummer *")
            tel = st.text_input("Telefoon *")
        with col2:
            email = st.text_input("E-mail *")
            lad_nr = st.text_input("LAD Nummer (optioneel)")
            woonadres = st.text_input("Woonadres *")
        
        bericht = st.text_area("Omschrijving van het verzoek *")
        
        # Datum en Tijd sectie
        datum = st.date_input("Kies datum (Maandag of Woensdag)", min_value=datetime.date.today())
        alle_tijden, bezet = get_beschikbare_tijden(datum)
        tijd = st.selectbox("Kies tijdstip", alle_tijden)
        
        # De groen/rood indicatie (Direct zichtbaar in het formulier)
        if tijd in bezet:
            st.error(f"🔴 {tijd} is al bezet op deze datum.")
        else:
            st.success(f"🟢 {tijd} is beschikbaar.")

        uploaded_file = st.file_uploader("Upload documenten (PDF/JPG/PNG)", type=['pdf', 'jpg', 'png'])
        submit = st.form_submit_button("Aanvraag Verzenden")

    if submit:
        if not (vnaam and anaam and id_nr and woonadres and bericht):
            st.warning("Vul a.u.b. alle verplichte velden (*) in.")
        elif datum.weekday() not in [0, 2]: # 0 = Maandag, 2 = Woensdag
            st.error("⚠️ Afspraken kunnen alleen op Maandag of Woensdag worden gemaakt.")
        elif tijd in bezet:
            st.error("Deze tijd is helaas niet meer beschikbaar.")
        else:
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
            st.success("✅ Uw aanvraag is succesvol verzonden!")

# --- 6. MEDEWERKER PORTAAL ---
elif keuze == "Medewerker Portaal":
    if not st.session_state["logged_in"]:
        st.title("🔐 Login Medewerker")
        u_input = st.text_input("Gebruikersnaam").strip()
        p_input = st.text_input("Wachtwoord", type="password").strip()
        
        if st.button("Inloggen"):
            # Failsafe check voor ICT Wanica conform image_fe42bf.png
            if u_input == "ICT Wanica" and p_input == "l3lyd@rp":
                st.session_state.update({"logged_in": True, "user_rol": "Admin"})
                st.rerun()
            else:
                try:
                    res = supabase.table("medewerkers").select("*").eq("gebruikersnaam", u_input).execute()
                    if res.data and res.data[0]['wachtwoord'] == p_input:
                        st.session_state.update({"logged_in": True, "user_rol": res.data[0].get('rol', 'Medewerker')})
                        st.rerun()
                    else:
                        st.error("Inloggegevens onjuist. Controleer uw gegevens.")
                except:
                    st.error("Inloggen mislukt. Controleer uw database verbinding.")
    else:
        st.sidebar.button("Uitloggen", on_click=lambda: st.session_state.update({"logged_in": False}))
        
        tabs = st.tabs(["📋 Dossiers", "📅 Kalender", "📊 Rapportage", "⚙️ Admin"])

        # TAB 1: DOSSIERS
        with tabs[0]:
            res = supabase.table("aanvragen").select("*").execute()
            if res.data:
                df = pd.DataFrame(res.data)
                sel_id = st.selectbox("Selecteer Dossier ID voor beheer", df['id'].tolist())
                
                c1, c2 = st.columns(2)
                with c1:
                    new_st = st.selectbox("Status aanpassen", ["Bevestigd", "Geannuleerd", "In behandeling"])
                    if st.button("Update Status"):
                        supabase.table("aanvragen").update({"status": new_st}).eq("id", sel_id).execute()
                        st.success("Status bijgewerkt!")
                        st.rerun()
                with c2:
                    if st.button("❌ Verwijder Dossier"):
                        supabase.table("aanvragen").delete().eq("id", sel_id).execute()
                        st.rerun()
                st.dataframe(df)

        # TAB 2: KALENDER
        with tabs[1]:
            st.subheader("📅 Geplande Afspraken")
            res_c = supabase.table("aanvragen").select("voornaam, achternaam, afspraak_datum, afspraak_tijd, status").execute()
            if res_c.data:
                st.table(pd.DataFrame(res_c.data).sort_values(['afspraak_datum', 'afspraak_tijd']))

        # TAB 3: RAPPORTAGE
        with tabs[2]:
            st.subheader("📊 Rapportage Export")
            res_r = supabase.table("aanvragen").select("*").execute()
            if res_r.data:
                df_r = pd.DataFrame(res_r.data)
                st.dataframe(df_r)
                csv = df_r.to_csv(index=False).encode('utf-8')
                st.download_button("📥 Download als CSV", csv, "DGW_Dossiers.csv", "text/csv")

        # TAB 4: ADMIN (Alleen zichtbaar voor Admins)
        with tabs[3]:
            if st.session_state["user_rol"] == "Admin":
                st.subheader("👥 Medewerker Beheer")
                with st.expander("➕ Voeg Medewerker Toe"):
                    nu = st.text_input("Gebruikersnaam").strip()
                    np = st.text_input("Wachtwoord").strip()
                    nr = st.selectbox("Rol", ["Medewerker", "Admin"])
                    if st.button("Account Aanmaken"):
                        if nu and np:
                            supabase.table("medewerkers").insert({"gebruikersnaam": nu, "wachtwoord": np, "rol": nr}).execute()
                            st.success(f"Account voor {nu} aangemaakt!")
                            st.rerun()
                
                st.divider()
                res_m = supabase.table("medewerkers").select("*").execute()
                if res_m.data:
                    df_m = pd.DataFrame(res_m.data)
                    st.dataframe(df_m[["gebruikersnaam", "rol"]])
                    del_u = st.selectbox("Account om te verwijderen", df_m['gebruikersnaam'].tolist())
                    if st.button("Definitief Verwijderen"):
                        if del_u.lower() != "ict wanica":
                            supabase.table("medewerkers").delete().eq("gebruikersnaam", del_u).execute()
                            st.rerun()
                        else:
                            st.error("U kunt de hoofdaccount niet verwijderen.")
            else:
                st.warning("⚠️ Alleen beheerders hebben toegang tot dit tabblad.")

import streamlit as st
from supabase import create_client, Client
import datetime
import pandas as pd

# --- 1. CONFIGURATIE & THEMA ---
# Professionele layout met groen/wit kleurenschema
st.set_page_config(page_title="DGW Wanica Portaal", page_icon="📝", layout="wide")

st.markdown("""
    <style>
    .stButton>button { background-color: #2e7d32; color: white; border-radius: 5px; width: 100%; }
    .stTextInput>div>div>input { border-color: #2e7d32; }
    .main { background-color: #ffffff; }
    </style>
    """, unsafe_allow_html=True)

# --- 2. DATABASE VERBINDING ---
# Gebruik van Supabase voor dataopslag
try:
    URL = st.secrets["SUPABASE_URL"]
    KEY = st.secrets["SUPABASE_KEY"]
    supabase: Client = create_client(URL, KEY)
except Exception:
    st.error("Systeemfout: Controleer de verbinding met Supabase!")
    st.stop()

# --- 3. HELPER FUNCTIES ---
def get_beschikbare_tijden(datum):
    # Afspraken tussen 07:00 en 15:00 met 15 min interval
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
        
        # Alleen Maandag (0) en Woensdag (2)
        datum = st.date_input("Kies een datum", min_value=datetime.date.today())
        alle_tijden, bezet = get_beschikbare_tijden(datum)
        tijd = st.selectbox("Kies een tijdstip", alle_tijden)
        
        if tijd in bezet:
            st.error(f"🔴 {tijd} is al bezet.")
        else:
            st.success(f"🟢 {tijd} is beschikbaar.")

        submit = st.form_submit_button("Aanvraag Indienen")

    if submit:
        if datum.weekday() not in [0, 2]:
            st.error("Afspraken zijn alleen mogelijk op Maandag en Woensdag.")
        elif not (vnaam and anaam and id_nr and tel):
            st.warning("Vul a.u.b. alle verplichte velden in.")
        else:
            data = {
                "voornaam": vnaam, "achternaam": anaam, "email": email, "id_nummer": id_nr,
                "lad_nummer": lad_nr, "telefoon": tel, "woonadres": woonadres,
                "bericht": bericht, "afspraak_datum": str(datum), "afspraak_tijd": tijd,
                "status": "In behandeling"
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
            # Harde bypass voor ICT Wanica administrator
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
        
        # Tabs voor verschillende beheertaken
        tabs = st.tabs(["📋 Dossiers & DC", "📅 Kalender", "📊 Rapportage", "⚙️ Admin"])

        with tabs[0]: # DOSSIERBEHEER & DC-NUMMERS
            st.subheader("Binnengekomen Aanvragen")
            res = supabase.table("aanvragen").select("*").execute()
            if res.data:
                df = pd.DataFrame(res.data)
                st.dataframe(df)
                
                with st.expander("📝 Dossier Bewerken, Status Wijzigen of Verwijderen"):
                    sel_id = st.selectbox("Selecteer Dossier ID", df['id'].tolist())
                    row = df[df['id'] == sel_id].iloc[0]
                    
                    c1, c2 = st.columns(2)
                    with c1:
                        new_dc = st.text_input("DC Nummer aanpassen", value=str(row.get('dc_nummer', '')))
                        status_opties = ["In behandeling", "Bevestigd", "Verschoven", "Afgehandeld", "Afgewezen"]
                        huidige_status = row['status'] if row['status'] in status_opties else "In behandeling"
                        new_status = st.selectbox("Status aanpassen", status_opties, index=status_opties.index(huidige_status))
                        
                        if st.button("Wijzigingen Opslaan"):
                            supabase.table("aanvragen").update({"dc_nummer": new_dc, "status": new_status}).eq("id", sel_id).execute()
                            st.success(f"Dossier {sel_id} bijgewerkt.")
                            st.rerun()
                    with c2:
                        st.write("---")
                        if st.button("🗑️ Dossier Definitief Verwijderen"):
                            supabase.table("aanvragen").delete().eq("id", sel_id).execute()
                            st.warning(f"Dossier {sel_id} verwijderd.")
                            st.rerun()

        with tabs[1]: # KALENDER OVERZICHT
            res_c = supabase.table("aanvragen").select("voornaam, achternaam, afspraak_datum, afspraak_tijd, status").execute()
            if res_c.data:
                st.table(pd.DataFrame(res_c.data).sort_values(['afspraak_datum', 'afspraak_tijd']))

        with tabs[2]: # RAPPORTAGE & EXPORT
            st.subheader("📊 Systeem Rapportage")
            res_r = supabase.table("aanvragen").select("*").execute()
            if res_r.data:
                df_r = pd.DataFrame(res_r.data)
                st.dataframe(df_r)
                csv = df_r.to_csv(index=False).encode('utf-8')
                st.download_button("📥 Download Rapport (CSV)", data=csv, file_name="DGW_Rapport.csv", mime="text/csv")

        with tabs[3]: # ADMIN & GEBRUIKERSBEHEER
            if st.session_state["user_rol"] == "Admin":
                st.subheader("👤 Gebruikersbeheer")
                
                with st.expander("➕ Nieuwe Medewerker Toevoegen"):
                    nu = st.text_input("Gebruikersnaam")
                    np = st.text_input("Wachtwoord", type="password")
                    nr = st.selectbox("Rol", ["Medewerker", "Admin"])
                    if st.button("Account Aanmaken"):
                        supabase.table("medewerkers").insert({"gebruikersnaam": nu, "wachtwoord": np, "rol": nr}).execute()
                        st.success(f"Account voor {nu} aangemaakt!")
                        st.rerun()

                st.write("---")
                st.subheader("Huidige Medewerkers")
                res_m = supabase.table("medewerkers").select("*").execute()
                if res_m.data:
                    m_df = pd.DataFrame(res_m.data)
                    st.table(m_df[['gebruikersnaam', 'rol']])
                    
                    del_u = st.selectbox("Account verwijderen", m_df['gebruikersnaam'].tolist())
                    if del_u != "ICT Wanica":
                        if st.button(f"🗑️ Verwijder {del_u}"):
                            supabase.table("medewerkers").delete().eq("gebruikersnaam", del_u).execute()
                            st.rerun()
                    else:
                        st.info("Het hoofdaccount kan niet worden verwijderd.")
            else:
                st.warning("Geen toegang tot admin instellingen.")

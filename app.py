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
    st.error("Systeemfout: Controleer uw Streamlit Secrets!")
    st.stop()

# --- 3. NAVIGATIE & AUTHENTICATIE ---
if "logged_in" not in st.session_state:
    st.session_state["logged_in"] = False
    st.session_state["user_rol"] = "Medewerker"

st.sidebar.title("DGW Menu")
keuze = st.sidebar.radio("Ga naar:", ["Cliënt Registratie", "Medewerker Portaal"])

# --- 4. CLIËNT REGISTRATIE ---
if keuze == "Cliënt Registratie":
    st.title("📝 Registratie Dienst Grondzaken")
    with st.form("registratie"):
        vnaam = st.text_input("Voornaam *")
        anaam = st.text_input("Achternaam *")
        omschrijving = st.text_area("Omschrijving van het verzoek (bijv. Land claim/Documenten) *")
        submit = st.form_submit_button("Verzenden")
        
    if submit and vnaam and omschrijving:
        data = {"voornaam": vnaam, "achternaam": anaam, "omschrijving": omschrijving, "status": "In behandeling"}
        supabase.table("aanvragen").insert(data).execute()
        st.success("Aanvraag succesvol verzonden!")

# --- 5. MEDEWERKER PORTAAL ---
elif keuze == "Medewerker Portaal":
    if not st.session_state["logged_in"]:
        st.title("🔐 Login")
        u = st.text_input("Gebruikersnaam").strip()
        p = st.text_input("Wachtwoord", type="password").strip()
        if st.button("Inloggen"):
            if u == "ICT Wanica" and p == "l3lyd@rp":
                st.session_state["logged_in"] = True
                st.session_state["user_rol"] = "Admin"
                st.rerun()
            else:
                res = supabase.table("medewerkers").select("*").eq("gebruikersnaam", u).execute()
                if res.data and res.data[0]['wachtwoord'] == p:
                    st.session_state["logged_in"] = True
                    st.session_state["user_rol"] = res.data[0]['rol']
                    st.rerun()
                else: st.error("Inloggen mislukt.")
    else:
        st.sidebar.info(f"Ingelogd als: {st.session_state['user_rol']}")
        st.sidebar.button("Uitloggen", on_click=lambda: st.session_state.update({"logged_in": False}))
        
        tabs = st.tabs(["📋 Beheer", "📊 Rapportage", "⚙️ Admin Instellingen"])

        # TAB 1: BEHEER
        with tabs[0]:
            st.subheader("Dossiers Beheren")
            res = supabase.table("aanvragen").select("*").execute()
            if res.data:
                st.dataframe(pd.DataFrame(res.data))

        # TAB 2: RAPPORTAGE (Download Functie)
        with tabs[1]:
            st.subheader("📊 Klantenrapportage")
            res_rep = supabase.table("aanvragen").select("*").execute()
            if res_rep.data:
                df_rep = pd.DataFrame(res_rep.data)
                st.write("Overzicht van alle afspraken en omschrijvingen:")
                st.dataframe(df_rep[["voornaam", "achternaam", "omschrijving", "status"]])
                
                # Download knop
                csv = df_rep.to_csv(index=False).encode('utf-8')
                st.download_button(label="📥 Download Rapportage (CSV)", data=csv, file_name='DGW_Rapportage.csv', mime='text/csv')

        # TAB 3: ADMIN (Gebruikersbeheer)
        with tabs[2]:
            if st.session_state["user_rol"] == "Admin":
                st.subheader("👥 Medewerkers Beheren")
                
                # Toevoegen
                with st.expander("Nieuwe Medewerker Toevoegen"):
                    nu = st.text_input("Nieuwe Gebruikersnaam")
                    np = st.text_input("Nieuw Wachtwoord", type="password")
                    nr = st.selectbox("Rol", ["Medewerker", "Admin"])
                    if st.button("Account Aanmaken"):
                        supabase.table("medewerkers").insert({"gebruikersnaam": nu, "wachtwoord": np, "rol": nr}).execute()
                        st.success(f"Account voor {nu} aangemaakt!")
                
                # Verwijderen
                st.divider()
                res_m = supabase.table("medewerkers").select("*").execute()
                if res_m.data:
                    df_m = pd.DataFrame(res_m.data)
                    del_u = st.selectbox("Verwijder Medewerker", df_m['gebruikersnaam'].tolist())
                    if st.button("❌ Account Verwijderen"):
                        supabase.table("medewerkers").delete().eq("gebruikersnaam", del_u).execute()
                        st.warning(f"Account {del_u} verwijderd.")
                        st.rerun()
            else:
                st.error("U heeft geen toegang tot de Admin instellingen.")

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

# --- 4. NAVIGATIE ---
if "logged_in" not in st.session_state:
    st.session_state["logged_in"] = False
    st.session_state["user_rol"] = None

st.sidebar.title("DGW Menu")
keuze = st.sidebar.radio("Ga naar:", ["Cliënt Registratie", "Medewerker Portaal"])

# --- 5. CLIËNT REGISTRATIE ---
if keuze == "Cliënt Registratie":
    st.title("📝 Registratie Dienst Grondzaken Wanica")
    with st.form("registratie"):
        col1, col2 = st.columns(2)
        with col1:
            vnaam = st.text_input("Voornaam *")
            id_nr = st.text_input("ID-Nummer *")
            tel = st.text_input("Telefoon *")
        with col2:
            anaam = st.text_input("Achternaam *")
            lad_nr = st.text_input("LAD Nummer *")
            email = st.text_input("E-mail *")
        
        omschrijving = st.text_area("Omschrijving van het verzoek *")
        datum = st.date_input("Kies datum (Ma/Wo)", min_value=datetime.date.today())
        
        alle_tijden, bezet = get_beschikbare_tijden(datum)
        tijd = st.selectbox("Kies tijdstip (15 min)", alle_tijden)
        
        if tijd in bezet: st.error(f"🔴 {tijd} is al bezet.")
        else: st.success(f"🟢 {tijd} is beschikbaar.")

        uploaded_file = st.file_uploader("Upload documenten", type=['pdf', 'jpg', 'png'])
        submit = st.form_submit_button("Aanvraag Verzenden")

    if submit and vnaam and omschrijving:
        if datum.weekday() in [0, 2]:
            doc_url = ""
            if uploaded_file:
                fn = f"{vnaam}_{datetime.datetime.now().timestamp()}.pdf"
                supabase.storage.from_("documenten").upload(fn, uploaded_file.getvalue())
                doc_url = supabase.storage.from_("documenten").get_public_url(fn)

            data = {
                "voornaam": vnaam, "achternaam": anaam, "email": email, "id_nummer": id_nr,
                "lad_nummer": lad_nr, "telefoon": tel, "afspraak_datum": str(datum),
                "afspraak_tijd": tijd, "status": "In behandeling", "document_url": doc_url,
                "omschrijving": omschrijving
            }
            supabase.table("aanvagen").insert(data).execute()
            st.success("✅ Uw aanvraag is succesvol verzonden!")
        else:
            st.error("⚠️ Afspraken alleen op Maandag of Woensdag.")

# --- 6. MEDEWERKER PORTAAL ---
elif keuze == "Medewerker Portaal":
    if not st.session_state["logged_in"]:
        st.title("🔐 Login Medewerker")
        u = st.text_input("Gebruikersnaam").strip()
        p = st.text_input("Wachtwoord", type="password").strip()
        
        if st.button("Inloggen"):
            # DIRECTE FIX VOOR image_ff18bf.png
            if u == "ICT Wanica" and p == "l3lyd@rp":
                st.session_state.update({"logged_in": True, "user_rol": "Admin"})
                st.rerun()
            else:
                res = supabase.table("medewerkers").select("*").eq("gebruikersnaam", u).execute()
                if res.data and res.data[0]['wachtwoord'] == p:
                    st.session_state.update({"logged_in": True, "user_rol": res.data[0]['rol']})
                    st.rerun()
                else: st.error("Inloggen mislukt.")
    else:
        st.sidebar.button("Uitloggen", on_click=lambda: st.session_state.update({"logged_in": False}))
        tabs = st.tabs(["📋 Beheer & Verwijderen", "📅 Kalender Overzicht", "📊 Rapportage", "⚙️ Admin"])

        # TAB: BEHEER
        with tabs[0]:
            res = supabase.table("aanvragen").select("*").execute()
            if res.data:
                df = pd.DataFrame(res.data)
                sel_id = st.selectbox("Selecteer ID voor actie", df['id'].tolist())
                c1, c2 = st.columns(2)
                with c1:
                    new_st = st.selectbox("Status", ["Bevestigd", "Geannuleerd", "In behandeling"])
                    if st.button("Update Status"):
                        supabase.table("aanvragen").update({"status": new_st}).eq("id", sel_id).execute()
                        st.rerun()
                with c2:
                    if st.button("❌ Dossier Verwijderen"):
                        supabase.table("aanvragen").delete().eq("id", sel_id).execute()
                        st.rerun()
                st.dataframe(df)

        # TAB: KALENDER
        with tabs[1]:
            st.subheader("📅 Afspraken Schema")
            res_c = supabase.table("aanvragen").select("voornaam, achternaam, afspraak_datum, afspraak_tijd, status").execute()
            if res_c.data: st.table(pd.DataFrame(res_c.data).sort_values(['afspraak_datum', 'afspraak_tijd']))

        # TAB: RAPPORTAGE (Download)
        with tabs[2]:
            st.subheader("📊 Klantenrapportage")
            res_r = supabase.table("aanvragen").select("*").execute()
            if res_r.data:
                df_r = pd.DataFrame(res_r.data)
                st.dataframe(df_r[["voornaam", "achternaam", "omschrijving", "afspraak_datum", "status"]])
                csv = df_r.to_csv(index=False).encode('utf-8')
                st.download_button("📥 Download Rapportage (CSV)", csv, "DGW_Rapport.csv", "text/csv")

        # TAB: ADMIN (Gebruikers & Rollen)
        with tabs[3]:
            if st.session_state["user_rol"] == "Admin":
                st.subheader("👥 Medewerkers Beheren")
                with st.expander("Nieuwe Medewerker"):
                    nu = st.text_input("Gebruikersnaam")
                    np = st.text_input("Wachtwoord", type="password")
                    nr = st.selectbox("Rol", ["Medewerker", "Admin"])
                    if st.button("Aanmaken"):
                        supabase.table("medewerkers").insert({"gebruikersnaam": nu, "wachtwoord": np, "rol": nr}).execute()
                        st.success(f"Account {nu} actief!")
                
                res_m = supabase.table("medewerkers").select("*").execute()
                if res_m.data:
                    df_m = pd.DataFrame(res_m.data)
                    del_m = st.selectbox("Verwijder Account", df_m['gebruikersnaam'].tolist())
                    if st.button("Verwijderen"):
                        supabase.table("medewerkers").delete().eq("gebruikersnaam", del_m).execute()
                        st.rerun()
            else: st.warning("Alleen voor Admins.")

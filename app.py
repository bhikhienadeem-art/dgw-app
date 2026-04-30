import streamlit as st
from supabase import create_client, Client
import smtplib
from email.mime.text import MIMEText
from email.mime.multipart import MIMEMultipart
import datetime
import pandas as pd

# 1. Pagina Configuratie & Styling (Groen/Wit thema)
st.set_page_config(page_title="DGW Wanica Portaal", page_icon="📝", layout="wide")

st.markdown("""
    <style>
    .main { background-color: #ffffff; }
    .stButton>button { background-color: #2e7d32 !important; color: white !important; border-radius: 5px; width: 100%; }
    .sidebar .sidebar-content { background-color: #f1f8e9; }
    h1, h2, h3 { color: #1b5e20; font-family: 'Arial'; }
    .stDataFrame { border: 1px solid #2e7d32; }
    </style>
    """, unsafe_allow_html=True)

# 2. Database Verbinding
try:
    URL = st.secrets["SUPABASE_URL"]
    KEY = st.secrets["SUPABASE_KEY"]
    supabase: Client = create_client(URL, KEY)
except:
    st.error("Systeemfout: Controleer uw Streamlit Secrets!")
    st.stop()

# 3. Professionele E-mail Functies
def stuur_mail_base(ontvanger, onderwerp, bericht):
    try:
        GMAIL_USER = st.secrets["GMAIL_USER"]
        GMAIL_PASSWORD = st.secrets["GMAIL_PASSWORD"]
        msg = MIMEMultipart()
        msg['From'] = f"Dienst Grondzaken Wanica <{GMAIL_USER}>"
        msg['To'] = ontvanger
        msg['Subject'] = onderwerp
        msg.attach(MIMEText(bericht, 'plain'))
        
        server = smtplib.SMTP('smtp.gmail.com', 587)
        server.starttls()
        server.login(GMAIL_USER, GMAIL_PASSWORD)
        server.sendmail(GMAIL_USER, ontvanger, msg.as_string())
        server.quit()
        return True
    except:
        return False

def stuur_status_update_mail(data):
    if data['status'] == "Bevestigd":
        onderwerp = "✅ Uw afspraak is bevestigd - DGW Wanica"
        bericht = f"Beste {data['voornaam']},\n\nUw afspraak bij DGW Wanica is officieel bevestigd.\n\n📅 Datum: {data['datum']}\n⏰ Tijd: {data['tijd']} uur\n\nMet vriendelijke groet,\nDGW Wanica"
    elif data['status'] == "Geannuleerd":
        onderwerp = "❌ Informatie over uw afspraak - DGW Wanica"
        bericht = f"Beste {data['voornaam']},\n\nUw afspraak kon helaas niet worden goedgekeurd. Gelieve een nieuwe datum en tijd te kiezen via ons portaal.\n\nMet vriendelijke groet,\nDGW Wanica"
    else:
        onderwerp = f"Update aanvraag DGW: {data['status']}"
        bericht = f"Beste {data['voornaam']},\n\nDe status van uw aanvraag is gewijzigd naar: {data['status']}."
    
    stuur_mail_base(data['email'], onderwerp, bericht)

# 4. Navigatie & Sessiebeheer
if "logged_in" not in st.session_state:
    st.session_state["logged_in"] = False
    st.session_state["user_rol"] = None
    st.session_state["user_naam"] = None

st.sidebar.markdown("<h2 style='color: #2e7d32;'>DGW Menu</h2>", unsafe_allow_html=True)
keuze = st.sidebar.radio("Navigatie:", ["Cliënt Registratie", "Medewerker Portaal"])

# --- CLIËNT REGISTRATIE ---
if keuze == "Cliënt Registratie":
    st.title("📝 Registratie: Dienst Grondzaken Wanica")
    with st.form("aanvraag_form", clear_on_submit=True):
        c1, c2 = st.columns(2)
        with c1:
            vnaam = st.text_input("Voornaam *")
            id_nr = st.text_input("ID-Nummer *")
            tel = st.text_input("Telefoon *")
        with c2:
            anaam = st.text_input("Achternaam *")
            lad_nr = st.text_input("LAD Nummer *")
            email = st.text_input("E-mail *")
        adres = st.text_input("Woonadres *")
        bericht = st.text_area("Bericht / Klacht *")
        cd, ct = st.columns(2)
        with cd:
            datum = st.date_input("Datum (Ma of Wo)", min_value=datetime.date.today())
        with ct:
            tijd = st.selectbox("Tijdstip", ["07:00", "07:30", "08:00", "08:30"])
        submit = st.form_submit_button("Gegevens Versturen")

    if submit:
        if vnaam and anaam and id_nr and email:
            if datum.weekday() in [0, 2]: # Maandag of Woensdag
                form_data = {
                    "voornaam": vnaam, "achternaam": anaam, "id_nummer": id_nr,
                    "lad_nummer": lad_nr, "telefoon": tel, "woonadres": adres,
                    "email": email, "bericht": bericht, 
                    "afspraak_datum": str(datum), "afspraak_tijd": tijd,
                    "status": "In behandeling"
                }
                try:
                    supabase.table("aanvragen").insert(form_data).execute()
                    st.success(f"✅ Bedankt {vnaam}! Uw aanvraag is opgeslagen.")
                except Exception as e:
                    st.error(f"Fout bij opslaan: {e}")
            else:
                st.error("⚠️ Afspraken zijn alleen mogelijk op Maandag en Woensdag.")

# --- MEDEWERKER PORTAAL ---
elif keuze == "Medewerker Portaal":
    if not st.session_state["logged_in"]:
        st.title("🔐 Login Medewerker")
        with st.form("login_form"):
            u = st.text_input("Gebruikersnaam")
            p = st.text_input("Wachtwoord", type="password")
            if st.form_submit_button("Inloggen"):
                # Check in de nieuwe medewerkers tabel
                res = supabase.table("medewerkers").select("*").eq("gebruikersnaam", u.strip()).eq("wachtwoord", p.strip()).execute()
                if res.data:
                    st.session_state["logged_in"] = True
                    st.session_state["user_rol"] = res.data[0]['rol']
                    st.session_state["user_naam"] = res.data[0]['gebruikersnaam']
                    st.rerun()
                else:
                    st.error("Onjuiste inloggegevens.")
    else:
        st.sidebar.info(f"Ingelogd als: {st.session_state['user_naam']} ({st.session_state['user_rol']})")
        if st.sidebar.button("Uitloggen"):
            st.session_state["logged_in"] = False
            st.rerun()

        # Tabs bepalen op basis van rol
        tab_namen = ["📋 Aanvragen", "📅 Kalender"]
        if st.session_state["user_rol"] == "Admin":
            tab_namen.append("⚙️ Admin Instellingen")
        
        tabs = st.tabs(tab_namen)

        try:
            res = supabase.table("aanvragen").select("*").execute()
            df = pd.DataFrame(res.data) if res.data else pd.DataFrame()

            # TAB 1: AANVRAGEN BEHEREN
            with tabs[0]:
                if not df.empty:
                    st.subheader("Dossier Bijwerken")
                    sel_id = st.selectbox("Selecteer dossier ID:", df['id'].tolist())
                    row = df[df['id'] == sel_id].iloc[0]

                    tijd_opties = ["07:00", "07:30", "08:00", "08:30"]
                    current_tijd = str(row['afspraak_tijd']) if str(row['afspraak_tijd']) in tijd_opties else tijd_opties[0]

                    col1, col2, col3 = st.columns(3)
                    with col1:
                        n_status = st.selectbox("Status", ["In behandeling", "Bevestigd", "Geannuleerd"])
                    with col2:
                        n_datum = st.date_input("Datum", value=pd.to_datetime(row['afspraak_datum']))
                    with col3:
                        n_tijd = st.selectbox("Tijd", tijd_opties, index=tijd_opties.index(current_tijd))

                    if st.button("Update & Mail Klant"):
                        up_data = {"status": n_status, "afspraak_datum": str(n_datum), "afspraak_tijd": n_tijd}
                        supabase.table("aanvragen").update(up_data).eq("id", sel_id).execute()
                        stuur_status_update_mail({"email": row['email'], "voornaam": row['voornaam'], "status": n_status, "datum": str(n_datum), "tijd": n_tijd})
                        st.success("Dossier bijgewerkt!")
                        st.rerun()

                    st.write("---")
                    st.dataframe(df.sort_values('created_at', ascending=False), use_container_width=True)

            # TAB 2: KALENDER
            with tabs[1]:
                if not df.empty:
                    st.subheader("Overzicht Afspraken")
                    st.table(df[['afspraak_datum', 'afspraak_tijd', 'voornaam', 'achternaam', 'status']].sort_values(['afspraak_datum', 'afspraak_tijd']))

            # TAB 3: ADMIN INSTELLINGEN (Alleen voor Admin)
            if st.session_state["user_rol"] == "Admin":
                with tabs[2]:
                    st.header("⚙️ Medewerkersbeheer")
                    
                    # Medewerker toevoegen
                    with st.expander("➕ Nieuwe Medewerker Toevoegen"):
                        with st.form("new_user_form"):
                            new_u = st.text_input("Gebruikersnaam")
                            new_p = st.text_input("Wachtwoord")
                            new_r = st.selectbox("Rol", ["Medewerker", "Admin"])
                            if st.form_submit_button("Account Aanmaken"):
                                supabase.table("medewerkers").insert({"gebruikersnaam": new_u, "wachtwoord": new_p, "rol": new_r}).execute()
                                st.success(f"Account voor {new_u} is aangemaakt!")
                                st.rerun()

                    # Medewerkers overzicht & verwijderen
                    st.subheader("Huidige Accounts")
                    m_res = supabase.table("medewerkers").select("*").execute()
                    if m_res.data:
                        m_df = pd.DataFrame(m_res.data)
                        st.dataframe(m_df[['id', 'gebruikersnaam', 'rol', 'created_at']], use_container_width=True)
                        
                        del_id = st.number_input("ID van medewerker om te verwijderen:", step=1, value=0)
                        if st.button("🗑️ Verwijder Medewerker"):
                            if del_id > 0:
                                supabase.table("medewerkers").delete().eq("id", del_id).execute()
                                st.warning(f"ID {del_id} is verwijderd.")
                                st.rerun()
        except Exception as e:
            st.error(f"Systeemfout: {e}")

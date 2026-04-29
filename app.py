import streamlit as st
from supabase import create_client, Client
import smtplib
from email.mime.text import MIMEText
from email.mime.multipart import MIMEMultipart
import datetime
import pandas as pd

# 1. Pagina Configuratie & Styling (Groen/Wit)
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
    st.error("Check uw Streamlit Secrets!")
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

def stuur_bevestigings_mail(data):
    onderwerp = "📝 Ontvangstbevestiging aanvraag - DGW Wanica"
    bericht = f"""
Beste {data['voornaam']},

Bedankt voor uw bericht aan Dienst Grondzaken Wanica. Uw aanvraag is succesvol ontvangen en wordt momenteel verwerkt.

Uw voorlopige afspraak:
📅 Datum: {data['afspraak_datum']}
⏰ Tijd: {data['afspraak_tijd']} uur

De status van uw aanvraag is momenteel: In behandeling. U ontvangt nader bericht zodra uw afspraak officieel is bevestigd.

Met vriendelijke groet,
DGW Wanica
    """
    stuur_mail_base(data['email'], onderwerp, bericht)

def stuur_status_update_mail(data):
    if data['status'] == "Bevestigd":
        onderwerp = "✅ Uw afspraak is bevestigd - DGW Wanica"
        bericht = f"""
Beste {data['voornaam']},

Goed nieuws! Uw aanvraag bij Dienst Grondzaken Wanica is goedgekeurd en uw afspraak is officieel bevestigd.

Details van uw afspraak:
📅 Datum: {data['afspraak_datum']}
⏰ Tijd: {data['afspraak_tijd']} uur

Wij kijken ernaar uit u te mogen verwelkomen. Vergeet niet uw originele documenten mee te nemen.

Met vriendelijke groet,
DGW Wanica
        """
    elif data['status'] == "Geannuleerd":
        onderwerp = "❌ Belangrijke informatie over uw afspraak - DGW Wanica"
        bericht = f"""
Beste {data['voornaam']},

Hierbij informeren wij u dat uw huidige afspraak voor de aanvraag bij Dienst Grondzaken Wanica niet kon worden goedgekeurd.

Wat u nu kunt doen:
Wij verzoeken u vriendelijk om een nieuwe afspraak in te plannen via ons portaal op een andere beschikbare datum (Maandag of Woensdag).

Onze excuses voor het ongemak.

Met vriendelijke groet,
DGW Wanica
        """
    else:
        onderwerp = f"Update uw aanvraag DGW: {data['status']}"
        bericht = f"Beste {data['voornaam']},\n\nDe status van uw aanvraag is gewijzigd naar: {data['status']}.\nAfspraak: {data['afspraak_datum']} om {data['afspraak_tijd']} uur."

    stuur_mail_base(data['email'], onderwerp, bericht)

# 4. Navigatie & Login Status
if "logged_in" not in st.session_state:
    st.session_state["logged_in"] = False

st.sidebar.markdown("<h2 style='color: #2e7d32;'>DGW Menu</h2>", unsafe_allow_html=True)
keuze = st.sidebar.radio("Navigatie:", ["Cliënt Registratie", "Medewerker Portaal"])

# --- CLIENT REGISTRATIE ---
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
                    stuur_bevestigings_mail(form_data)
                    st.success(f"✅ Bedankt {vnaam}! Uw aanvraag is opgeslagen.")
                except Exception as e:
                    st.error(f"Fout bij opslaan: {e}")
            else:
                st.error("⚠️ Afspraken zijn alleen mogelijk op Maandag en Woensdag.")
        else:
            st.warning("Vul a.u.b. alle verplichte velden in.")

# --- MEDEWERKER PORTAAL ---
elif keuze == "Medewerker Portaal":
    if not st.session_state["logged_in"]:
        st.title("🔐 Login Medewerker")
        with st.form("login_form"):
            u = st.text_input("Gebruikersnaam")
            p = st.text_input("Wachtwoord", type="password")
            if st.form_submit_button("Inloggen"):
                if u.strip() == "ICT Wanica" and p.strip() == "l3lyd@rp":
                    st.session_state["logged_in"] = True
                    st.rerun()
                else:
                    st.error("Onjuiste inloggegevens.")
    else:
        st.title("📂 Beheerders Dashboard")
        st.sidebar.button("Uitloggen", on_click=lambda: st.session_state.update({"logged_in": False}))
        
        tab1, tab2 = st.tabs(["📋 Beheer Aanvragen", "📅 Kalender"])

        try:
            res = supabase.table("aanvragen").select("*").execute()
            df = pd.DataFrame(res.data) if res.data else pd.DataFrame()

            with tab1:
                if not df.empty:
                    st.subheader("Status of Afspraak Wijzigen")
                    sel_id = st.selectbox("Selecteer dossier ID:", df['id'].tolist())
                    row = df[df['id'] == sel_id].iloc[0]

                    # Mogelijke opties voor de dropdowns
                    status_opties = ["In behandeling", "Bevestigd", "Geannuleerd"]
                    tijd_opties = ["07:00", "07:30", "08:00", "08:30"]

                    col1, col2, col3 = st.columns(3)
                    with col1:
                        # Beveiliging voor status index
                        current_status = row['status'] if row['status'] in status_opties else status_opties[0]
                        n_status = st.selectbox("Nieuwe Status", status_opties, index=status_opties.index(current_status))
                    
                    with col2:
                        n_datum = st.date_input("Nieuwe Datum", value=pd.to_datetime(row['afspraak_datum']))
                    
                    with col3:
                        # Beveiliging voor tijd index (Oplossing voor image_8aa2b6.png)
                        db_tijd = str(row['afspraak_tijd'])
                        current_tijd = db_tijd if db_tijd in tijd_opties else tijd_opties[0]
                        n_tijd = st.selectbox("Nieuwe Tijd", tijd_opties, index=tijd_opties.index(current_tijd))

                    if st.button("Update doorvoeren & Klant mailen"):
                        up_data = {"status": n_status, "afspraak_datum": str(n_datum), "afspraak_tijd": n_tijd}
                        supabase.table("aanvragen").update(up_data).eq("id", sel_id).execute()
                        
                        mail_info = {"email": row['email'], "voornaam": row['voornaam'], "status": n_status, "afspraak_datum": str(n_datum), "afspraak_tijd": n_tijd}
                        stuur_status_update_mail(mail_info)
                        st.success(f"Dossier {sel_id} bijgewerkt! Mail is verstuurd.")
                        st.rerun()

                    st.write("---")
                    st.dataframe(df.sort_values('created_at', ascending=False), use_container_width=True)
                else:
                    st.info("Geen aanvragen gevonden.")

            with tab2:
                if not df.empty:
                    st.subheader("📅 Overzicht Geplande Afspraken")
                    cal_view = df[['afspraak_datum', 'afspraak_tijd', 'voornaam', 'achternaam', 'status', 'telefoon']]
                    st.table(cal_view.sort_values(by=['afspraak_datum', 'afspraak_tijd']))
        except Exception as e:
            st.error(f"Systeemfout: {e}")

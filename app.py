import streamlit as st
from supabase import create_client, Client
import datetime
import pandas as pd
import smtplib
from email.mime.text import MIMEText
from email.mime.multipart import MIMEMultipart
from email.mime.application import MIMEApplication

# --- 1. CONFIGURATIE & STYLING ---
st.set_page_config(page_title="DGW Wanica Portaal", layout="wide")

# Logo toevoegen in de sidebar
try:
    st.sidebar.image("orgineel logo Centrum.png", use_container_width=True)
except:
    st.sidebar.warning("Logo bestand (orgineel logo Centrum.png) niet gevonden.")

st.markdown("""
    <style>
    .tijd-knop { display: inline-block; padding: 10px; margin: 5px; border-radius: 5px; text-align: center; font-weight: bold; width: 85px; }
    .vrij { background-color: #e8f5e9; border: 2px solid #2e7d32; color: #2e7d32; }
    .bezet { background-color: #ffebee; border: 2px solid #c62828; color: #c62828; text-decoration: line-through; }
    .stButton>button { background-color: #2e7d32 !important; color: white !important; border-radius: 5px; width: 100%; height: 50px; font-size: 18px; border: none; }
    .status-card { padding: 15px; border-radius: 10px; border-left: 5px solid #2e7d32; background-color: #f9f9f9; margin-bottom: 10px; }
    </style>
    """, unsafe_allow_html=True)

# Verbinding met Supabase
try:
    supabase = create_client(st.secrets["SUPABASE_URL"], st.secrets["SUPABASE_KEY"])
except:
    st.error("Configuratie fout in Secrets.")
    st.stop()

# --- MAIL FUNCTIE ---
def stuur_mail(ontvanger, onderwerp, inhoud, bestanden=None):
    try:
        msg = MIMEMultipart()
        msg['Subject'] = onderwerp
        msg['From'] = st.secrets["EMAIL_USER"]
        msg['To'] = ontvanger
        msg.attach(MIMEText(inhoud))
        
        if bestanden:
            for f in bestanden:
                f.seek(0)
                bijlage = MIMEApplication(f.read(), Name=f.name)
                bijlage['Content-Disposition'] = f'attachment; filename="{f.name}"'
                msg.attach(bijlage)
                f.seek(0)

        with smtplib.SMTP_SSL('smtp.gmail.com', 465) as server:
            server.login(st.secrets["EMAIL_USER"], st.secrets["EMAIL_PASS"])
            server.send_message(msg)
    except Exception as e:
        st.warning(f"Mailfout: {e}")

# --- 2. LOGIN SYSTEEM ---
if 'logged_in' not in st.session_state:
    st.session_state.logged_in = False
    st.session_state.role = None
    st.session_state.user = None

def login():
    st.sidebar.subheader("Inloggen Medewerker")
    try:
        res = supabase.table("medewerkers").select("*").execute()
        user_list = [u['gebruikersnaam'] for u in res.data] if res.data else []
        selected_user = st.sidebar.selectbox("Gebruiker", ["--- Selecteer ---"] + user_list)
        password = st.sidebar.text_input("Wachtwoord", type="password")
        if st.sidebar.button("Login"):
            user_data = next((u for u in res.data if u['gebruikersnaam'] == selected_user), None)
            if user_data and user_data['wachtwoord'] == password:
                st.session_state.logged_in = True
                st.session_state.role = user_data['rol']
                st.session_state.user = selected_user
                st.rerun()
            else:
                st.sidebar.error("Onjuiste gegevens")
    except Exception as e:
        st.sidebar.error(f"Database fout: {e}")

# --- 3. NAVIGATIE ---
menu_options = ["Cliënt Registratie"]
if st.session_state.logged_in:
    menu_options += ["Medewerker Portaal", "Agenda Overzicht", "Rapportages"]
    if st.session_state.role == "Admin":
        menu_options.append("Admin Instellingen")
    if st.sidebar.button("Uitloggen"):
        st.session_state.logged_in = False
        st.rerun()
else:
    login()

menu = st.sidebar.radio("Navigatie", menu_options)

# --- 4. PAGINA'S ---

if menu == "Cliënt Registratie":
    st.subheader("📝 Nieuwe Aanvraag Indienen")
    col1, col2 = st.columns(2)
    with col1:
        vnaam = st.text_input("Voornaam *")
        anaam = st.text_input("Achternaam *")
        id_nr = st.text_input("ID-Nummer *")
        woonadres = st.text_input("Woonadres *")
    with col2:
        tel = st.text_input("Telefoonnummer *")
        email = st.text_input("E-mailadres *")
        lad_nr = st.text_input("LAD Nummer (optioneel)")
    
    bericht = st.text_area("Omschrijving klacht/verzoek *")
    uploaded_files = st.file_uploader("Documenten Uploaden", accept_multiple_files=True)

    st.write("---")
    st.subheader("📅 Kies uw Afspraakmoment")
    datum = st.date_input("Kies een datum", min_value=datetime.date.today())
    
    if datum.weekday() not in [0, 2]: # Alleen Ma en Wo
        st.error("⚠️ Afspraken zijn uitsluitend mogelijk op Maandag en Woensdag.")
        vrije_tijden = []
    else:
        tijden = [f"{h:02d}:{m:02d}" for h in range(7, 15) for m in [0, 15, 30, 45]]
        slots = [t for t in tijden if "07:00" <= t <= "14:45"]
        res = supabase.table("aanvragen").select("afspraak_tijd").eq("afspraak_datum", str(datum)).execute()
        bezet = [r['afspraak_tijd'] for r in res.data] if res.data else []
        
        cols = st.columns(6)
        for i, t in enumerate(slots):
            status = "bezet" if t in bezet else "vrij"
            with cols[i % 6]:
                st.markdown(f'<div class="tijd-knop {status}">{t}</div>', unsafe_allow_html=True)
        vrije_tijden = [t for t in slots if t not in bezet]

    st.write("---")
    gekozen_tijd = st.selectbox("Selecteer uw tijdstip *", ["--- Maak een keuze ---"] + vrije_tijden)

    if st.button("Verstuur Aanvraag"):
        if all([vnaam, anaam, id_nr, woonadres, tel, email, bericht]) and gekozen_tijd != "--- Maak een keuze ---":
            data = {
                "voornaam": vnaam, "achternaam": anaam, "id_nummer": id_nr, "woonadres": woonadres, 
                "telefoon": tel, "email": email, "lad_nummer": lad_nr, "bericht": bericht, 
                "afspraak_datum": str(datum), "afspraak_tijd": gekozen_tijd, "status": "In behandeling"
            }
            supabase.table("aanvragen").insert(data).execute()
            
            # Bevestigingtekst voor download en mail
            bevestiging_tekst = f"BEWIJS VAN AANVRAAG - DGW WANICA\n\nNaam: {vnaam} {anaam}\nID-Nummer: {id_nr}\nDatum: {datum}\nTijd: {gekozen_tijd}u\nStatus: In behandeling\n\nBewaar dit document goed."
            
            stuur_mail(email, "Ontvangstbevestiging DGW Wanica", bevestiging_tekst)
            stuur_mail(st.secrets["EMAIL_USER"], f"Nieuwe Aanvraag: {vnaam} {anaam}", f"Klantgegevens: {data}", bestanden=uploaded_files)
            
            st.success("✅ Uw aanvraag is succesvol verzonden!")
            st.download_button("📥 Download Bewijs van Aanvraag (TXT)", bevestiging_tekst, file_name=f"DGW_Bewijs_{id_nr}.txt")
            st.balloons()
        else:
            st.error("⚠️ Vul a.u.b. alle verplichte velden in.")

elif menu == "Medewerker Portaal":
    st.subheader("📋 Beheer & Verwijder Aanvragen")
    res = supabase.table("aanvragen").select("*").order('afspraak_datum', desc=False).execute()
    if res.data:
        df = pd.DataFrame(res.data)
        st.dataframe(df, use_container_width=True)
        
        st.write("---")
        colA, colB = st.columns(2)
        
        with colA:
            st.subheader("⚙️ Status Bijwerken")
            opties = {row['id']: f"{row['voornaam']} {row['achternaam']} ({row['afspraak_datum']})" for index, row in df.iterrows()}
            selected_id = st.selectbox("Selecteer aanvraag voor update", options=list(opties.keys()), format_func=lambda x: opties[x])
            aanvraag = next(item for item in res.data if item["id"] == selected_id)
            
            nieuwe_status = st.selectbox("Nieuwe Status", ["In behandeling", "Bevestigd", "Geannuleerd", "Verwezen"])
            n_datum = st.date_input("Nieuwe Datum", value=datetime.datetime.strptime(aanvraag['afspraak_datum'], '%Y-%m-%d').date())
            n_tijd = st.text_input("Nieuwe Tijd", value=aanvraag['afspraak_tijd'])
            
            if st.button("Update Opslaan & Mailen"):
                supabase.table("aanvragen").update({"status": nieuwe_status, "afspraak_datum": str(n_datum), "afspraak_tijd": n_tijd}).eq("id", selected_id).execute()
                stuur_mail(aanvraag['email'], "Update DGW Aanvraag", f"Uw status is nu: {nieuwe_status} op {n_datum} om {n_tijd}.")
                st.success("Aanvraag bijgewerkt!")
                st.rerun()

        with colB:
            st.subheader("🗑️ Definitief Verwijderen")
            st.warning("Let op: Verwijderen kan niet ongedaan worden gemaakt.")
            del_id = st.selectbox("Selecteer aanvraag om te WISSEN", options=list(opties.keys()), format_func=lambda x: opties[x])
            
            if st.button("🔥 VERWIJDER REGISTRATIE"):
                supabase.table("aanvragen").delete().eq("id", del_id).execute()
                st.error(f"Registratie {del_id} is definitief verwijderd.")
                st.rerun()

elif menu == "Agenda Overzicht":
    st.subheader("📅 Verbeterde Kalenderweergave")
    res = supabase.table("aanvragen").select("*").execute()
    if res.data:
        df = pd.DataFrame(res.data)
        df['afspraak_datum'] = pd.to_datetime(df['afspraak_datum']).dt.date
        
        # Filteren op toekomstige afspraken
        dag_keuze = st.date_input("Bekijk planning voor datum:", value=datetime.date.today())
        dag_data = df[df['afspraak_datum'] == dag_keuze].sort_values('afspraak_tijd')
        
        if not dag_data.empty:
            st.write(f"### Planning voor {dag_keuze}")
            for _, row in dag_data.iterrows():
                with st.container():
                    st.markdown(f"""
                    <div class="status-card">
                        <b>🕒 {row['afspraak_tijd']}</b> | {row['voornaam']} {row['achternaam']} <br>
                        📞 {row['telefoon']} | 🏷️ Status: {row['status']}
                    </div>
                    """, unsafe_allow_html=True)
        else:
            st.info(f"Geen afspraken gepland voor {dag_keuze}")

elif menu == "Rapportages":
    st.subheader("📊 Management Rapportages")
    res = supabase.table("aanvragen").select("*").execute()
    if res.data:
        df = pd.DataFrame(res.data)
        st.write("Statistieken per status:")
        st.bar_chart(df['status'].value_counts())
        csv = df.to_csv(index=False).encode('utf-8')
        st.download_button("📥 Download Database Export (.csv)", data=csv, file_name="DGW_Export.csv")

elif menu == "Admin Instellingen":
    st.subheader("⚙️ Medewerkers Beheer")
    res_m = supabase.table("medewerkers").select("*").execute()
    if res_m.data:
        st.table(pd.DataFrame(res_m.data)[['gebruikersnaam', 'rol']])
        # Voeg hier de logica toe voor nieuwe medewerkers zoals in de vorige versies

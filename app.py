import streamlit as st
from supabase import create_client, Client
import datetime
import pandas as pd
import smtplib
from email.mime.text import MIMEText
from email.mime.multipart import MIMEMultipart
from email.mime.application import MIMEApplication

# --- 1. CONFIGURATIE & THEMA ---
st.set_page_config(page_title="DGW Wanica Portaal", page_icon="📝", layout="wide")

# Styling voor de tijdsknoppen en interface
st.markdown("""
    <style>
    .tijd-knop {
        display: inline-block; padding: 10px; margin: 5px; border-radius: 5px;
        text-align: center; font-weight: bold; width: 85px;
    }
    .vrij { background-color: #e8f5e9; border: 2px solid #2e7d32; color: #2e7d32; }
    .bezet { background-color: #ffebee; border: 2px solid #c62828; color: #c62828; text-decoration: line-through; }
    .stButton>button { background-color: #2e7d32; color: white; border-radius: 5px; width: 100%; height: 50px; font-weight: bold; }
    </style>
    """, unsafe_allow_html=True)

# --- 2. VERBINDINGEN (Secrets check) ---
def connect_db():
    try:
        url = st.secrets["SUPABASE_URL"]
        key = st.secrets["SUPABASE_KEY"]
        return create_client(url, key)
    except Exception:
        st.error("Systeemfout: Database Secrets niet gevonden!")
        st.stop()

supabase = connect_db()

# --- 3. HELPER FUNCTIES ---
def stuur_mail_met_bijlagen(ontvanger, onderwerp, inhoud, bestanden=None):
    """Verstuurt mails naar cliënt en medewerker (inclusief bijlagen)"""
    try:
        msg = MIMEMultipart()
        msg['Subject'] = onderwerp
        msg['From'] = st.secrets["EMAIL_USER"]
        msg['To'] = ontvanger
        msg.attach(MIMEText(inhoud))
        
        if bestanden:
            for f in bestanden:
                bijlage = MIMEApplication(f.read(), Name=f.name)
                bijlage['Content-Disposition'] = f'attachment; filename="{f.name}"'
                msg.attach(bijlage)
                f.seek(0) # Reset voor database opslag indien nodig
        
        with smtplib.SMTP_SSL('smtp.gmail.com', 465) as server:
            server.login(st.secrets["EMAIL_USER"], st.secrets["EMAIL_PASS"])
            server.send_message(msg)
    except Exception as e:
        st.warning(f"Mail-notificatie kon niet volledig worden verzonden: {e}")

def get_tijd_status(datum):
    """Haalt bezette tijden op en genereert slots tussen 07:30 en 14:00"""
    start = datetime.datetime.strptime("07:30", "%H:%M")
    eind = datetime.datetime.strptime("14:00", "%H:%M")
    alle_tijden = []
    while start <= eind:
        alle_tijden.append(start.strftime("%H:%M"))
        start += datetime.timedelta(minutes=15)
    
    # Check bezette slots in de tabel 'aanvragen'
    res = supabase.table("aanvragen").select("afspraak_tijd").eq("afspraak_datum", str(datum)).execute()
    bezette_tijden = [r['afspraak_tijd'] for r in res.data] if res.data else []
    return alle_tijden, bezette_tijden

# --- 4. GEBRUIKERSINTERFACE ---
st.title("📝 Dienst Grondzaken Wanica (DGW)")
menu = st.sidebar.radio("Navigatie", ["Cliënt Registratie", "Medewerker Portaal"])

if menu == "Cliënt Registratie":
    st.subheader("Nieuwe Aanvraag")
    
    col1, col2 = st.columns(2)
    with col1:
        vnaam = st.text_input("Voornaam *")
        anaam = st.text_input("Achternaam *")
        id_nr = st.text_input("ID-Nummer *")
        woonadres = st.text_input("Woonadres *")
    with col2:
        tel = st.text_input("Telefoonnummer *")
        email = st.text_input("E-mailadres *")
        lad_nr = st.text_input("LAD Nummer (indien van toepassing)")
    
    bericht = st.text_area("Omschrijving klacht/verzoek *")
    uploaded_files = st.file_uploader("Documenten Uploaden (ID, Grondpapieren, etc.)", accept_multiple_files=True)

    st.write("---")
    st.subheader("📅 Plan uw afspraak")
    datum = st.date_input("Kies een datum", min_value=datetime.date.today())

    # Beperking op Maandag (0) en Woensdag (2)
    if datum.weekday() not in [0, 2]:
        st.error("Afspraken zijn uitsluitend mogelijk op Maandag en Woensdag.")
    else:
        alle_tijden, bezette_tijden = get_tijd_status(datum)
        st.write("**Beschikbaarheid:**")
        
        cols = st.columns(6)
        for i, t in enumerate(alle_tijden):
            kleur = "bezet" if t in bezette_tijden else "vrij"
            with cols[i % 6]:
                st.markdown(f'<div class="tijd-knop {kleur}">{t}</div>', unsafe_allow_html=True)

        vrije_opties = [t for t in alle_tijden if t not in bezette_tijden]
        
        if vrije_opties:
            gekozen_tijd = st.selectbox("Selecteer een beschikbaar tijdstip *", vrije_opties)
            
            if st.button("Aanvraag indienen"):
                # Controleer of alle verplichte velden zijn gevuld
                if vnaam and anaam and id_nr and woonadres and tel and email and bericht:
                    # A. Opslaan in Database
                    payload = {
                        "voornaam": vnaam, "achternaam": anaam, "id_nummer": id_nr,
                        "woonadres": woonadres, "telefoon": tel, "email": email, 
                        "lad_nummer": lad_nr, "bericht": bericht, "afspraak_datum": str(datum),
                        "afspraak_tijd": gekozen_tijd, "status": "In behandeling"
                    }
                    supabase.table("aanvragen").insert(payload).execute()
                    
                    # B. Mail naar Cliënt
                    mail_c = f"Beste {vnaam},\n\nUw aanvraag is ontvangen voor {datum} om {gekozen_tijd}u."
                    stuur_mail_met_bijlagen(email, "Bevestiging Ontvangst DGW", mail_c)
                    
                    # C. Mail naar Medewerker (Met alle details en bijlagen)
                    mail_m = f"""
                    Nieuwe registratie binnengekomen:
                    
                    Naam: {vnaam} {anaam}
                    ID: {id_nr}
                    Adres: {woonadres}
                    Tel: {tel}
                    Email: {email}
                    LAD: {lad_nr if lad_nr else 'Niet opgegeven'}
                    
                    Bericht: {bericht}
                    Afspraak: {datum} om {gekozen_tijd}u
                    """
                    stuur_mail_met_bijlagen(st.secrets["EMAIL_USER"], f"Nieuwe Aanvraag: {vnaam} {anaam}", mail_m, uploaded_files)
                    
                    st.success("✅ Uw aanvraag is succesvol ingediend! De medewerker heeft uw documenten ontvangen.")
                    st.balloons()
                else:
                    st.error("⚠️ Vul a.u.b. alle velden met een sterretje (*) in.")
        else:
            st.warning("Helaas zijn er geen plekken meer vrij op deze dag.")

elif menu == "Medewerker Portaal":
    st.subheader("Overzicht Aanvragen")
    # Haal alle data op voor de baliemedewerkers
    res = supabase.table("aanvragen").select("*").order("afspraak_datum", desc=False).execute()
    
    if res.data:
        df = pd.DataFrame(res.data)
        # Toon tabel met de mogelijkheid voor medewerkers om gegevens te controleren
        st.dataframe(df[['voornaam', 'achternaam', 'id_nummer', 'telefoon', 'afspraak_datum', 'afspraak_tijd', 'status']])
    else:
        st.info("Er zijn momenteel geen actieve aanvragen.")

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

st.markdown("""
    <style>
    .tijd-knop {
        display: inline-block; padding: 10px; margin: 5px; border-radius: 5px;
        text-align: center; font-weight: bold; width: 85px;
    }
    .vrij { background-color: #e8f5e9; border: 2px solid #2e7d32; color: #2e7d32; }
    .bezet { background-color: #ffebee; border: 2px solid #c62828; color: #c62828; text-decoration: line-through; }
    .stButton>button { background-color: #2e7d32; color: white; border-radius: 5px; width: 100%; }
    </style>
    """, unsafe_allow_html=True)

# --- 2. DATABASE & EMAIL VERBINDING ---
try:
    URL = st.secrets["SUPABASE_URL"]
    KEY = st.secrets["SUPABASE_KEY"]
    supabase: Client = create_client(URL, KEY)
    
    EMAIL_USER = st.secrets["EMAIL_USER"]
    EMAIL_PASS = st.secrets["EMAIL_PASS"]
except Exception:
    st.error("Systeemfout: Controleer uw Secrets!")
    st.stop()

# --- 3. HERSTELDE EMAIL FUNCTIE MET BIJLAGEN ---
def stuur_mail_met_bijlagen(ontvanger, onderwerp, inhoud, bestanden=None):
    try:
        msg = MIMEMultipart()
        msg['Subject'] = onderwerp
        msg['From'] = EMAIL_USER
        msg['To'] = ontvanger
        msg.attach(MIMEText(inhoud))
        
        # Voeg elk geüpload bestand toe als bijlage
        if bestanden:
            for f in bestanden:
                bijlage = MIMEApplication(f.read(), Name=f.name)
                bijlage['Content-Disposition'] = f'attachment; filename="{f.name}"'
                msg.attach(bijlage)
                f.seek(0) # Reset file pointer voor hergebruik
        
        with smtplib.SMTP_SSL('smtp.gmail.com', 465) as server:
            server.login(EMAIL_USER, EMAIL_PASS)
            server.send_message(msg)
    except Exception as e:
        st.error(f"E-mail verzenden mislukt: {e}")

def get_tijd_status(datum):
    start = datetime.datetime.strptime("07:30", "%H:%M")
    eind = datetime.datetime.strptime("14:00", "%H:%M")
    alle_tijden = []
    while start <= eind:
        alle_tijden.append(start.strftime("%H:%M"))
        start += datetime.timedelta(minutes=15)
    
    res = supabase.table("aanvragen").select("afspraak_tijd").eq("afspraak_datum", str(datum)).execute()
    bezette_tijden = [r['afspraak_tijd'] for r in res.data] if res.data else []
    return alle_tijden, bezette_tijden

# --- 4. INTERFACE ---
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
        lad_nr = st.text_input("LAD Nummer")
    
    bericht = st.text_area("Omschrijving klacht/verzoek *")
    uploaded_files = st.file_uploader("Documenten Uploaden (ID, Grondpapieren)", accept_multiple_files=True)

    st.write("---")
    st.subheader("📅 Plan uw afspraak")
    datum = st.date_input("Kies een datum", min_value=datetime.date.today())

    if datum.weekday() not in [0, 2]:
        st.error("Afspraken uitsluitend op Maandag en Woensdag (07:30 - 14:00).")
    else:
        alle_tijden, bezette_tijden = get_tijd_status(datum)
        cols = st.columns(6)
        for i, t in enumerate(alle_tijden):
            is_bezet = t in bezette_tijden
            kleur_class = "bezet" if is_bezet else "vrij"
            with cols[i % 6]:
                st.markdown(f'<div class="tijd-knop {kleur_class}">{t}</div>', unsafe_allow_html=True)

        vrije_opties = [t for t in alle_tijden if t not in bezette_tijden]
        if vrije_opties:
            tijd = st.selectbox("Kies uw tijdstip *", vrije_opties)
            if st.button("Aanvraag indienen"):
                if vnaam and anaam and id_nr and woonadres and email:
                    # Database opslag
                    data = {
                        "voornaam": vnaam, "achternaam": anaam, "id_nummer": id_nr,
                        "woonadres": woonadres, "telefoon": tel, "email": email, 
                        "lad_nummer": lad_nr, "bericht": bericht, "afspraak_datum": str(datum),
                        "afspraak_tijd": tijd, "status": "In behandeling"
                    }
                    supabase.table("aanvragen").insert(data).execute()
                    
                    # 1. Bevestiging naar Cliënt
                    mail_client = f"Beste {vnaam},\n\nUw aanvraag is ontvangen voor {datum} om {tijd}u."
                    stuur_mail_met_bijlagen(email, "Bevestiging Aanvraag DGW", mail_client)
                    
                    # 2. Gedetailleerde mail naar Medewerker INCLUSIEF BIJLAGEN
                    mail_medewerker = f"""
                    Nieuwe aanvraag binnengekomen:
                    
                    Naam: {vnaam} {anaam}
                    ID-Nummer: {id_nr}
                    Woonadres: {woonadres}
                    Telefoon: {tel}
                    E-mail: {email}
                    LAD Nummer: {lad_nr}
                    Bericht: {bericht}
                    
                    Afspraak: {datum} om {tijd}u
                    """
                    stuur_mail_met_bijlagen(EMAIL_USER, f"Nieuwe Aanvraag: {vnaam} {anaam}", mail_medewerker, uploaded_files)
                    
                    st.success("✅ Aanvraag succesvol ingediend! De medewerker heeft de documenten als bijlage ontvangen.")
                else:
                    st.warning("Vul alle velden met een * in.")

elif menu == "Medewerker Portaal":
    st.subheader("Dossierbeheer")
    res = supabase.table("aanvragen").select("*").execute()
    if res.data:
        df = pd.DataFrame(res.data)
        st.dataframe(df)

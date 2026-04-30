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

# Jouw specifieke groen/wit styling
st.markdown("""
    <style>
    .tijd-knop { display: inline-block; padding: 10px; margin: 5px; border-radius: 5px; text-align: center; font-weight: bold; width: 85px; }
    .vrij { background-color: #e8f5e9; border: 2px solid #2e7d32; color: #2e7d32; }
    .bezet { background-color: #ffebee; border: 2px solid #c62828; color: #c62828; text-decoration: line-through; }
    .stButton>button { background-color: #2e7d32 !important; color: white !important; border-radius: 5px; width: 100%; height: 50px; font-size: 18px; border: none; }
    </style>
    """, unsafe_allow_html=True)

# Verbinding met Supabase
try:
    supabase = create_client(st.secrets["SUPABASE_URL"], st.secrets["SUPABASE_KEY"])
except Exception as e:
    st.error("Database configuratie fout. Controleer je Secrets.")
    st.stop()

def stuur_mail(ontvanger, onderwerp, inhoud, bestanden=None):
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
                f.seek(0)
        with smtplib.SMTP_SSL('smtp.gmail.com', 465) as server:
            server.login(st.secrets["EMAIL_USER"], st.secrets["EMAIL_PASS"])
            server.send_message(msg)
    except Exception as e:
        st.warning(f"E-mail kon niet worden verzonden: {e}")

# --- 2. INTERFACE ---
st.title("📝 Dienst Grondzaken Wanica (DGW)")
menu = st.sidebar.radio("Navigatie", ["Cliënt Registratie", "Medewerker Portaal"])

if menu == "Cliënt Registratie":
    st.subheader("Nieuwe Aanvraag")
    
    # Stap 1: Datum en Beschikbaarheid (buiten het formulier voor directe update)
    datum = st.date_input("Kies een datum voor uw afspraak", min_value=datetime.date.today())
    
    vrije_tijden = []
    # Alleen Maandag (0) en Woensdag (2)
    if datum.weekday() not in [0, 2]:
        st.error("⚠️ Afspraken zijn uitsluitend mogelijk op Maandag en Woensdag.")
    else:
        # Tijd slots van 07:30 tot 14:00
        tijden = [f"{h:02d}:{m:02d}" for h in range(7, 15) for m in [0, 15, 30, 45]]
        slots = [t for t in tijden if "07:30" <= t <= "14:00"]
        
        # Bezette tijden ophalen uit Supabase
        res = supabase.table("aanvragen").select("afspraak_tijd").eq("afspraak_datum", str(datum)).execute()
        bezet = [r['afspraak_tijd'] for r in res.data] if res.data else []
        
        st.write("Groen = Vrij | Rood = Bezet")
        cols = st.columns(6)
        for i, t in enumerate(slots):
            status = "bezet" if t in bezet else "vrij"
            with cols[i % 6]:
                st.markdown(f'<div class="tijd-knop {status}">{t}</div>', unsafe_allow_html=True)
        
        vrije_tijden = [t for t in slots if t not in bezet]

    st.write("---")

    # Stap 2: Het Formulier (lost de problemen in image_efc300.png op)
    with st.form("client_form", clear_on_submit=True):
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
        
        # Tijdselectie binnen het formulier
        gekozen_tijd = st.selectbox("Selecteer uw tijdstip *", vrije_tijden if vrije_tijden else ["Geen tijden beschikbaar"])
        
        submit_button = st.form_submit_button("Verstuur Aanvraag")

    if submit_button:
        # Validatie: Controleer of alle verplichte velden gevuld zijn
        if vnaam and anaam and id_nr and woonadres and tel and email and bericht and gekozen_tijd != "Geen tijden beschikbaar":
            # 1. Opslaan in Database
            data = {
                "voornaam": vnaam, "achternaam": anaam, "id_nummer": id_nr,
                "woonadres": woonadres, "telefoon": tel, "email": email, 
                "lad_nummer": lad_nr, "bericht": bericht, "afspraak_datum": str(datum),
                "afspraak_tijd": gekozen_tijd, "status": "In behandeling"
            }
            supabase.table("aanvragen").insert(data).execute()
            
            # 2. E-mails versturen
            mail_body = f"Nieuwe aanvraag DGW:\n\nNaam: {vnaam} {anaam}\nID: {id_nr}\nAdres: {woonadres}\nTel: {tel}\nAfspraak: {datum} om {gekozen_tijd}u\nBericht: {bericht}"
            
            # Naar medewerker
            stuur_mail(st.secrets["EMAIL_USER"], f"Nieuwe Aanvraag: {vnaam} {anaam}", mail_body, uploaded_files)
            # Naar cliënt
            stuur_mail(email, "Ontvangstbevestiging DGW Wanica", f"Beste {vnaam},\n\nUw aanvraag voor een afspraak op {datum} om {gekozen_tijd}u is succesvol ontvangen.")
            
            st.success("✅ Uw aanvraag is succesvol ingediend!")
            st.balloons()
        else:
            st.error("⚠️ Vul a.u.b. alle velden met een sterretje (*) in en kies een geldig tijdstip.")

elif menu == "Medewerker Portaal":
    st.subheader("Overzicht Registraties")
    # Alleen toegankelijk voor medewerkers
    res = supabase.table("aanvragen").select("*").order("afspraak_datum").execute()
    if res.data:
        df = pd.DataFrame(res.data)
        st.dataframe(df)
    else:
        st.info("Er zijn momenteel geen registraties gevonden.")

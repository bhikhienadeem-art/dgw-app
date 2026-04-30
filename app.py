import streamlit as st
from supabase import create_client, Client
import datetime
import pandas as pd
import smtplib
from email.mime.text import MIMEText
from email.mime.multipart import MIMEMultipart
from email.mime.application import MIMEApplication

# --- 1. CONFIGURATIE ---
st.set_page_config(page_title="DGW Wanica Portaal", layout="wide")

# Styling behouden (Groen/Wit)
st.markdown("""
    <style>
    .tijd-knop { display: inline-block; padding: 10px; margin: 5px; border-radius: 5px; text-align: center; font-weight: bold; width: 85px; }
    .vrij { background-color: #e8f5e9; border: 2px solid #2e7d32; color: #2e7d32; }
    .bezet { background-color: #ffebee; border: 2px solid #c62828; color: #c62828; text-decoration: line-through; }
    .stButton>button { background-color: #2e7d32; color: white; border-radius: 5px; width: 100%; height: 50px; font-size: 18px; border: none; }
    </style>
    """, unsafe_allow_html=True)

# Supabase Verbinding
try:
    supabase = create_client(st.secrets["SUPABASE_URL"], st.secrets["SUPABASE_KEY"])
except Exception as e:
    st.error(f"Configuratie fout: {e}")
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
        st.warning(f"Mail niet verzonden: {e}")

# --- 2. INTERFACE ---
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
        lad_nr = st.text_input("LAD Nummer (optioneel)")
    
    bericht = st.text_area("Omschrijving klacht/verzoek *")
    uploaded_files = st.file_uploader("Documenten Uploaden", accept_multiple_files=True)

    st.write("---")
    datum = st.date_input("Kies een datum", min_value=datetime.date.today())

    # Alleen Maandag en Woensdag toegestaan
    if datum.weekday() not in [0, 2]:
        st.error("Let op: Afspraken kunnen alleen op Maandag en Woensdag gepland worden.")
        gekozen_tijd = "Geen tijd"
    else:
        # Tijdslots 07:30 - 14:00 (15 min interval)
        tijden = [f"{h:02d}:{m:02d}" for h in range(7, 15) for m in [0, 15, 30, 45]]
        slots = [t for t in tijden if "07:30" <= t <= "14:00"]
        
        # Check bezette tijden in Supabase
        res = supabase.table("aanvragen").select("afspraak_tijd").eq("afspraak_datum", str(datum)).execute()
        bezet = [r['afspraak_tijd'] for r in res.data] if res.data else []
        vrij = [t for t in slots if t not in bezet]
        
        gekozen_tijd = st.selectbox("Selecteer tijdstip *", ["--- Selecteer een tijdstip ---"] + vrij)

        st.write("---")

        # VALIDATIE LOGICA: De knop werkt alleen als alles gevuld is
        foutmeldingen = []
        if not vnaam: foutmeldingen.append("Voornaam")
        if not anaam: foutmeldingen.append("Achternaam")
        if not id_nr: foutmeldingen.append("ID-Nummer")
        if not woonadres: foutmeldingen.append("Woonadres")
        if not tel: foutmeldingen.append("Telefoonnummer")
        if not email: foutmeldingen.append("E-mailadres")
        if not bericht: foutmeldingen.append("Omschrijving")
        if gekozen_tijd == "--- Selecteer een tijdstip ---": foutmeldingen.append("Tijdstip")

        if st.button("Verstuur Aanvraag"):
            if not foutmeldingen:
                # Alles is OK -> Opslaan en verzenden
                data = {
                    "voornaam": vnaam, "achternaam": anaam, "id_nummer": id_nr,
                    "woonadres": woonadres, "telefoon": tel, "email": email, 
                    "lad_nummer": lad_nr, "bericht": bericht, "afspraak_datum": str(datum),
                    "afspraak_tijd": gekozen_tijd, "status": "In behandeling"
                }
                supabase.table("aanvragen").insert(data).execute()
                
                # Mails versturen
                mail_body = f"Nieuwe afspraak DGW:\n\nNaam: {vnaam} {anaam}\nAdres: {woonadres}\nTel: {tel}\nAfspraak: {datum} om {gekozen_tijd}u"
                stuur_mail(st.secrets["EMAIL_USER"], f"Nieuwe Aanvraag: {vnaam}", mail_body, uploaded_files)
                stuur_mail(email, "DGW Bevestiging", f"Beste {vnaam}, uw afspraak is vastgelegd op {datum} om {gekozen_tijd}u.")
                
                st.success("✅ Uw aanvraag is succesvol ingediend! U ontvangt een bevestiging per mail.")
                st.balloons()
            else:
                # Toon precies wat er mist
                st.error(f"⚠️ Er ontbreekt nog informatie: {', '.join(foutmeldingen)}.")

elif menu == "Medewerker Portaal":
    st.subheader("Overzicht van alle aanvragen")
    res = supabase.table("aanvragen").select("*").execute()
    if res.data:
        df = pd.DataFrame(res.data)
        st.dataframe(df)

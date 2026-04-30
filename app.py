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

# Jouw specifieke groen/wit styling behouden
st.markdown("""
    <style>
    .tijd-knop { display: inline-block; padding: 10px; margin: 5px; border-radius: 5px; text-align: center; font-weight: bold; width: 85px; }
    .vrij { background-color: #e8f5e9; border: 2px solid #2e7d32; color: #2e7d32; }
    .bezet { background-color: #ffebee; border: 2px solid #c62828; color: #c62828; text-decoration: line-through; }
    .stButton>button { background-color: #2e7d32 !important; color: white !important; border-radius: 5px; width: 100%; height: 50px; font-size: 18px; border: none; }
    </style>
    """, unsafe_allow_html=True)

# Verbinding met de database
try:
    supabase = create_client(st.secrets["SUPABASE_URL"], st.secrets["SUPABASE_KEY"])
except:
    st.error("Database configuratie fout.")
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
        st.warning(f"Mailfout: {e}")

# --- 2. INTERFACE ---
st.title("📝 Dienst Grondzaken Wanica (DGW)")
menu = st.sidebar.radio("Navigatie", ["Cliënt Registratie", "Medewerker Portaal"])

if menu == "Cliënt Registratie":
    st.subheader("Nieuwe Aanvraag")
    
    # Gebruik van 'key' dwingt Streamlit om de waarden te onthouden
    col1, col2 = st.columns(2)
    with col1:
        vnaam = st.text_input("Voornaam *", key="vnaam")
        anaam = st.text_input("Achternaam *", key="anaam")
        id_nr = st.text_input("ID-Nummer *", key="id_nr")
        woonadres = st.text_input("Woonadres *", key="adres")
    with col2:
        tel = st.text_input("Telefoonnummer *", key="tel")
        email = st.text_input("E-mailadres *", key="email")
        lad_nr = st.text_input("LAD Nummer (optioneel)", key="lad")
    
    bericht = st.text_area("Omschrijving klacht/verzoek *", key="msg")
    uploaded_files = st.file_uploader("Documenten Uploaden", accept_multiple_files=True)

    st.write("---")
    st.subheader("📅 Beschikbaarheid")
    
    datum = st.date_input("Kies een datum", min_value=datetime.date.today())
    
    vrije_tijden = []
    
    # Alleen Maandag en Woensdag (0 en 2)
    if datum.weekday() not in [0, 2]:
        st.error("⚠️ Afspraken zijn uitsluitend op Maandag en Woensdag.")
    else:
        # Tijd slots van 07:30 tot 14:00
        tijden = [f"{h:02d}:{m:02d}" for h in range(7, 15) for m in [0, 15, 30, 45]]
        slots = [t for t in tijden if "07:30" <= t <= "14:00"]
        
        # Bezette tijden ophalen
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
    gekozen_tijd = st.selectbox("Selecteer uw tijdstip *", ["--- Maak een keuze ---"] + vrije_tijden, key="gekozen_tijd")

    if st.button("Verstuur Aanvraag"):
        # We controleren de ingevulde waarden direct uit de session_state
        s = st.session_state
        verplicht = [s.vnaam, s.anaam, s.id_nr, s.adres, s.tel, s.email, s.msg]
        
        if all(verplicht) and s.gekozen_tijd != "--- Maak een keuze ---":
            # Opslaan in de database
            data = {
                "voornaam": s.vnaam, "achternaam": s.anaam, "id_nummer": s.id_nr,
                "woonadres": s.adres, "telefoon": s.tel, "email": s.email, 
                "lad_nummer": s.lad, "bericht": s.msg, "afspraak_datum": str(datum),
                "afspraak_tijd": s.gekozen_tijd, "status": "In behandeling"
            }
            supabase.table("aanvragen").insert(data).execute()
            
            # E-mails naar medewerker en cliënt
            mail_body = f"Nieuwe aanvraag:\nNaam: {s.vnaam} {s.anaam}\nAdres: {s.adres}\nTel: {s.tel}\nDatum: {datum} om {s.gekozen_tijd}u"
            stuur_mail(st.secrets["EMAIL_USER"], f"DGW Aanvraag: {s.vnaam}", mail_body, uploaded_files)
            stuur_mail(s.email, "DGW Ontvangstbevestiging", f"Beste {s.vnaam}, uw afspraak voor {datum} om {s.gekozen_tijd}u is ontvangen.")
            
            st.success("✅ Uw aanvraag is succesvol ingediend!")
            st.balloons()
        else:
            # We tonen nu exact welk veld de app als 'leeg' ziet voor betere controle
            missende_velden = []
            if not s.vnaam: missende_velden.append("Voornaam")
            if not s.anaam: missende_velden.append("Achternaam")
            if not s.email: missende_velden.append("E-mailadres")
            if s.gekozen_tijd == "--- Maak een keuze ---": missende_velden.append("Tijdstip")
            
            st.error(f"⚠️ Er ontbreekt nog informatie: {', '.join(missende_velden)}.")

elif menu == "Medewerker Portaal":
    st.subheader("Overzicht Registraties")
    res = supabase.table("aanvragen").select("*").execute()
    if res.data:
        st.dataframe(pd.DataFrame(res.data))

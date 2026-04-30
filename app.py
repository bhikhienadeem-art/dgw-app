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

st.markdown("""
    <style>
    .stButton>button { background-color: #2e7d32; color: white; border-radius: 5px; width: 100%; height: 50px; font-size: 18px; border: none; }
    </style>
    """, unsafe_allow_html=True)

# Verbinding met Supabase
try:
    supabase = create_client(st.secrets["SUPABASE_URL"], st.secrets["SUPABASE_KEY"])
except Exception as e:
    st.error("Configuratie fout. Controleer uw secrets.")
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
        st.warning(f"E-mail niet verzonden: {e}")

# --- 2. INTERFACE ---
st.title("📝 Dienst Grondzaken Wanica (DGW)")
menu = st.sidebar.radio("Navigatie", ["Cliënt Registratie", "Medewerker Portaal"])

if menu == "Cliënt Registratie":
    st.subheader("Nieuwe Aanvraag")
    
    # Gebruik van st.form lost de validatiefout op de screenshots op
    with st.form("aanvraag_formulier", clear_on_submit=False):
        c1, c2 = st.columns(2)
        with c1:
            vnaam = st.text_input("Voornaam *")
            anaam = st.text_input("Achternaam *")
            id_nr = st.text_input("ID-Nummer *")
            woonadres = st.text_input("Woonadres *")
        with c2:
            tel = st.text_input("Telefoonnummer *")
            email = st.text_input("E-mailadres *")
            lad_nr = st.text_input("LAD Nummer (optioneel)")
        
        bericht = st.text_area("Omschrijving klacht/verzoek *")
        uploaded_files = st.file_uploader("Documenten Uploaden", accept_multiple_files=True)

        st.write("---")
        datum = st.date_input("Kies een datum", min_value=datetime.date.today())
        
        # Tijdslots ophalen (Alleen op Maandag en Woensdag)
        vrije_tijden = []
        if datum.weekday() in [0, 2]:
            tijden = [f"{h:02d}:{m:02d}" for h in range(7, 15) for m in [0, 15, 30, 45]]
            slots = [t for t in tijden if "07:30" <= t <= "14:00"]
            res = supabase.table("aanvragen").select("afspraak_tijd").eq("afspraak_datum", str(datum)).execute()
            bezet = [r['afspraak_tijd'] for r in res.data] if res.data else []
            vrije_tijden = [t for t in slots if t not in bezet]

        gekozen_tijd = st.selectbox("Selecteer tijdstip *", ["--- Kies een tijdstip ---"] + vrije_tijden)
        
        submit = st.form_submit_button("Verstuur Aanvraag")

        if submit:
            mist_info = []
            if not vnaam: mist_info.append("Voornaam")
            if not anaam: mist_info.append("Achternaam")
            if not id_nr: mist_info.append("ID-Nummer")
            if not woonadres: mist_info.append("Woonadres")
            if not tel: mist_info.append("Telefoonnummer")
            if not email: mist_info.append("E-mailadres")
            if not bericht: mist_info.append("Omschrijving")
            if gekozen_tijd == "--- Kies een tijdstip ---": mist_info.append("Tijdstip")

            if not mist_info:
                # DATA OPSLAAN
                payload = {
                    "voornaam": vnaam, "achternaam": anaam, "id_nummer": id_nr,
                    "woonadres": woonadres, "telefoon": tel, "email": email, 
                    "lad_nummer": lad_nr, "bericht": bericht, "afspraak_datum": str(datum),
                    "afspraak_tijd": gekozen_tijd, "status": "In behandeling"
                }
                supabase.table("aanvragen").insert(payload).execute()
                
                # MAILS VERSTUREN
                mail_tekst = f"Nieuwe aanvraag:\nNaam: {vnaam} {anaam}\nTel: {tel}\nAfspraak: {datum} om {gekozen_tijd}u"
                stuur_mail(st.secrets["EMAIL_USER"], f"Nieuwe Aanvraag: {vnaam}", mail_tekst, uploaded_files)
                stuur_mail(email, "Bevestiging DGW", f"Beste {vnaam}, uw afspraak is ontvangen voor {datum}.")
                
                st.success("✅ Uw aanvraag is succesvol ingediend!")
                st.balloons()
            else:
                st.error(f"⚠️ Er ontbreekt nog informatie: {', '.join(mist_info)}.")

elif menu == "Medewerker Portaal":
    st.subheader("Overzicht aanvragen")
    res = supabase.table("aanvragen").select("*").execute()
    if res.data:
        st.dataframe(pd.DataFrame(res.data))

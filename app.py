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
    .tijd-knop { display: inline-block; padding: 10px; margin: 5px; border-radius: 5px; text-align: center; font-weight: bold; width: 85px; }
    .vrij { background-color: #e8f5e9; border: 2px solid #2e7d32; color: #2e7d32; }
    .bezet { background-color: #ffebee; border: 2px solid #c62828; color: #c62828; text-decoration: line-through; }
    .stButton>button { background-color: #2e7d32; color: white; border-radius: 5px; width: 100%; height: 50px; }
    </style>
    """, unsafe_allow_html=True)

# Verbinding
supabase = create_client(st.secrets["SUPABASE_URL"], st.secrets["SUPABASE_KEY"])

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
        st.error(f"Mailfout: {e}")

# --- 2. INTERFACE ---
st.title("📝 Dienst Grondzaken Wanica (DGW)")
menu = st.sidebar.radio("Navigatie", ["Cliënt Registratie", "Medewerker Portaal"])

if menu == "Cliënt Registratie":
    st.subheader("Nieuwe Aanvraag")
    
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
    files = st.file_uploader("Documenten", accept_multiple_files=True)

    st.write("---")
    datum = st.date_input("Kies datum (Ma/Wo)", min_value=datetime.date.today())

    if datum.weekday() not in [0, 2]:
        st.error("Kies een Maandag of Woensdag.")
    else:
        # Tijd slots ophalen
        tijden = [f"{h:02d}:{m:02d}" for h in range(7, 15) for m in [0, 15, 30, 45]][2:-3] # 07:30 - 14:00
        res = supabase.table("aanvragen").select("afspraak_tijd").eq("afspraak_datum", str(datum)).execute()
        bezet = [r['afspraak_tijd'] for r in res.data] if res.data else []
        
        vrij = [t for t in tijden if t not in bezet]
        gekozen_tijd = st.selectbox("Selecteer tijdstip *", ["--- Kies een tijd ---"] + vrij)

        if st.button("Aanvraag indienen"):
            # STRENGE CONTROLE
            if vnaam and anaam and id_nr and woonadres and tel and email and bericht and gekozen_tijd != "--- Kies een tijd ---":
                # Opslaan
                payload = {
                    "voornaam": vnaam, "achternaam": anaam, "id_nummer": id_nr,
                    "woonadres": woonadres, "telefoon": tel, "email": email, 
                    "lad_nummer": lad_nr, "bericht": bericht, "afspraak_datum": str(datum),
                    "afspraak_tijd": gekozen_tijd, "status": "In behandeling"
                }
                supabase.table("aanvragen").insert(payload).execute()
                
                # Mails
                inhoud = f"Nieuwe aanvraag: {vnaam} {anaam}\nID: {id_nr}\nAdres: {woonadres}\nTel: {tel}\nBericht: {bericht}\nDatum: {datum} om {gekozen_tijd}u"
                stuur_mail(st.secrets["EMAIL_USER"], f"Nieuwe Aanvraag: {vnaam}", inhoud, files)
                stuur_mail(email, "DGW Bevestiging", f"Beste {vnaam}, uw aanvraag voor {datum} om {gekozen_tijd}u is ontvangen.")
                
                st.success("✅ Geregistreerd! De medewerker heeft de mail ontvangen.")
                st.balloons()
            else:
                st.error("⚠️ Vul a.u.b. alle velden met een sterretje (*) in, inclusief het tijdstip.")

elif menu == "Medewerker Portaal":
    st.subheader("Dossiers")
    res = supabase.table("aanvragen").select("*").execute()
    if res.data:
        st.dataframe(pd.DataFrame(res.data))

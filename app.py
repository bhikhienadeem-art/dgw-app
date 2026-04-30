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

st.markdown("""
    <style>
    .tijd-knop { display: inline-block; padding: 10px; margin: 5px; border-radius: 5px; text-align: center; font-weight: bold; width: 85px; }
    .vrij { background-color: #e8f5e9; border: 2px solid #2e7d32; color: #2e7d32; }
    .bezet { background-color: #ffebee; border: 2px solid #c62828; color: #c62828; text-decoration: line-through; }
    .stButton>button { background-color: #2e7d32; color: white; border-radius: 5px; width: 100%; height: 50px; font-size: 18px; }
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
        st.warning(f"Mailfout: {e}")

# --- 2. INTERFACE ---
st.title("📝 Dienst Grondzaken Wanica (DGW)")
menu = st.sidebar.radio("Navigatie", ["Cliënt Registratie", "Medewerker Portaal"])

if menu == "Cliënt Registratie":
    st.subheader("Nieuwe Aanvraag")
    
    # Gebruik session_state om te voorkomen dat velden "verdwijnen" voor de code
    c1, c2 = st.columns(2)
    with c1:
        vnaam = st.text_input("Voornaam *", key="vn")
        anaam = st.text_input("Achternaam *", key="an")
        id_nr = st.text_input("ID-Nummer *", key="id")
        woonadres = st.text_input("Woonadres *", key="wa")
    with c2:
        tel = st.text_input("Telefoonnummer *", key="tl")
        email = st.text_input("E-mailadres *", key="em")
        lad_nr = st.text_input("LAD Nummer (optioneel)", key="lad")
    
    bericht = st.text_area("Omschrijving klacht/verzoek *", key="msg")
    uploaded_files = st.file_uploader("Documenten Uploaden", accept_multiple_files=True)

    st.write("---")
    datum = st.date_input("Kies een datum", min_value=datetime.date.today())

    if datum.weekday() not in [0, 2]:
        st.error("Kies een Maandag of Woensdag.")
    else:
        tijden = [f"{h:02d}:{m:02d}" for h in range(7, 15) for m in [0, 15, 30, 45]]
        slots = [t for t in tijden if "07:30" <= t <= "14:00"]
        
        res = supabase.table("aanvragen").select("afspraak_tijd").eq("afspraak_datum", str(datum)).execute()
        bezet = [r['afspraak_tijd'] for r in res.data] if res.data else []
        vrij = [t for t in slots if t not in bezet]
        
        gekozen_tijd = st.selectbox("Selecteer tijdstip *", ["Kies een tijd"] + vrij, key="tijd")

        if st.button("Verstuur Aanvraag"):
            # We controleren direct de session_state waarden
            verplicht = [st.session_state.vn, st.session_state.an, st.session_state.id, 
                         st.session_state.wa, st.session_state.tl, st.session_state.em, 
                         st.session_state.msg]
            
            if all(verplicht) and st.session_state.tijd != "Kies een tijd":
                # Opslaan
                data = {
                    "voornaam": st.session_state.vn, "achternaam": st.session_state.an, 
                    "id_nummer": st.session_state.id, "woonadres": st.session_state.wa, 
                    "telefoon": st.session_state.tl, "email": st.session_state.em, 
                    "lad_nummer": st.session_state.lad, "bericht": st.session_state.msg, 
                    "afspraak_datum": str(datum), "afspraak_tijd": st.session_state.tijd, 
                    "status": "In behandeling"
                }
                supabase.table("aanvragen").insert(data).execute()
                
                # Mails
                inhoud = f"Nieuwe aanvraag van {st.session_state.vn} {st.session_state.an}\nDatum: {datum} om {st.session_state.tijd}u"
                stuur_mail(st.secrets["EMAIL_USER"], f"Aanvraag: {st.session_state.vn}", inhoud, uploaded_files)
                stuur_mail(st.session_state.em, "Bevestiging DGW", "Uw aanvraag is ontvangen.")
                
                st.success("✅ Alles is succesvol verzonden!")
                st.balloons()
            else:
                st.error("⚠️ Er ontbreekt nog informatie. Controleer alle velden met een sterretje.")

elif menu == "Medewerker Portaal":
    st.subheader("Dossier Overzicht")
    res = supabase.table("aanvragen").select("*").execute()
    if res.data:
        st.dataframe(pd.DataFrame(res.data))

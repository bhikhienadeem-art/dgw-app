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

try:
    st.sidebar.image("orgineel logo Centrum.png", use_container_width=True)
except:
    st.sidebar.warning("Logo bestand niet gevonden.")

# Verbinding met Supabase
try:
    supabase = create_client(st.secrets["SUPABASE_URL"], st.secrets["SUPABASE_KEY"])
except:
    st.error("Configuratie fout in Secrets.")
    st.stop()

# --- PROFESSIONELE MAIL FUNCTIE ---
def stuur_mail(ontvanger, onderwerp, inhoud, bestanden=None):
    try:
        msg = MIMEMultipart()
        msg['Subject'] = onderwerp
        msg['From'] = f"DGW Wanica <{st.secrets['EMAIL_USER']}>"
        msg['To'] = ontvanger
        
        # Nette HTML-achtige opmaak in tekstvorm
        body = f"""
Geachte cliënt,

{inhoud}

Mocht u nog vragen hebben, dan kunt u contact opnemen met ons kantoor.

Met vriendelijke groet,

Districtscommissariaat Wanica Centrum
Afdeling Grondzaken (DGW)
Lelydorp, Suriname
        """
        msg.attach(MIMEText(body, 'plain'))
        
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
        st.error(f"Mail kon niet worden verzonden: {e}")

# --- 2. LOGIN SYSTEEM ---
if 'logged_in' not in st.session_state:
    st.session_state.logged_in = False
    st.session_state.role = None
    st.session_state.user = None

def login():
    st.sidebar.subheader("🔐 Inloggen Medewerker")
    try:
        res = supabase.table("medewerkers").select("*").execute()
        user_list = [u['gebruikersnaam'] for u in res.data] if res.data else []
        selected_user = st.sidebar.selectbox("Selecteer Gebruiker", ["--- Kies ---"] + user_list)
        password = st.sidebar.text_input("Wachtwoord", type="password")
        if st.sidebar.button("Inloggen"):
            user_data = next((u for u in res.data if u['gebruikersnaam'] == selected_user), None)
            if user_data and user_data['wachtwoord'] == password:
                st.session_state.logged_in = True
                st.session_state.role = user_data['rol'] # Haalt 'Admin' of 'Medewerker' op
                st.session_state.user = selected_user
                st.rerun()
            else:
                st.sidebar.error("Onjuist wachtwoord")
    except Exception as e:
        st.sidebar.error(f"Fout bij laden gebruikers: {e}")

# --- 3. NAVIGATIE MENU ---
menu_options = ["Cliënt Registratie"]

if st.session_state.logged_in:
    menu_options += ["Medewerker Portaal", "Agenda Overzicht", "Rapportages"]
    
    # Controleer op Admin rol (ongeacht hoofdletters)
    if str(st.session_state.role).lower() == "admin":
        menu_options.append("Admin Instellingen")
        
    if st.sidebar.button("🚪 Uitloggen"):
        st.session_state.logged_in = False
        st.session_state.role = None
        st.rerun()
else:
    login()

menu = st.sidebar.radio("Navigatie", menu_options)

# --- 4. PAGINA'S ---

if menu == "Cliënt Registratie":
    st.header("📝 Nieuwe Aanvraag DGW")
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
    datum = st.date_input("Kies een datum voor uw afspraak", min_value=datetime.date.today())
    
    if datum.weekday() not in [0, 2]: # Maandag=0, Woensdag=2
        st.error("⚠️ Afspraken zijn uitsluitend op Maandag en Woensdag mogelijk.")
    else:
        # Tijdstippen ophalen
        tijden = [f"{h:02d}:{m:02d}" for h in range(7, 15) for m in [0, 15, 30, 45]]
        slots = [t for t in tijden if "07:00" <= t <= "14:45"]
        res = supabase.table("aanvragen").select("afspraak_tijd").eq("afspraak_datum", str(datum)).execute()
        bezet = [r['afspraak_tijd'] for r in res.data] if res.data else []
        vrije_tijden = [t for t in slots if t not in bezet]
        
        gekozen_tijd = st.selectbox("Selecteer een tijdstip *", ["--- Kies ---"] + vrije_tijden)

        if st.button("Aanvraag Verzenden"):
            if all([vnaam, anaam, id_nr, woonadres, tel, email, bericht]) and gekozen_tijd != "--- Kies ---":
                data = {
                    "voornaam": vnaam, "achternaam": anaam, "id_nummer": id_nr, "woonadres": woonadres, 
                    "telefoon": tel, "email": email, "lad_nummer": lad_nr, "bericht": bericht, 
                    "afspraak_datum": str(datum), "afspraak_tijd": gekozen_tijd, "status": "In behandeling"
                }
                supabase.table("aanvragen").insert(data).execute()
                
                # Klant mail
                inhoud_klant = f"Uw aanvraag voor een afspraak op {datum} om {gekozen_tijd} uur is succesvol ontvangen. Onze medewerkers zullen uw verzoek spoedig beoordelen."
                stuur_mail(email, "Bevestiging Ontvangst Aanvraag", inhoud_klant)
                
                # Medewerker mail
                stuur_mail(st.secrets["EMAIL_USER"], f"Nieuwe Aanvraag: {vnaam} {anaam}", f"Nieuwe aanvraag van {vnaam} {anaam} voor {datum}.", bestanden=uploaded_files)
                
                st.success("✅ Uw aanvraag is verzonden. U ontvangt een e-mail ter bevestiging.")
                st.balloons()
            else:
                st.error("⚠️ Vul alle verplichte velden in.")

elif menu == "Medewerker Portaal":
    st.header("📋 Beheer van Aanvragen")
    res = supabase.table("aanvragen").select("*").order('created_at', desc=True).execute()
    if res.data:
        df = pd.DataFrame(res.data)
        st.dataframe(df, use_container_width=True)
        
        st.write("---")
        selected_id = st.selectbox("Kies een aanvraag om te beheren (ID)", df['id'].tolist())
        
        col_up, col_del = st.columns(2)
        with col_up:
            nieuwe_status = st.selectbox("Nieuwe Status", ["Bevestigd", "In behandeling", "Geannuleerd", "Verwezen"])
            if st.button("Status Bijwerken"):
                supabase.table("aanvragen").update({"status": nieuwe_status}).eq("id", selected_id).execute()
                # Mail naar klant bij update
                aanvraag = next(item for item in res.data if item['id'] == selected_id)
                stuur_mail(aanvraag['email'], "Update status van uw aanvraag", f"De status van uw aanvraag is bijgewerkt naar: {nieuwe_status}.")
                st.success(f"Status van ID {selected_id} aangepast naar {nieuwe_status}")
                st.rerun()

        with col_del:
            st.warning("⚠️ Dit verwijdert de klant definitief!")
            if st.button("🗑️ Verwijder deze aanvraag"):
                supabase.table("aanvragen").delete().eq("id", selected_id).execute()
                st.success("Aanvraag verwijderd.")
                st.rerun()

elif menu == "Admin Instellingen":
    st.header("⚙️ Gebruikersbeheer (Admin Only)")
    
    # Medewerker Toevoegen
    with st.expander("➕ Nieuwe Medewerker Toevoegen"):
        n_user = st.text_input("Gebruikersnaam")
        n_pass = st.text_input("Wachtwoord", type="password")
        n_rol = st.selectbox("Rol", ["Medewerker", "Admin"])
        if st.button("Account Aanmaken"):
            supabase.table("medewerkers").insert({"gebruikersnaam": n_user, "wachtwoord": n_pass, "rol": n_rol}).execute()
            st.success("Gebruiker toegevoegd!")
            st.rerun()

    # Lijst en Verwijderen
    st.write("### Huidige Medewerkers")
    res_m = supabase.table("medewerkers").select("*").execute()
    if res_m.data:
        df_m = pd.DataFrame(res_m.data)
        st.table(df_m[['gebruikersnaam', 'rol']])
        
        user_to_del = st.selectbox("Kies account om te verwijderen", df_m['gebruikersnaam'].tolist())
        if st.button("❌ Verwijder Account"):
            if user_to_del != st.session_state.user:
                supabase.table("medewerkers").delete().eq("gebruikersnaam", user_to_del).execute()
                st.success("Gebruiker verwijderd.")
                st.rerun()
            else:
                st.error("Je kunt je eigen account niet verwijderen!")

# Andere menu's (Agenda & Rapportages) kunnen hier worden aangevuld indien nodig.

import streamlit as st
from supabase import create_client, Client
import datetime
import pandas as pd
import smtplib
from email.mime.text import MIMEText
from email.mime.multipart import MIMEMultipart
from streamlit_calendar import calendar

# --- 1. CONFIGURATIE & TITEL ---
st.set_page_config(page_title="Registratie Dienst Grondzaken Wanica Centrum", layout="wide")

# Verbinding met Supabase
supabase = create_client(st.secrets["SUPABASE_URL"], st.secrets["SUPABASE_KEY"])

# Styling
st.markdown("""
    <style>
    .stButton>button { background-color: #2e7d32 !important; color: white !important; border-radius: 5px; }
    .main { background-color: #f8f9fa; }
    </style>
    """, unsafe_allow_html=True)

# --- HELPER FUNCTIES ---
def stuur_mail(ontvanger, onderwerp, inhoud):
    try:
        msg = MIMEMultipart()
        msg['Subject'] = onderwerp
        msg['From'] = f"DGW Centrum <{st.secrets['EMAIL_USER']}>"
        msg['To'] = ontvanger
        msg.attach(MIMEText(inhoud + "\n\n---\nDistrictscommissariaat Wanica-Centrum", 'plain'))
        with smtplib.SMTP_SSL('smtp.gmail.com', 465) as server:
            server.login(st.secrets["EMAIL_USER"], st.secrets["EMAIL_PASS"])
            server.send_message(msg)
    except Exception as e:
        st.error(f"Mail fout: {e}")

# --- 2. AUTHENTICATIE ---
if 'logged_in' not in st.session_state:
    st.session_state.update({'logged_in': False, 'role': None, 'user': None})

if not st.session_state.logged_in:
    st.sidebar.subheader("🔐 Medewerker Login")
    res_m = supabase.table("medewerkers").select("*").execute()
    user_list = [u['gebruikersnaam'] for u in res_m.data] if res_m.data else []
    u_sel = st.sidebar.selectbox("Gebruiker", ["---"] + user_list)
    p_inp = st.sidebar.text_input("Wachtwoord", type="password")
    if st.sidebar.button("Inloggen"):
        user_data = next((u for u in res_m.data if u['gebruikersnaam'] == u_sel), None)
        if user_data and user_data['wachtwoord'] == p_inp:
            st.session_state.update({'logged_in': True, 'role': user_data['rol'], 'user': u_sel})
            st.rerun()

# --- 3. MENU ---
menu_options = ["Nieuwe Aanvraag DGW"]
if st.session_state.logged_in:
    menu_options += ["Beheer Registraties", "Agenda", "Rapportages", "Systeembeheer"]
    if st.sidebar.button("🚪 Uitloggen"):
        st.session_state.logged_in = False
        st.rerun()

menu = st.sidebar.radio("Hoofdmenu", menu_options)

# --- 4. PAGINA'S ---

if menu == "Nieuwe Aanvraag DGW":
    st.header("📝 Registratie Dienst Grondzaken Wanica Centrum")
    # ... (Bestaande code voor aanvragen blijft gelijk)
    col1, col2 = st.columns(2)
    with col1:
        vnaam = st.text_input("Voornaam *")
        anaam = st.text_input("Achternaam *")
        email = st.text_input("E-mailadres *")
    with col2:
        id_nr = st.text_input("ID-Nummer *")
        tel = st.text_input("Telefoonnummer *")
        lad_nr = st.text_input("LAD Nummer")
    
    bericht = st.text_area("Omschrijving van uw verzoek *")
    st.file_uploader("Documenten uploaden", accept_multiple_files=True)
    
    datum = st.date_input("Kies een datum", min_value=datetime.date.today())
    
    if datum.weekday() not in [0, 2]:
        st.warning("⚠️ Afspraken zijn enkel mogelijk op maandag en woensdag.")
    else:
        st.subheader("⏰ Beschikbare Tijden")
        tijdsblokken = [f"{h:02d}:{m:02d}" for h in range(8, 15) for m in (0, 15, 30, 45) if not (h == 14 and m > 30)]
        res_t = supabase.table("aanvragen").select("afspraak_tijd").eq("afspraak_datum", str(datum)).execute()
        bezet = [r['afspraak_tijd'] for r in res_t.data] if res_t.data else []
        
        cols = st.columns(6)
        for i, tijd in enumerate(tijdsblokken):
            is_bezet = tijd in bezet
            if cols[i % 6].button(f"🚫 {tijd}" if is_bezet else tijd, key=f"t_{tijd}", disabled=is_bezet):
                st.session_state.sel_tijd = tijd
        
        if 'sel_tijd' in st.session_state:
            st.info(f"Geselecteerd: **{st.session_state.sel_tijd}**")

    if st.button("Registratie Verzenden"):
        if all([vnaam, anaam, email, id_nr, bericht]) and 'sel_tijd' in st.session_state:
            supabase.table("aanvragen").insert({
                "voornaam": vnaam, "achternaam": anaam, "email": email, "id_nummer": id_nr,
                "telefoon": tel, "lad_nummer": lad_nr, "afspraak_datum": str(datum),
                "afspraak_tijd": st.session_state.sel_tijd, "status": "In behandeling", "bericht": bericht
            }).execute()
            st.success("✅ Succesvol geregistreerd!")
            del st.session_state.sel_tijd
        else:
            st.error("Vul alle velden in.")

elif menu == "Beheer Registraties":
    st.header("📋 Cliëntendossiers Beheren")
    res = supabase.table("aanvragen").select("*").order('created_at', desc=True).execute()
    if res.data:
        df = pd.DataFrame(res.data)
        st.dataframe(df[['id', 'voornaam', 'achternaam', 'status', 'afspraak_datum']])
        
        sel_id = st.selectbox("Selecteer Dossier ID", df['id'].tolist())
        reg = next(item for item in res.data if item['id'] == sel_id)

        with st.expander("⚠️ Dossier Verwijderen"):
            if st.button(f"Bevestig verwijderen van dossier {sel_id}"):
                supabase.table("aanvragen").delete().eq("id", sel_id).execute()
                st.success("Dossier verwijderd.")
                st.rerun()

        with st.form("update_dossier"):
            stat = st.selectbox("Status", ["Bevestigd", "In behandeling", "Afgehandeld", "Geannuleerd", "Verwezen"], index=0)
            beh_optie = st.selectbox("Afgehandeld?", ["Nee", "Ja"], index=1 if reg.get('behandeld') else 0)
            verslag = st.text_area("Intern verslag", value=str(reg.get('intern_verslag') or ""))
            mail_tekst = st.text_area("Update mail naar cliënt")
            
            if st.form_submit_button("Wijzigingen Opslaan"):
                is_beh = (beh_optie == "Ja")
                supabase.table("aanvragen").update({"status": stat, "behandeld": is_beh, "intern_verslag": verslag}).eq("id", sel_id).execute()
                if mail_tekst:
                    stuur_mail(reg['email'], "Update Grondzaken", mail_tekst)
                st.success("Bijgewerkt.")
                st.rerun()

elif menu == "Rapportages":
    st.header("📊 Management Rapportages")
    res = supabase.table("aanvragen").select("*").execute()
    if res.data:
        df_rep = pd.DataFrame(res.data)
        st.dataframe(df_rep)
        st.download_button("📥 Exporteer CSV", data=df_rep.to_csv(index=False), file_name="dgw_export.csv")

elif menu == "Agenda":
    st.header("📅 Agenda")
    res = supabase.table("aanvragen").select("*").execute()
    if res.data:
        events = [{"title": f"{r['voornaam']} {r['achternaam']}", "start": r['afspraak_datum']} for r in res.data]
        calendar(events=events)

# --- NIEUWE UITGEBREIDE SYSTEEMBEHEER ---
elif menu == "Systeembeheer":
    st.header("⚙️ Beheer Medewerkers")
    
    # Haal huidige medewerkers op
    res_m = supabase.table("medewerkers").select("*").execute()
    medewerkers_df = pd.DataFrame(res_m.data) if res_m.data else pd.DataFrame()

    # 1. Medewerker Toevoegen
    with st.expander("➕ Nieuwe Medewerker Toevoegen"):
        with st.form("new_user_form"):
            new_u = st.text_input("Gebruikersnaam")
            new_p = st.text_input("Wachtwoord", type="password")
            new_r = st.selectbox("Rol", ["Medewerker", "Admin"])
            if st.form_submit_button("Account Aanmaken"):
                if new_u and new_p:
                    supabase.table("medewerkers").insert({"gebruikersnaam": new_u, "wachtwoord": new_p, "rol": new_r}).execute()
                    st.success(f"Medewerker {new_u} toegevoegd!")
                    st.rerun()
                else:
                    st.error("Vul alle velden in.")

    # 2. Medewerkers beheren (Wachtwoord wijzigen of Verwijderen)
    if not medewerkers_df.empty:
        st.subheader("👥 Bestaande Accounts")
        for index, row in medewerkers_df.iterrows():
            with st.container():
                c1, c2, c3 = st.columns([2, 2, 1])
                c1.write(f"**{row['gebruikersnaam']}** ({row['rol']})")
                
                # Wachtwoord wijzigen
                with c2.popover("🔑 Wachtwoord wijzigen"):
                    new_pass = st.text_input(f"Nieuw wachtwoord voor {row['gebruikersnaam']}", type="password", key=f"p_{row['id']}")
                    if st.button("Opslaan", key=f"s_{row['id']}"):
                        supabase.table("medewerkers").update({"wachtwoord": new_pass}).eq("id", row['id']).execute()
                        st.success("Wachtwoord gewijzigd.")
                
                # Verwijderen
                if c3.button("🗑️ Verwijder", key=f"d_{row['id']}"):
                    if row['gebruikersnaam'] == st.session_state.user:
                        st.error("Je kunt je eigen account niet verwijderen terwijl je bent ingelogd.")
                    else:
                        supabase.table("medewerkers").delete().eq("id", row['id']).execute()
                        st.success("Account verwijderd.")
                        st.rerun()
                st.divider()
    else:
        st.info("Geen medewerkers gevonden.")

import streamlit as st
from supabase import create_client, Client
import datetime
import pandas as pd
import plotly.express as px
import smtplib
from email.mime.text import MIMEText
from email.mime.multipart import MIMEMultipart
from email.mime.application import MIMEApplication

# --- 1. CONFIGURATIE ---
st.set_page_config(page_title="Dienst Grondzaken Wanica Centrum", layout="wide")

supabase = create_client(st.secrets["SUPABASE_URL"], st.secrets["SUPABASE_KEY"])

EMAIL_USER = "wanicacentrum.gz@gmail.com"
EMAIL_PASS = "kmebjorjujxwqbvo"

# --- 2. STYLING ---
st.markdown("""
    <style>
    .stApp { background-color: white; }
    h1, h2, h3, .stTitle { color: #1b5e20 !important; font-family: 'Segoe UI', sans-serif; font-weight: bold; }
    [data-testid="stSidebar"] { background-color: #f1f8e9 !important; }
    [data-testid="stSidebar"] .st-emotion-cache-17l69uz, [data-testid="stSidebar"] p, [data-testid="stSidebar"] label {
        color: #1b5e20 !important; font-weight: bold !important;
    }
    .stTextInput>div>div>input, .stTextArea>div>div>textarea, .stSelectbox>div>div>div {
        background-color: white !important; color: black !important; border: 2px solid #2e7d32 !important; border-radius: 8px !important;
    }
    div.stButton > button { width: 100%; border-radius: 10px; background-color: #2e7d32; color: white; font-weight: bold; height: 3.5em; }
    </style>
""", unsafe_allow_html=True)

# --- 3. EMAIL FUNCTIE ---
def stuur_mail(ontvanger, onderwerp, inhoud, bestanden=None):
    msg = MIMEMultipart()
    msg['From'] = f"Dienst Grondzaken Wanica Centrum <{EMAIL_USER}>"
    msg['To'] = ontvanger
    msg['Subject'] = onderwerp
    html = f"<html><body style='font-family: Arial;'>{inhoud.replace('\\n', '<br>')}</body></html>"
    msg.attach(MIMEText(html, 'html'))
    if bestanden:
        for f in bestanden:
            f.seek(0)
            part = MIMEApplication(f.read(), Name=f.name)
            part['Content-Disposition'] = f'attachment; filename="{f.name}"'
            msg.attach(part)
    try:
        server = smtplib.SMTP('smtp.gmail.com', 587)
        server.starttls(); server.login(EMAIL_USER, EMAIL_PASS)
        server.send_message(msg); server.quit()
        return True
    except: return False

# --- 4. STATE INITIALISATIE ---
if 'logged_in' not in st.session_state:
    st.session_state.update({'logged_in': False, 'role': None, 'user': None})

# --- 5. HOOFDMENU EN LOGICA ---
if not st.session_state.logged_in:
    # Menu voor cliënten
    menu = st.sidebar.radio("Hoofdmenu", ["📝 Nieuwe Registratie", "🔐 Medewerker Login"])
    
    if menu == "📝 Nieuwe Registratie":
        st.image("https://raw.githubusercontent.com/bhikhienadeem-art/dgw-app/main/orgineel%20logo%20Centrum.png", width=120)
        st.title("Registratie Grondzaken")
        
        with st.form("registratie_form", clear_on_submit=True):
            col1, col2 = st.columns(2)
            with col1:
                v_naam = st.text_input("Voornaam *")
                a_naam = st.text_input("Achternaam *")
                email = st.text_input("E-mailadres *")
                tel = st.text_input("Telefoonnummer *")
            with col2:
                id_nr = st.text_input("ID-nummer *")
                woonadres = st.text_input("Woonadres *")
                lad_nr = st.text_input("LAD-nummer")
                d_keuze = st.date_input("Kies datum", min_value=datetime.date.today())
                t_keuze = st.selectbox("Tijdstip", ["08:00", "09:00", "10:00", "11:00", "12:00"])

            bericht = st.text_area("Omschrijving klacht/verzoek *")
            
            st.subheader("📁 Documenten Uploaden")
            uploads = st.file_uploader("Kies bestanden", accept_multiple_files=True)
            
            if st.form_submit_button("✅ REGISTRATIE VERZENDEN"):
                if d_keuze.weekday() not in [0, 2]:
                    st.error("Afspraken zijn alleen mogelijk op maandag of woensdag.")
                elif v_naam and a_naam and email and id_nr and woonadres and bericht:
                    reg_data = {
                        "voornaam": v_naam, "achternaam": a_naam, "email": email, 
                        "telefoon": tel, "id_nummer": id_nr, "woonadres": woonadres,
                        "lad_nummer": lad_nr, "bericht": bericht, 
                        "afspraak_datum": str(d_keuze), "afspraak_tijd": t_keuze,
                        "status": "In behandeling"
                    }
                    supabase.table("aanvragen").insert(reg_data).execute()
                    st.success(f"Registratie voltooid! Afspraak op {d_keuze} om {t_keuze}.")
                else:
                    st.error("Vul a.u.b. alle velden met een * in.")

    elif menu == "🔐 Medewerker Login":
        st.subheader("Medewerker Login")
        user_inp = st.text_input("Gebruikersnaam")
        pass_inp = st.text_input("Wachtwoord", type="password")
        if st.button("Inloggen"):
            res = supabase.table("medewerkers").select("*").eq("gebruikersnaam", user_inp).eq("wachtwoord", pass_inp).execute()
            if res.data:
                user = res.data[0]
                st.session_state.update({'logged_in': True, 'role': user['rol'].lower(), 'user': user['gebruikersnaam']})
                st.rerun()
            else:
                st.error("Onjuiste inloggegevens.")

else:
    # Menu voor ingelogde medewerkers
    st.sidebar.success(f"Ingelogd: {st.session_state.user} ({st.session_state.role})")
    menu = st.sidebar.radio("Navigatie", ["📊 Dashboard", "📅 Agenda", "📋 Dossierbeheer", "⚙️ Systeembeheer"])
    
    if st.sidebar.button("🚪 Uitloggen"):
        st.session_state.update({'logged_in': False, 'role': None, 'user': None})
        st.rerun()

    # --- DASHBOARD ---
    if menu == "📊 Dashboard":
        st.header("📊 Dashboard & Rapportages")
        res = supabase.table("aanvragen").select("*").execute()
        if res.data:
            df = pd.DataFrame(res.data)
            col1, col2 = st.columns(2)
            with col1:
                st.plotly_chart(px.pie(df, names='status', title="Status Verdeling"), use_container_width=True)
            with col2:
                df['datum'] = pd.to_datetime(df['created_at']).dt.date
                st.plotly_chart(px.bar(df.groupby('datum').size().reset_index(name='aantal'), x='datum', y='aantal'), use_container_width=True)
            
            st.subheader("Volledige Export")
            csv = df.to_csv(index=False).encode('utf-8')
            st.download_button("📥 Download Rapportage (CSV)", csv, "rapport.csv", "text/csv")

    # --- AGENDA ---
    elif menu == "📅 Agenda":
        st.header("📅 Agenda")
        res = supabase.table("aanvragen").select("*").order('afspraak_datum').execute()
        if res.data:
            df_ag = pd.DataFrame(res.data)
            st.dataframe(df_ag[['afspraak_datum', 'afspraak_tijd', 'voornaam', 'achternaam', 'status']], use_container_width=True)

# --- 7. DOSSIERBEHEER (HERSTELD: INTERN + EMAIL) ---
elif menu == "📋 Dossierbeheer":
    st.header("📋 Dossierbeheer")
    
    # Gegevens ophalen uit de database
    res = supabase.table("aanvragen").select("*").order('id', desc=True).execute()
    
    if res.data:
        df = pd.DataFrame(res.data)
        # Toon de vertrouwde tabelweergave bovenaan
        st.dataframe(df[['id', 'voornaam', 'achternaam', 'status', 'afspraak_datum']], use_container_width=True)
        
        sel_id = st.selectbox("Selecteer Dossier ID", df['id'].tolist())
        d = next(item for item in res.data if item['id'] == sel_id)
        
        st.markdown(f"### 📄 Dossier #{sel_id}: {d['voornaam']} {d['achternaam']}")
        
        # Informatie sectie
        col_info1, col_info2 = st.columns(2)
        with col_info1:
            st.write(f"**ID-nummer:** {d.get('id_nummer', 'N/A')}")
            st.write(f"**E-mail:** {d['email']}")
        with col_info2:
            st.write(f"**Afspraak:** {d['afspraak_datum']} om {d.get('afspraak_tijd', 'N/A')}")
        
        st.info(f"**Klacht:** {d['bericht']}")
        st.divider()
        
        # --- BEHEER: TWEE APARTE VELDEN ---
        col_intern, col_client = st.columns(2)
        
        with col_intern:
            st.subheader("📝 Interne Notitie")
            n_status = st.selectbox(
                "Status", 
                ["In behandeling", "Wacht op documenten", "Bevestigd", "Afgehandeld"],
                index=["In behandeling", "Wacht op documenten", "Bevestigd", "Afgehandeld"].index(d['status']) if d['status'] in ["In behandeling", "Wacht op documenten", "Bevestigd", "Afgehandeld"] else 0
            )
            # Bericht alleen voor de medewerker zelf
            interne_tekst = st.text_area(
                "Notitie voor medewerker (Intern)", 
                value=d.get('medewerker_toelichting', ""),
                key="intern_box"
            )
        
        with col_client:
            st.subheader("📧 Bericht naar Cliënt")
            # Bericht dat als e-mail wordt verstuurd
            email_tekst = st.text_area(
                "Inhoud e-mail voor cliënt", 
                placeholder="Typ hier de tekst voor de cliënt...",
                key="email_box"
            )

        # Actie knoppen (Groen voor bijwerken, Grijs voor verwijderen)
        btn_update, btn_delete = st.columns(2)
        with btn_update:
            if st.button("💾 BIJWERKEN & MAILEN", use_container_width=True):
                # Sla status en interne notitie op
                supabase.table("aanvragen").update({
                    "status": n_status, 
                    "medewerker_toelichting": interne_tekst
                }).eq("id", sel_id).execute()
                
                # Verzend mail alleen als er tekst is ingevuld voor de cliënt
                if email_tekst:
                    onderwerp = f"Update Dossier #{sel_id}"
                    inhoud = f"Beste {d['voornaam']},\n\nUw dossier is bijgewerkt naar: {n_status}.\n\nBericht:\n{email_tekst}"
                    stuur_mail(d['email'], onderwerp, inhoud)
                    st.success("Opgeslagen en mail verzonden!")
                else:
                    st.success("Interne notitie opgeslagen.")
                st.rerun()
                
        with btn_delete:
            if st.button(f"🗑️ VERWIJDER DOSSIER #{sel_id}", type="secondary", use_container_width=True):
                supabase.table("aanvragen").delete().eq("id", sel_id).execute()
                st.warning("Dossier verwijderd.")
                st.rerun()
    else:
        st.info("Geen dossiers gevonden.")

    # --- SYSTEEMBEHEER ---
    elif menu == "⚙️ Systeembeheer":
        if st.session_state.role == 'admin':
            st.header("⚙️ Systeembeheer")
            # Medewerkersbeheer code hier...
        else:
            st.error("Geen toegang.")

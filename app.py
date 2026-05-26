import plotly.express as px
import streamlit as st
from supabase import create_client, Client
import datetime
import pandas as pd
import smtplib
from email.mime.text import MIMEText
from email.mime.multipart import MIMEMultipart
from email.mime.application import MIMEApplication

# --- 1. CONFIGURATIE ---
st.set_page_config(page_title="Registratie Dienst Grondzaken Wanica Centrum", layout="wide")

supabase = create_client(st.secrets["SUPABASE_URL"], st.secrets["SUPABASE_KEY"])

EMAIL_USER = "wanicacentrum.gz@gmail.com"
EMAIL_PASS = "kmebjorjujxwqbvo"

# --- 2. STYLING ---
st.markdown("""
    <style>
    .stApp { background-color: white; }
    h1, h2, h3 { color: #2e7d32 !important; font-weight: bold; }
    input, textarea, [data-baseweb="select"] > div {
        background-color: white !important;
        color: black !important;
        border: 1px solid #2e7d32 !important;
    }
    label p {
        color: #1b5e20 !important;
        font-weight: bold !important;
    }
    .stButton>button { 
        background-color: #2e7d32 !important; 
        color: white !important; 
        border-radius: 5px; 
        font-weight: bold;
    }
    [data-testid="stSidebar"] { background-color: #f1f8e9 !important; }
    button[data-testid="stBaseButton-secondary"] {
        background-color: #d32f2f !important;
        color: white !important;
        border: none !important;
    }
    .stDataFrame { color: black !important; }
    </style>
""", unsafe_allow_html=True)

# --- 3. EMAIL FUNCTIE ---
def stuur_mail(ontvanger, onderwerp, inhoud, bestanden=None):
    msg = MIMEMultipart()
    msg['From'] = f"Dienst Grondzaken Wanica Centrum <{EMAIL_USER}>"
    msg['To'] = ontvanger
    msg['Subject'] = onderwerp
    
    # Zorgt ervoor dat regeleinden (\n) netjes worden omgezet naar HTML-balken (<br>)
    html_inhoud = f"<html><body style='font-family: Arial; font-size: 14px; color: black;'>{inhoud.replace('\\n', '<br>')}</body></html>"
    msg.attach(MIMEText(html_inhoud, 'html'))
    
    if bestanden:
        for f in bestanden:
            f.seek(0)
            part = MIMEApplication(f.read(), Name=f.name)
            part['Content-Disposition'] = f'attachment; filename="{f.name}"'
            msg.attach(part)
    try:
        server = smtplib.SMTP('smtp.gmail.com', 587)
        server.starttls()
        server.login(EMAIL_USER, EMAIL_PASS)
        server.send_message(msg)
        server.quit()
        return True
    except: 
        return False

# --- 4. STATE ---
if 'logged_in' not in st.session_state:
    st.session_state.update({'logged_in': False, 'role': None, 'user': None})
if 'selected_time' not in st.session_state:
    st.session_state.selected_time = None

# --- 5. MENU & LOGIN ---
menu_options = ["📝 Nieuwe Registratie"]
if st.session_state.logged_in:
    menu_options += ["📋 Dossierbeheer", "📊 Rapportages", "📅 Agenda", "⚙️ Systeembeheer"]

menu = st.sidebar.radio("Hoofdmenu", menu_options)

if not st.session_state.logged_in:
    with st.sidebar.expander("🔐 Medewerker Login"):
        res_m = supabase.table("medewerkers").select("*").execute()
        u_list = [u['gebruikersnaam'] for u in res_m.data] if res_m.data else []
        u_sel = st.selectbox("Gebruiker", ["---"] + u_list)
        p_inp = st.text_input("Wachtwoord", type="password")
        if st.button("Inloggen"):
            user = next((u for u in res_m.data if u['gebruikersnaam'] == u_sel), None)
            if user and user['wachtwoord'] == p_inp:
                st.session_state.update({'logged_in': True, 'role': str(user['rol']).lower(), 'user': u_sel})
                st.rerun()
else:
    st.sidebar.write(f"Ingelogd: **{st.session_state.user}** ({st.session_state.role})")
    if st.sidebar.button("🚪 Afmelden"):
        st.session_state.update({'logged_in': False, 'role': None, 'user': None})
        st.rerun()

# --- 6. PAGINA LOGICA ---

# A. NIEUWE REGISTRATIE
if menu == "📝 Nieuwe Registratie":
    col_l, col_r = st.columns([1, 4])
    with col_l:
        st.image("https://raw.githubusercontent.com/bhikhienadeem-art/dgw-app/main/orgineel%20logo%20Centrum.png", width=120)
    with col_r:
       st.title("Meldpunt Grondproblemen Wanica Centrum")
    
    st.divider()
    c1, c2 = st.columns(2)
    with c1:
        vnaam = st.text_input("Voornaam *")
        anaam = st.text_input("Achternaam *")
        adres = st.text_input("Woonadres *")
        email = st.text_input("E-mailadres *")
    with c2:
        id_nr = st.text_input("ID-nummer *")
        tel = st.text_input("Telefoonnummer *")
        lad = st.text_input("LAD-nummer")
    
    bericht = st.text_area("Omschrijving klacht/verzoek *")
    docs = st.file_uploader("Documenten uploaden", accept_multiple_files=True)
    
    st.divider()
    st.subheader("📅 Afspraak inplannen (Maandag & Woensdag)")
    datum = st.date_input("Kies datum", min_value=datetime.date.today())
    
    if datum.weekday() in [0, 2]:
        tijden = [f"{h:02d}:{m:02d}" for h in range(8, 13) for m in (0, 15, 30, 45) if not (h == 12 and m > 0)]
        cols = st.columns(6)
        for idx, t in enumerate(tijden):
            with cols[idx % 6]:
                if st.button(t, key=f"t_{t}", type="primary" if st.session_state.selected_time == t else "secondary", use_container_width=True):
                    st.session_state.selected_time = t
                    st.rerun()
    else:
        st.warning("Bezoekafspraken zijn enkel op maandag en woensdag.")

    if st.button("✅ Indienen", type="primary", use_container_width=True):
        if all([vnaam, anaam, adres, email, id_nr, bericht]) and st.session_state.selected_time:
            # 1. Opslaan in Supabase Database
            data = {
                "voornaam": vnaam, 
                "achternaam": anaam, 
                "woonadres": adres, 
                "email": email, 
                "id_nummer": id_nr, 
                "telefoon": tel, 
                "lad_nummer": lad, 
                "afspraak_datum": str(datum), 
                "afspraak_tijd": st.session_state.selected_time, 
                "status": "In behandeling", 
                "bericht": bericht
            }
            supabase.table("aanvragen").insert(data).execute()
            
            # 2. E-mailtekst opbouwen voor de medewerker
            mail_onderwerp = f"🚨 Nieuwe Registratie: LAD {lad if lad else 'N.v.t.'} - {vnaam} {anaam}"
            mail_inhoud = f"""
            <h3>Nieuwe melding binnengekomen via het portaal:</h3>
            <br>
            <b>CLIËNT GEGEVENS:</b><br>
            - <b>Naam:</b> {vnaam} {anaam}<br>
            - <b>ID-nummer:</b> {id_nr}<br>
            - <b>Adres:</b> {adres}<br>
            - <b>Telefoonnummer:</b> {tel}<br>
            - <b>E-mailadres:</b> {email}<br>
            - <b>LAD-nummer:</b> {lad if lad else 'Niet opgegeven'}<br>
            <br>
            <b>OMSCHRIJVING KLACHT / VERZOEK:</b><br>
            {bericht}<br>
            <br>
            <b>GEPLANDE AFSPRAAK:</b><br>
            - <b>Datum:</b> {datum.strftime('%d-%m-%Y')}<br>
            - <b>Tijdstip:</b> {st.session_state.selected_time} uur<br>
            <br>
            <i>De bijbehorende documenten zijn als bijlage toegevoegd aan deze e-mail.</i>
            """
            
            # 3. E-mail verzenden met de uploadlijst (docs) als bijlage
            with st.spinner("Notificatie verzenden naar medewerker..."):
                mail_verzonden = stuur_mail(EMAIL_USER, mail_onderwerp, mail_inhoud, bestanden=docs)
            
            if mail_verzonden:
                st.success("Registratie succesvol ingediend! De medewerker heeft de documenten en gegevens per e-mail ontvangen.")
            else:
                st.warning("Registratie succesvol opgeslagen in de database, maar er was een probleem met het verzenden van de e-mail.")
                
            st.session_state.selected_time = None
            st.rerun()
        else: 
            st.error("Vul alle verplichte velden in en kies een tijdstip.")

    st.write("")
    st.divider()
    st.subheader("📞 Direct Contact")
    st.markdown("""
        <div style="background-color: #f1f8e9; padding: 15px; border-radius: 10px; border-left: 5px solid #2e7d32;">
            <p style="margin: 0; color: black;"><b>📧 E-mail:</b> wanicacentrum.gz@gmail.com</p>
            <p style="margin: 0; color: black;"><b>📞 Telefoon:</b> +597-366660 / +597-366929</p>
        </div>
    """, unsafe_allow_html=True)

# B. DOSSIERBEHEER
elif menu == "📋 Dossierbeheer" and st.session_state.logged_in:
    st.header("📋 Dossierbeheer")
    res = supabase.table("aanvragen").select("*").order('id', desc=True).execute()
    if res.data:
        df = pd.DataFrame(res.data)
        
        # Toon een overzichtelijke tabel van de belangrijkste kolommen
        st.dataframe(df[['id', 'voornaam', 'achternaam', 'id_nummer', 'telefoon', 'lad_nummer', 'status', 'afspraak_datum']], hide_index=True, use_container_width=True)
        
        sel_id = st.selectbox("Selecteer Dossier", df['id'].tolist())
        d = next(item for item in res.data if item['id'] == sel_id)
        
        # --- NIEUW: UITGEBREID OVERZICHT VAN ALLE CLIËNTGEGEVENS ---
        st.write("")
        st.subheader(f"🔍 Volledige Details - Dossier #{sel_id}")
        
        # We maken een nette layout met 3 kolommen voor de cliënt- en afspraakkaarten
        det_c1, det_c2, det_c3 = st.columns(3)
        
        with det_c1:
            st.markdown(f"""
            <div style="background-color: #f1f8e9; padding: 15px; border-radius: 5px; border-left: 4px solid #2e7d32;">
                <h4 style="margin-top:0; color: #1b5e20;">👤 Cliëntgegevens</h4>
                <b>Voornaam:</b> {d.get('voornaam', '')}<br>
                <b>Achternaam:</b> {d.get('achternaam', '')}<br>
                <b>ID-nummer:</b> {d.get('id_nummer', '')}<br>
                <b>Woonadres:</b> {d.get('woonadres', '')}
            </div>
            """, unsafe_allow_html=True)
            
        with det_c2:
            st.markdown(f"""
            <div style="background-color: #f1f8e9; padding: 15px; border-radius: 5px; border-left: 4px solid #2e7d32;">
                <h4 style="margin-top:0; color: #1b5e20;">📞 Contact & Referentie</h4>
                <b>Telefoonnummer:</b> {d.get('telefoon', '')}<br>
                <b>E-mailadres:</b> {d.get('email', '')}<br>
                <b>LAD-nummer:</b> {d.get('lad_nummer', 'N.v.t.')}
            </div>
            """, unsafe_allow_html=True)
            
        with det_c3:
            st.markdown(f"""
            <div style="background-color: #e8f5e9; padding: 15px; border-radius: 5px; border-left: 4px solid #1b5e20;">
                <h4 style="margin-top:0; color: #1b5e20;">📅 Afspraakstatus</h4>
                <b>Datum:</b> {d.get('afspraak_datum', '')}<br>
                <b>Tijdstip:</b> {d.get('afspraak_tijd', '')} uur<br>
                <b>Huidige Status:</b> <u>{d.get('status', '')}</u>
            </div>
            """, unsafe_allow_html=True)
            
        # Volledige omschrijving van de klacht over de hele breedte
        st.write("")
        st.markdown(f"""
        <div style="background-color: #fafafa; padding: 15px; border-radius: 5px; border: 1px solid #2e7d32;">
            <h4 style="margin-top:0; color: #1b5e20;">📝 Omschrijving klacht/verzoek:</h4>
            <p style="color: black; white-space: pre-wrap;">{d.get('bericht', '')}</p>
        </div>
        """, unsafe_allow_html=True)
        # -----------------------------------------------------------
        
        st.divider()
        st.subheader("⚙️ Dossier Bewerken & Acties")
        ce1, ce2 = st.columns(2)
        with ce1:
            n_status = st.selectbox("Status aanpassen", ["In behandeling", "Wacht op documenten", "Bevestigd", "Afgehandeld"], index=["In behandeling", "Wacht op documenten", "Bevestigd", "Afgehandeld"].index(d['status']) if d['status'] in ["In behandeling", "Wacht op documenten", "Bevestigd", "Afgehandeld"] else 0)
            n_datum = st.date_input("Nieuwe Datum", value=datetime.datetime.strptime(d['afspraak_datum'], '%Y-%m-%d').date())
            n_tijd = st.text_input("Nieuwe Tijd", value=d['afspraak_tijd'])
        with ce2:
            toelichting = st.text_area("Interne Notitie (Medewerker)", value=d.get('medewerker_toelichting', ""))
            mail_tekst = st.text_area("Bericht naar Cliënt (Laat leeg indien geen mail gewenst)")

        b1, b2 = st.columns(2)
        with b1:
            if st.button("💾 Bijwerken & Mailen", use_container_width=True):
                supabase.table("aanvragen").update({"status": n_status, "afspraak_datum": str(n_datum), "afspraak_tijd": n_tijd, "medewerker_toelichting": toelichting}).eq("id", sel_id).execute()
                if mail_tekst:
                    mail_body = f"Update Dossier: {n_status}.\\nAfspraak: {n_datum} om {n_tijd}.\\n\\n{mail_tekst}"
                    stuur_mail(d['email'], "Update Dossier", mail_body)
                st.success("Dossier succesvol bijgewerkt!")
                st.rerun()
        with b2:
            if st.button(f"🗑️ Verwijder Dossier #{sel_id}", type="secondary", use_container_width=True):
                supabase.table("aanvragen").delete().eq("id", sel_id).execute()
                st.rerun()

# C. RAPPORTAGES
elif menu == "📊 Rapportages" and st.session_state.logged_in:
    st.header("📊 Management Rapportages")
    res = supabase.table("aanvragen").select("*").execute()
    if res.data:
        df = pd.DataFrame(res.data)
        c1, c2 = st.columns(2)
        with c1:
            st.subheader("🎯 Status Verdeling")
            fig_pie = px.pie(df, names='status', color_discrete_sequence=['#2e7d32', '#4caf50', '#81c784', '#a5d6a7'])
            st.plotly_chart(fig_pie, use_container_width=True)
        with c2:
            st.subheader("📈 Aanvragen Trend")
            df['created_at'] = pd.to_datetime(df['created_at']).dt.date
            trend = df.groupby('created_at').size().reset_index(name='aantal')
            fig_line = px.line(trend, x='created_at', y='aantal', markers=True)
            fig_line.update_traces(line_color='#2e7d32')
            st.plotly_chart(fig_line, use_container_width=True)
        st.divider()
        st.dataframe(df, use_container_width=True, hide_index=True)

# D. AGENDA
elif menu == "📅 Agenda" and st.session_state.logged_in:
    st.header("📅 Afspraken Agenda")
    res = supabase.table("aanvragen").select("voornaam, achternaam, afspraak_datum, afspraak_tijd, status, telefoon").execute()
    if res.data:
        df = pd.DataFrame(res.data)
        vandaag = datetime.date.today()
        tab1, tab2, tab3 = st.tabs(["📅 Vandaag", "⏭️ Komende Week", "📁 Alles"])
        with tab1:
            df_v = df[pd.to_datetime(df['afspraak_datum']).dt.date == vandaag]
            st.dataframe(df_v, use_container_width=True)
        with tab2:
            df_w = df[pd.to_datetime(df['afspraak_datum']).dt.date > vandaag]
            st.dataframe(df_w, use_container_width=True)
        with tab3:
            st.dataframe(df.sort_values('afspraak_datum'), use_container_width=True)

# E. SYSTEEMBEHEER (GEBRUIKERSBEHEER)
elif menu == "⚙️ Systeembeheer" and st.session_state.logged_in:
    st.header("⚙️ Systeembeheer")
    if st.session_state.role == 'admin':
        t1, t2 = st.tabs(["👥 Gebruikers Overzicht", "➕ Gebruiker Toevoegen"])
        with t1:
            res_u = supabase.table("medewerkers").select("*").execute()
            if res_u.data:
                df_u = pd.DataFrame(res_u.data)
                st.dataframe(df_u[['gebruikersnaam', 'rol']], use_container_width=True)
                u_del = st.selectbox("Verwijder medewerker", df_u['gebruikersnaam'].tolist())
                if st.button("🗑️ Definitief Verwijderen", type="secondary"):
                    if u_del != st.session_state.user:
                        supabase.table("medewerkers").delete().eq("gebruikersnaam", u_del).execute()
                        st.success("Gebruiker verwijderd.")
                        st.rerun()
                    else: st.error("Je kunt jezelf niet verwijderen.")
        with t2:
            new_u = st.text_input("Nieuwe Gebruikersnaam")
            new_p = st.text_input("Wachtwoord", type="password")
            new_r = st.selectbox("Rol", ["user", "admin"])
            if st.button("✅ Gebruiker Opslaan"):
                supabase.table("medewerkers").insert({"gebruikersnaam": new_u, "wachtwoord": new_p, "rol": new_r}).execute()
                st.success("Gebruiker aangemaakt!")
                st.rerun()
    else:
        st.warning("⚠️ Alleen beheerders hebben toegang tot dit menu.")

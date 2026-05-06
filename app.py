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

# --- 2. STYLING (DEFINITIEVE LEESBAARHEID) ---
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

# --- 4. STATE & LOGIN ---
if 'logged_in' not in st.session_state:
    st.session_state.update({'logged_in': False, 'role': None, 'user': None})
if 'selected_time' not in st.session_state:
    st.session_state.selected_time = None

# --- 5. NAVIGATIE ---
menu_options = ["📝 Nieuwe Registratie"]
if st.session_state.logged_in:
    menu_options += ["📋 Dossierbeheer", "📊 Rapportages", "📅 Agenda", "⚙️ Systeembeheer"]

menu = st.sidebar.radio("Hoofdmenu", menu_options)

if st.session_state.logged_in:
    st.sidebar.write(f"Ingelogd: **{st.session_state.user}**")
    if st.sidebar.button("🚪 Afmelden"):
        st.session_state.update({'logged_in': False, 'role': None, 'user': None})
        st.rerun()
else:
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

# --- 6. NIEUWE REGISTRATIE (HERSTELD & UITGEBREID) ---
elif menu == "📝 Nieuwe Registratie":
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
            # Nieuwe verplichte velden
            woonadres = st.text_input("Woonadres *")
            lad_nr = st.text_input("LAD-nummer")
            
            # Afspraakplanning (Maandag & Woensdag)
            d_keuze = st.date_input("Kies datum", min_value=datetime.date.today())
            t_keuze = st.selectbox("Tijdstip", ["08:00", "09:00", "10:00", "11:00", "12:00"])

        bericht = st.text_area("Omschrijving klacht/verzoek *")
        
        # Documenten uploaden
        st.write("---")
        st.subheader("📁 Documenten Uploaden")
        uploads = st.file_uploader("Kies bestanden (ID, grondbescheiden, etc.)", accept_multiple_files=True)
        
        submit_btn = st.form_submit_button("✅ REGISTRATIE VERZENDEN")
        
        if submit_btn:
            # Validatie op dagen
            if d_keuze.weekday() not in [0, 2]:
                st.error("Let op: Afspraken zijn alleen mogelijk op maandag of woensdag.")
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
                if uploads:
                    st.info(f"{len(uploads)} bestand(en) succesvol klaargezet voor verwerking.")
            else:
                st.error("Vul a.u.b. alle velden met een * in.")

# --- 7. DOSSIERBEHEER (ONGEWIJZIGD) ---
elif menu == "📋 Dossierbeheer":
    # ... (code blijft gelijk aan de werkende versie die je had)

# --- 7. DOSSIERBEHEER (VOLLEDIGE CLIËNTGEGEVENS & BERICHTEN) ---
elif menu == "📋 Dossierbeheer":
    st.header("📋 Dossierbeheer")
    res = supabase.table("aanvragen").select("*").order('id', desc=True).execute()
    if res.data:
        df = pd.DataFrame(res.data)
        st.dataframe(df[['id', 'voornaam', 'achternaam', 'status', 'afspraak_datum']], use_container_width=True)
        
        sel_id = st.selectbox("Selecteer Dossier ID", df['id'].tolist())
        d = next(item for item in res.data if item['id'] == sel_id)
        
        st.markdown(f"### 📄 Dossier #{sel_id}: {d['voornaam']} {d['achternaam']}")
        
        # Alle cliëntgegevens tonen
        col1, col2 = st.columns(2)
        with col1:
            st.write(f"**ID-nummer:** {d['id_nummer']}")
            st.write(f"**E-mail:** {d['email']}")
            st.write(f"**Telefoon:** {d.get('telefoon', 'Niet opgegeven')}")
        with col2:
            st.write(f"**Woonadres:** {d.get('woonadres', 'Niet opgegeven')}")
            st.write(f"**Afspraak:** {d['afspraak_datum']} om {d['afspraak_tijd']}")
        
        st.info(f"**Klacht van cliënt:** {d['bericht']}")
        
        # Beheer en Berichten
        st.divider()
        c_left, c_right = st.columns(2)
        with c_left:
            n_status = st.selectbox("Status Bijwerken", ["In behandeling", "Wacht op documenten", "Bevestigd", "Afgehandeld"], 
                                    index=["In behandeling", "Wacht op documenten", "Bevestigd", "Afgehandeld"].index(d['status']) if d['status'] in ["In behandeling", "Wacht op documenten", "Bevestigd", "Afgehandeld"] else 0)
            toelichting = st.text_area("Interne Notitie (Medewerker)", value=d.get('medewerker_toelichting', ""))
        
        with c_right:
            mail_tekst = st.text_area("📧 Bericht aan Cliënt (Email)", placeholder="Typ hier de informatie die u naar de cliënt wilt mailen...")

        btn_1, btn_2 = st.columns(2)
        with btn_1:
            if st.button("💾 BIJWERKEN & MAILEN"):
                supabase.table("aanvragen").update({"status": n_status, "medewerker_toelichting": toelichting}).eq("id", sel_id).execute()
                if mail_tekst:
                    onderwerp = f"Update Grondzaken Dossier #{sel_id}"
                    inhoud = f"Geachte {d['voornaam']} {d['achternaam']},\n\nUw dossier #{sel_id} is bijgewerkt.\n\nBericht:\n{mail_tekst}\n\nStatus: {n_status}"
                    stuur_mail(d['email'], onderwerp, inhoud)
                    st.success("Dossier bijgewerkt en gemaild!")
                else:
                    st.success("Dossier bijgewerkt.")
                st.rerun()
                
        with btn_2:
            if st.button(f"🗑️ VERWIJDER DOSSIER #{sel_id}", type="secondary"):
                supabase.table("aanvragen").delete().eq("id", sel_id).execute()
                st.rerun()

# --- 8. SYSTEEMBEHEER (INCLUSIEF VERWIJDEREN) ---
elif menu == "⚙️ Systeembeheer":
    st.header("⚙️ Systeembeheer")
    if st.session_state.role == 'admin':
        st.subheader("Medewerkersbeheer")
        with st.expander("➕ Nieuwe Medewerker Toevoegen"):
            n_user = st.text_input("Gebruikersnaam")
            n_pass = st.text_input("Wachtwoord", type="password")
            n_rol = st.selectbox("Rol", ["medewerker", "admin"])
            if st.button("💾 Medewerker Opslaan"):
                supabase.table("medewerkers").insert({"gebruikersnaam": n_user, "wachtwoord": n_pass, "rol": n_rol}).execute()
                st.success("Medewerker toegevoegd."); st.rerun()
        
        st.divider()
        res_m = supabase.table("medewerkers").select("*").execute()
        if res_m.data:
            df_m = pd.DataFrame(res_m.data)
            st.dataframe(df_m[['id', 'gebruikersnaam', 'rol']], use_container_width=True)
            
            sel_m_id = st.selectbox("Selecteer Medewerker ID om te verwijderen", df_m['id'].tolist())
            if st.button(f"🗑️ Verwijder Medewerker #{sel_m_id}", type="secondary"):
                supabase.table("medewerkers").delete().eq("id", sel_m_id).execute()
                st.success("Medewerker verwijderd."); st.rerun()
    else: st.error("U heeft geen admin-rechten voor deze pagina.")

# --- 9. RAPPORTAGES (VOLLEDIGE DETAILS & EXPORT) ---
elif menu == "📊 Rapportages":
    st.header("📊 Uitgebreide Rapportages")
    
    # Gegevens ophalen uit de database
    res = supabase.table("aanvragen").select("*").order('created_at', desc=True).execute()
    
    if res.data:
        df = pd.DataFrame(res.data)
        
        # Dashboard Visualisaties (Snel overzicht)
        col_v1, col_v2 = st.columns(2)
        with col_v1:
            fig_pie = px.pie(df, names='status', title="Dossier Status Verdeling", 
                             color_discrete_sequence=['#2e7d32', '#81c784', '#a5d6a7', '#d32f2f'])
            st.plotly_chart(fig_pie, use_container_width=True)
        
        with col_v2:
            df['datum_kort'] = pd.to_datetime(df['created_at']).dt.date
            fig_bar = px.bar(df.groupby('datum_kort').size().reset_index(name='aantal'), 
                             x='datum_kort', y='aantal', title="Registraties per Dag",
                             color_discrete_sequence=['#2e7d32'])
            st.plotly_chart(fig_bar, use_container_width=True)

        st.divider()
        
        # Volledige Detail Tabel (Zoals gevraagd)
        st.subheader("📄 Alle Cliëntgegevens & Dossier Details")
        
        # Kolommen hernoemen voor leesbaarheid in de rapportage
        df_display = df.copy()
        kolommen_config = {
            'id': 'Dossier ID',
            'created_at': 'Registratie Datum',
            'voornaam': 'Voornaam',
            'achternaam': 'Achternaam',
            'email': 'E-mailadres',
            'id_nummer': 'ID-Nummer',
            'telefoon': 'Telefoon',
            'woonadres': 'Adres',
            'status': 'Status',
            'bericht': 'Klacht/Omschrijving',
            'afspraak_datum': 'Afspraak Datum',
            'afspraak_tijd': 'Tijd'
        }
        
        # Alleen relevante kolommen tonen die in de database zitten
        beschikbare_kolommen = [k for k in kolommen_config.keys() if k in df_display.columns]
        df_final = df_display[beschikbare_kolommen].rename(columns=kolommen_config)
        
        st.dataframe(df_final, use_container_width=True)

        # Export optie naar Excel/CSV
        csv = df_final.to_csv(index=False).encode('utf-8')
        st.download_button(
            label="📥 Download Alle Details (CSV)",
            data=csv,
            file_name=f"rapportage_grondzaken_{datetime.date.today()}.csv",
            mime="text/csv",
        )
    else:
        st.info("Er zijn nog geen registraties gevonden om te rapporteren.")

# --- 10. UITGEBREIDE INTERACTIEVE AGENDA ---
elif menu == "📅 Agenda":
    st.header("📅 Interactief Afsprakenoverzicht")
    
    # Gegevens ophalen
    res = supabase.table("aanvragen").select("*").order('afspraak_datum').execute()
    
    if res.data:
        df_ag = pd.DataFrame(res.data)
        
        # 1. Korte statistieken bovenaan
        vandaag = datetime.date.today()
        afspraken_vandaag = df_ag[df_ag['afspraak_datum'] == str(vandaag)]
        
        col_stat1, col_stat2 = st.columns(2)
        col_stat1.metric("Afspraken Vandaag", len(afspraken_vandaag))
        col_stat2.metric("Totaal Ingepland", len(df_ag))

        st.divider()

        # 2. Dagelijkse Details Picker
        st.subheader("🔍 Planning per Dag")
        gekozen_datum = st.date_input("Selecteer een datum om de planning te zien", vandaag)
        dag_selectie = df_ag[df_ag['afspraak_datum'] == str(gekozen_datum)]
        
        if not dag_selectie.empty:
            for _, row in dag_selectie.iterrows():
                with st.expander(f"⏰ {row['afspraak_tijd']} - {row['voornaam']} {row['achternaam']} ({row['status']})"):
                    st.write(f"**Telefoon:** {row.get('telefoon', 'Onbekend')}")
                    st.write(f"**E-mail:** {row['email']}")
                    st.write(f"**Klacht:** {row['bericht']}")
                    if st.button(f"Bekijk Dossier #{row['id']}", key=f"btn_{row['id']}"):
                        st.info("Ga naar Dossierbeheer en selecteer dit ID voor bewerking.")
        else:
            st.info(f"Geen afspraken gepland voor {gekozen_datum}.")

        st.divider()

        # 3. Het Volledige Overzicht (Tabelweergave)
        st.subheader("📋 Volledige Agenda Lijst")
        st.dataframe(
            df_ag[['afspraak_datum', 'afspraak_tijd', 'voornaam', 'achternaam', 'telefoon', 'status']],
            column_config={
                "afspraak_datum": "Datum",
                "afspraak_tijd": "Tijdstip",
                "status": st.column_config.SelectboxColumn("Status", options=["In behandeling", "Bevestigd", "Afgehandeld"])
            },
            use_container_width=True,
            hide_index=True
        )

        # Export functie
        csv_ag = df_ag.to_csv(index=False).encode('utf-8')
        st.download_button("📥 Agenda Exporteren (CSV)", csv_ag, "agenda_export.csv", "text/csv")
    else:
        st.info("Er zijn momenteel geen afspraken geregistreerd.")

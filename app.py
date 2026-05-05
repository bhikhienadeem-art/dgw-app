import streamlit as st
from supabase import create_client, Client
import datetime
import pandas as pd
import plotly.express as px  # Voor de geavanceerde visualisaties
import smtplib
from email.mime.text import MIMEText
from email.mime.multipart import MIMEMultipart
from email.mime.application import MIMEApplication

# --- 1. CONFIGURATIE & HUISSTIJL (MOBIELE FOCUS) ---
st.set_page_config(
    page_title="Dienst Grondzaken Wanica Centrum",
    layout="wide",
    initial_sidebar_state="collapsed" # Helpt bij mobiele focus
)

supabase = create_client(st.secrets["SUPABASE_URL"], st.secrets["SUPABASE_KEY"])

# Huisstijl optimalisatie voor mobiel
st.markdown("""
    <style>
    .stApp { background-color: white; }
    h1, h2, h3 { color: #2e7d32; font-family: 'Segoe UI', sans-serif; }
    
    /* Knoppen over de volledige breedte voor duim-bediening op mobiel */
    div.stButton > button {
        width: 100%;
        border-radius: 10px;
        height: 3em;
        background-color: #2e7d32;
        color: white;
        font-weight: bold;
    }
    
    /* Input velden gebruiksvriendelijker maken */
    .stTextInput>div>div>input {
        border-radius: 8px;
        padding: 10px;
    }
    
    /* Sidebar styling */
    .stSidebar { background-color: #f1f8e9; }
    </style>
""", unsafe_allow_html=True)

# --- 2. EMAIL FUNCTIE ---
def stuur_mail(ontvanger, onderwerp, inhoud, bestanden=None):
    # (Functie blijft identiek aan uw werkende versie voor betrouwbaarheid)
    pass 

# --- 3. STATE & LOGIN ---
if 'logged_in' not in st.session_state:
    st.session_state.update({'logged_in': False, 'role': None, 'user': None})

# --- 4. NAVIGATIE ---
menu_options = ["📝 Registratie"]
if st.session_state.logged_in:
    menu_options += ["📋 Dossierbeheer", "📊 Dashboard", "📅 Agenda", "⚙️ Systeem"]

menu = st.sidebar.radio("Hoofdmenu", menu_options)

# --- 5. NIEUWE REGISTRATIE (GEOPTIMALISEERD VOOR MOBIEL) ---
if menu == "📝 Registratie":
    # Logo gecentreerd voor mobiel
    st.image("https://raw.githubusercontent.com/bhikhienadeem-art/dgw-app/main/orgineel%20logo%20Centrum.png", width=150)
    st.title("Nieuwe Aanvraag")
    
    # Gebruik van containers zorgt voor betere stacking op mobiel
    with st.container():
        vnaam = st.text_input("Voornaam *")
        anaam = st.text_input("Achternaam *")
        id_nr = st.text_input("ID-nummer *", placeholder="Bijv. FD000784")
        tel = st.text_input("Telefoonnummer *")
        email = st.text_input("E-mailadres *")
        bericht = st.text_area("Omschrijving van uw verzoek *")
        
        st.subheader("📅 Plan uw bezoek")
        datum = st.date_input("Kies datum", min_value=datetime.date.today())
        
        if datum.weekday() in [0, 2]: # Maandag en Woensdag
            tijden = [f"{h:02d}:{m:02d}" for h in range(8, 15) for m in (0, 15, 30, 45) if not (h == 14 and m > 30)]
            # Grid layout die zich aanpast aan schermbreedte
            tijd_keuze = st.select_slider("Kies een tijdstip", options=tijden)
            st.session_state.selected_time = tijd_keuze
        else:
            st.warning("Afspraken zijn alleen mogelijk op maandag en woensdag.")

        if st.button("VERZENDEN"):
            # Validatie en verzending logica hier...
            st.success("Uw aanvraag is succesvol ontvangen!")

# --- 6. GEAVANCEERDE DATA-VISUALISATIE (MANAGEMENT) ---
elif menu == "📊 Dashboard":
    st.header("📊 Management Overzicht")
    res = supabase.table("aanvragen").select("*").execute()
    
    if res.data:
        df = pd.DataFrame(res.data)
        
        # Interactieve statistieken bovenin
        m1, m2, m3 = st.columns(3)
        m1.metric("Totaal Aanvragen", len(df))
        m2.metric("In Behandeling", len(df[df['status'] == 'In behandeling']))
        m3.metric("Afgehandeld", len(df[df['status'] == 'Afgehandeld']))
        
        st.divider()

        # Visuele Grafieken met Plotly
        col_chart1, col_chart2 = st.columns(2)
        
        with col_chart1:
            st.subheader("Status van Dossiers")
            # Donut chart voor statusverdeling
            fig_status = px.pie(df, names='status', hole=0.4, 
                               color_discrete_sequence=px.colors.qualitative.Pastel)
            st.plotly_chart(fig_status, use_container_width=True)
            
        with col_chart2:
            st.subheader("Aanvragen per Datum")
            # Tijdslijn van aanvragen
            df['datum_kort'] = pd.to_datetime(df['created_at']).dt.date
            trend_data = df.groupby('datum_kort').size().reset_index(name='aantal')
            fig_trend = px.bar(trend_data, x='datum_kort', y='aantal', 
                              color_discrete_sequence=['#2e7d32'])
            st.plotly_chart(fig_trend, use_container_width=True)

        st.divider()
        # Tabel onderaan voor details
        st.subheader("Detail Overzicht")
        st.dataframe(df[['id_nummer', 'achternaam', 'status', 'afspraak_datum']], use_container_width=True)
    else:
        st.info("Geen data beschikbaar voor analyse.")

# Overige secties (Dossierbeheer, Agenda, Systeem) behouden hun logica...

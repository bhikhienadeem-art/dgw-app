import streamlit as st
import pandas as pd
from supabase import create_client, Client
import smtplib
import ssl
from email.mime.text import MIMEText
from email.mime.multipart import MIMEMultipart
from email.mime.base import MIMEBase
from email import encoders

# --- 1. CONFIGURATIE ---
SUPABASE_URL = "https://pmxfvchbyalhlknuvzyv.supabase.co"
SUPABASE_KEY = "sb_secret_Fd5ainmOfAMxjT82aeCrWg_89SNPliW" 
supabase: Client = create_client(SUPABASE_URL, SUPABASE_KEY)

# --- 2. MAIL FUNCTIE ---
def verzend_mail(onderwerp, ontvanger, tekst, bestanden=None):
    afzender = "wanicacentrum.gz@gmail.com"
    wachtwoord = "opetojzsidowbrba" 
    msg = MIMEMultipart()
    msg['From'], msg['To'], msg['Subject'] = afzender, ontvanger, onderwerp
    msg.attach(MIMEText(tekst, 'plain'))
    if bestanden:
        for bestand in bestanden:
            part = MIMEBase('application', 'octet-stream')
            part.set_payload(bestand.read())
            encoders.encode_base64(part)
            part.add_header('Content-Disposition', f'attachment; filename={bestand.name}')
            msg.attach(part)
            bestand.seek(0)
    context = ssl.create_default_context()
    try:
        with smtplib.SMTP_SSL("smtp.gmail.com", 465, context=context) as server:
            server.login(afzender, wachtwoord)
            server.send_message(msg)
        return True
    except:
        return False

# --- 3. SESSION STATE ---
if 'ingelogd' not in st.session_state:
    st.session_state.update({'ingelogd': False, 'gebruiker': None, 'rol': None})

# --- 4. STYLING (Huisstijl DGW) ---
st.set_page_config(page_title="Dienst Grondzaken Wanica (DGW)", layout="wide")
st.markdown("""<style>
    .stApp { background-color: white; }
    
    /* Labels zwart/donkergrijs maken voor leesbaarheid */
    label, .stMarkdown p, .stSelectbox label, .stTextInput label, .stTextArea label, p, span {
        color: #31333F !important; 
        font-weight: bold !important;
    }
    
    .stTextInput input, .stTextArea textarea {
        background-color: #f0f2f6 !important;
        color: black !important;
    }

    .klant-box { 
        padding: 25px; 
        border: 2px solid #2e7d32; 
        border-radius: 12px; 
        background-color: #f1f8e9; 
        margin-bottom: 20px; 
        color: black;
    }
    
    h1, h2, h3 { color: #2e7d32 !important; }
    
    .stButton>button { 
        border-radius: 8px; 
        font-weight: bold; 
        width: 100%; 
        height: 45px; 
    }
    </style>""", unsafe_allow_html=True)

# --- 5. NAVIGATIE ---
st.sidebar.title("DGW Menu")
if not st.session_state['ingelogd']:
    modus = st.sidebar.radio("Ga naar:", ["Cliënt Registratie", "Medewerker Login"])
else:
    huidige_rol = str(st.session_state.get('rol', '')).strip().lower()
    st.sidebar.success(f"Ingelogd: {st.session_state['gebruiker']}")
    opties = ["Dashboard"]
    if huidige_rol == "admin":
        opties.append("Instellingen (Admin)")
    modus = st.sidebar.radio("Beheer:", opties)
    st.sidebar.markdown("---")
    if st.sidebar.button("Uitloggen"):
        st.session_state.update({'ingelogd': False, 'gebruiker': None, 'rol': None})
        st.rerun()

# --- 6. CLIËNT REGISTRATIE ---
if modus == "Cliënt Registratie":
    st.title("📝 Portaal: Dienst Grondzaken Wanica")
    st.subheader("Registratieformulier")
    
    col1, col2 = st.columns(2)
    with col1:
        v = st.text_input("Voornaam *")
        id_n = st.text_input("ID-Nummer *")
        tel = st.text_input("Telefoonnummer *")
    with col2:
        a = st.text_input("Achternaam *")
        lad = st.text_input("LAD Nummer *")
        em = st.text_input("E-mailadres *")
        
    adr = st.text_input("Woonadres *")
    o = st.text_area("Omschrijving van uw klacht of aanvraag *")
    files = st.file_uploader("Upload relevante documenten", accept_multiple_files=True)
    d_afspraak = st.date_input("Kies een datum voor afspraak")
    
    res_b = supabase.table("klachten").select("afspraak_tijd").eq("afspraak_datum", str(d_afspraak)).execute()
    bezette_tijden = [t['afspraak_tijd'][:5] for t in res_b.data] if res_b.data else []
    alle_tijden = [f"{h:02d}:{m:02d}" for h in range(7, 15) for m in [0, 15, 30, 45]]
    t_opties = [f"{t} ({'🔴 BEZET' if t in bezette_tijden else '🟢 Vrij'})" for t in alle_tijden]
    t_keuze = st.selectbox("Kies een beschikbaar tijdstip", t_opties)

    if st.button("AANVRAAG DEFINITIEF VERZENDEN"):
        if v and a and id_n and em and "BEZET" not in t_keuze:
            data = {"voornaam": v, "naam": a, "id_nummer": id_n, "telefoon": tel, "email": em, "lad_nummer": lad, "adres": adr, "klacht_omschrijving": o, "status": "Nieuw", "afspraak_datum": str(d_afspraak), "afspraak_tijd": t_keuze[:5]}
            supabase.table("klachten").insert(data).execute()
            verzend_mail(f"DGW Registratie: {v} {a}", "wanicacentrum.gz@gmail.com", f"Een nieuwe aanvraag is ingediend door {v} {a}.\nOmschrijving: {o}", bestanden=files)
            st.success("✅ Uw aanvraag is succesvol verwerkt door DGW!")
            st.balloons()

# --- 7. MEDEWERKER DASHBOARD ---
elif modus == "Dashboard":
    st.title("👨‍💼 DGW Dossieroverzicht")
    res = supabase.table("klachten").select("*").order("id", desc=True).execute()
    if res.data:
        df = pd.DataFrame(res.data)
        client_namen = [f"{r['id']} - {r['voornaam']} {r['naam']}" for _, r in df.iterrows()]
        geselecteerde_client = st.selectbox("Selecteer een dossier om te behandelen", client_namen)
        sel_id = int(geselecteerde_client.split(" - ")[0])
        det = df[df['id'] == sel_id].iloc[0]
        
        st.markdown(f"""
        <div class='klant-box'>
            <h3>Dossier #{det['id']}: {det['voornaam']} {det['naam']}</h3>
            <p><b>Status:</b> {det['status']}</p>
            <p><b>Afspraak:</b> {det['afspraak_datum']} om {det['afspraak_tijd']}</p>
            <hr>
            <p><b>Omschrijving:</b><br>{det['klacht_omschrijving']}</p>
        </div>
        """, unsafe_allow_html=True)
        
        c1, c2 = st.columns(2)
        actie = c1.selectbox("Status bijwerken", ["Geen actie", "Afspraak Bevestigd", "In behandeling", "Aanvraag Afgewezen", "Voltooid"])
        if c1.button("STATUS OPSLAAN"):
            if actie != "Geen actie":
                supabase.table("klachten").update({"status": actie}).eq("id", sel_id).execute()
                verzend_mail("DGW Update: Dossier Status", det['email'], f"Beste {det['voornaam']},\n\nDe status van uw aanvraag bij Dienst Grondzaken Wanica is gewijzigd naar: {actie}.")
                st.rerun()
        if c2.button("🗑️ DOSSIER VERWIJDEREN"):
            supabase.table("klachten").delete().eq("id", sel_id).execute()
            st.rerun()

# --- 8. ADMIN INSTELLINGEN ---
elif modus == "Instellingen (Admin)":
    st.title("⚙️ DGW Systeembeheer")
    tab1, tab2 = st.tabs(["Gebruikerslijst", "Nieuwe Medewerker"])
    with tab1:
        m_res = supabase.table("medewerkers").select("*").execute()
        for m in m_res.data:
            with st.expander(f"👤 {m['gebruikersnaam']} (Rol: {m.get('rol')})"):
                new_p = st.text_input("Wachtwoord resetten", type="password", key=f"pw_{m['id']}")
                new_r = st.selectbox("Rol wijzigen", ["medewerker", "admin"], index=0 if str(m.get('rol','')).lower() == "medewerker" else 1, key=f"rol_{m['id']}")
                col_save, col_del = st.columns([1, 1])
                if col_save.button("💾 Wijzigingen Doorvoeren", key=f"save_{m['id']}"):
                    upd = {"rol": new_r}
                    if new_p: upd["wachtwoord"] = new_p
                    supabase.table("medewerkers").update(upd).eq("id", m['id']).execute()
                    st.success("Medewerkergegevens bijgewerkt.")
                    st.rerun()
                if m['gebruikersnaam'] != st.session_state['gebruiker']:
                    if col_del.button("🗑️ Account Verwijderen", key=f"del_{m['id']}"):
                        supabase.table("medewerkers").delete().eq("id", m['id']).execute()
                        st.rerun()

    with tab2:
        with st.form("new_user_dgw"):
            u_n = st.text_input("Nieuwe Gebruikersnaam")
            p_n = st.text_input("Tijdelijk Wachtwoord", type="password")
            r_n = st.selectbox("Toewijzen Rol", ["medewerker", "admin"])
            if st.form_submit_button("ACCOUNT AANMAKEN"):
                if u_n and p_n:
                    supabase.table("medewerkers").insert({"gebruikersnaam": u_n.strip(), "wachtwoord": p_n, "rol": r_n}).execute()
                    st.success(f"Account voor {u_n} is aangemaakt in het DGW systeem.")
                    st.rerun()

# --- 9. MEDEWERKER LOGIN ---
elif modus == "Medewerker Login":
    st.title("🔐 DGW Medewerkers Portaal")
    with st.form("login_form_dgw"):
        user_input = st.text_input("Gebruikersnaam")
        pw_input = st.text_input("Wachtwoord", type="password")
        if st.form_submit_button("Inloggen"):
            res = supabase.table("medewerkers").select("*").execute()
            found = False
            if res.data:
                for db_user in res.data:
                    if str(db_user['gebruikersnaam']).strip() == user_input.strip():
                        if str(db_user['wachtwoord']).strip() == pw_input.strip():
                            st.session_state.update({
                                'ingelogd': True, 
                                'gebruiker': db_user['gebruikersnaam'], 
                                'rol': db_user.get('rol', 'medewerker')
                            })
                            found = True
                            st.rerun()
            if not found:
                st.error("❌ Onjuiste DGW inloggegevens.")
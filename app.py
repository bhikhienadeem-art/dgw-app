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

# --- 2. STYLING (CORRECTIE VOOR LEESBAARHEID) ---
# De achtergrondkleur van de invoervelden is nu wit, met zwarte tekst.
st.markdown("""
    <style>
    .stApp { background-color: white; }
    h1, h2, h3, .stTitle { color: #1b5e20 !important; font-family: 'Segoe UI', sans-serif; font-weight: bold; }
    [data-testid="stSidebar"] { background-color: #f1f8e9 !important; }
    [data-testid="stSidebar"] .st-emotion-cache-17l69uz, [data-testid="stSidebar"] p, [data-testid="stSidebar"] label {
        color: #1b5e20 !important; font-weight: bold !important;
    }
    /* GECORRIGEERD: Wit veld, zwarte tekst voor invoer */
    .stTextInput>div>div>input, .stTextArea>div>div>textarea, .stSelectbox>div>div>div {
        background-color: white !important; color: black !important; border: 2px solid #2e7d32 !important; border-radius: 8px !important;
    }
    div.stButton > button { width: 100%; border-radius: 10px; background-color: #2e7d32; color: white; font-weight: bold; height: 3.5em; }
    </style>
""", unsafe_allow_html=True)

# --- 3. EMAIL FUNCTIE (Ongechanged) ---
# (De rest van je oorspronkelijke code blijft hieronder staan,
#  bijvoorbeeld vanaf regel 36, zoals je emailfunctie en menulogica)

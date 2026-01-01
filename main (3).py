import streamlit as st
import os
from openai import OpenAI
from fpdf import FPDF
import pdfplumber
from docx import Document
from io import BytesIO
import datetime

# --- CONFIGURATION ---
st.set_page_config(
    page_title="AppealOS | AI Denial Management", 
    layout="wide", 
    page_icon="🏥",
    initial_sidebar_state="collapsed"
)

# --- USER DATABASE (DEMO MODE) ---
USERS = {
    "admin": {
        "password": "admin123", 
        "name": "Dr. Lara Raj",
        "role": "Medical Director"
    },
    "staff": {
        "password": "staff123", 
        "name": "Dr. John Smith",
        "role": "Senior Resident"
    }
}

# --- ROBUST CSS THEME ---
def local_css():
    st.markdown("""
    <style>
        @import url('https://fonts.googleapis.com/css2?family=Inter:wght@300;400;600;800&display=swap');
        
        /* 1. BACKGROUND & GLOBAL TEXT */
        .stApp {
            background-color: #f8fafc; /* Light Gray Background */
        }
        
        /* 2. FORCE ALL HEADERS TO BE DARK */
        h1, h2, h3, h4, h5, h6 {
            color: #0f172a !important; /* Dark Navy/Black */
            font-family: 'Inter', sans-serif !important;
        }
        
        /* 3. FORCE NORMAL TEXT TO BE DARK */
        p, div, span, label, li {
            color: #334155 !important; /* Dark Slate */
            font-family: 'Inter', sans-serif !important;
        }
        
        /* 4. FORCE INPUT BOXES TO BE WHITE */
        input[type="text"], input[type="password"], textarea {
            background-color: #ffffff !important;
            color: #0f172a !important; /* Black Text */
            border: 1px solid #cbd5e1 !important;
        }
        
        /* Fix the Label above the input */
        .stTextInput > label, .stTextArea > label {
            color: #0f172a !important;
            font-weight: 600 !important;
        }
        
        /* 5. HERO HEADERS SPECIFIC */
        .hero-header { 
            font-weight: 800; 
            color: #0f172a !important; 
            text-align: center; 
            line-height: 1.2;
            margin-bottom: 1rem;
        }
        .hero-sub { 
            font-size: 1.15rem; 
            color: #334155 !important; 
            text-align: center; 
            margin-bottom: 2.5rem; 
            max-width: 700px;
            margin-left: auto;
            margin-right: auto;
            line-height: 1.6;
        }

        /* 6. RESPONSIVE SIZES */
        @media (min-width: 768px) { .hero-header { font-size: 3.5rem; } }
        @media (max-width: 768px) { .hero-header { font-size: 2.5rem; } }
        
        /* 7. FEATURE CARDS */
        .feature-card {
            background-color: #ffffff !important;
            padding: 1.5rem;
            border-radius: 12px;
            box-shadow: 0 4px 6px -1px rgba(0, 0, 0, 0.1);
            border: 1px solid #cbd5e1;
            text-align: center;
        }
        
        /* Force card text color explicitly */
        .feature-card h3 { color: #0f172a !important; }
        .feature-card p { color: #334155 !important; }
        
        /* 8. BUTTONS */
        div.stButton > button:first-child { 
            background: #2563eb !important; 
            color: #ffffff !important;
            border-radius: 8px; 
            border: none; 
            padding: 0.6rem 1.2rem; 
            font-weight: 600; 
        }
        
        /* 9. GLASS CONTAINERS */
        [data-testid="stVerticalBlockBorderWrapper"] { 
            border-radius: 12px; 
            padding: 2rem; 
            background: #ffffff;
            border: 1px solid #e2e8f0; 
            box-shadow: 0 4px 6px -1px rgba(0, 0, 0, 0.05); 
        }
    </style>
    """, unsafe_allow_html=True)

local_css()

# --- STATE MANAGEMENT ---
if 'page' not in st.session_state: st.session_state.page = "landing"
if 'user' not in st.session_state: st.session_state.user = None

def navigate_to(page):
    st.session_state.page = page
    st.rerun()

# --- CREDENTIALS ---
try:
    api_key = st.secrets["OPENAI_API_KEY"]
    tavily_key = st.secrets["TAVILY_API_KEY"]
    # Supabase is optional
    supabase_url = st.secrets.get("SUPABASE_URL", "")
    supabase_key = st.secrets.get("SUPABASE_KEY", "")
except:
    st.error("🚨 Secrets Missing.

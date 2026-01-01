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

# --- ROBUST CSS THEME (FINAL CONTRAST FIX) ---
def local_css():
    st.markdown("""
    <style>
        @import url('https://fonts.googleapis.com/css2?family=Inter:wght@300;400;600;800&display=swap');
        
        /* 1. BACKGROUND & GLOBAL TEXT */
        .stApp {
            background-color: #f8fafc; /* Light Gray Background */
        }
        
        /* 2. FORCE ALL HEADERS TO BE DARK (The Fix) */
        h1, h2, h3, h4, h5, h6 {
            color: #0f172a !important; /* Dark Navy/Black */
            font-family: 'Inter', sans-serif !important;
        }
        
        /* 3. FORCE NORMAL TEXT TO BE DARK */
        p, div, span, label {
            color: #334155 !important; /* Dark Slate */
            font-family: 'Inter', sans-serif !important;
        }
        
        /* 4. HERO HEADERS SPECIFIC */
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

        /* 5. RESPONSIVE SIZES */
        @media (min-width: 768px) { .hero-header { font-size: 3.5rem; } }
        @media (max-width: 768px) { .hero-header { font-size: 2.5rem; } }
        
        /* 6. FEATURE CARDS */
        .feature-card {
            background-color: #ffffff !important;
            padding: 1.5rem;
            border-radius: 12px;
            box-shadow: 0 4px 6px -1px rgba(0, 0, 0, 0.1);
            border: 1px solid #cbd5e1;
            text-align: center;
        }
        
        /* 7. BUTTONS */
        /* We exclude buttons from the global color rule so they stay white text on blue background */
        div.stButton > button:first-child { 
            background: #2563eb !important; 
            color: #ffffff !important;
            border-radius: 8px; 
            border: none; 
            padding: 0.6rem 1.2rem; 
            font-weight: 600; 
        }
        
        /* 8. GLASS CONTAINERS */
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
    st.error("🚨 Secrets Missing")
    st.stop()

client = OpenAI(api_key=api_key)
from tavily import TavilyClient
tavily = TavilyClient(api_key=tavily_key)
try:
    from supabase import create_client
    supabase = create_client(supabase_url, supabase_key)
except: supabase = None

# --- PAGE 1: LANDING PAGE ---
if st.session_state.page == "landing":
    
    # 1. Navbar (The "### AppealOS" title works now because of the H3 CSS rule)
    c1, c2 = st.columns([1, 5])
    with c1: st.markdown("### 🏥 AppealOS")

    # 2. Hero Section
    st.markdown("<br>", unsafe_allow_html=True)
    st.markdown('<div class="hero-header">Fight Insurance Denials<br>in Seconds.</div>', unsafe_allow_html=True)
    
    st.markdown("""
    <div class="hero-sub">
    AppealOS is an AI agent that <b>reads denial letters</b>, <b>researches payer policies</b> (Aetna, BCBS, etc.), 
    and <b>writes legal-grade appeals</b> instantly. Stop fighting paperwork. Start recovering revenue.
    </div>
    """, unsafe_allow_html=True)
    
    # 3. Call to Action
    col1, col2, col3 = st.columns([1, 1, 1])
    with col2:
        if st.button("🚀 Launch Workspace", use_container_width=True):
            navigate_to("login")
    
    # 4. Feature Grid
    st.markdown("<br><br>", unsafe_allow_html=True)
    f1, f2, f3 = st.columns(3)
    
    with f1:
        st.markdown("""
        <div class="feature-card">
            <div style="font-size: 2.5rem;">📄</div>
            <h3>Reads Documents</h3>
            <p>Upload any PDF denial letter. Our Computer Vision extracts codes, patient data, and denial reasons.</p>
        </div>
        """, unsafe_allow_html=True)
    
    with f2:
        st.markdown("""
        <div class="feature-card">
            <div style="font-size: 2.5rem;">🧠</div>
            <h3>Researches Policy</h3>
            <p>The AI Agent browses live insurance websites to find the exact coverage rule you need.</p>
        </div>
        """, unsafe_allow_html=True)
        
    with f3:
        st.markdown("""
        <div class="feature-card">
            <div style="font-size: 2.5rem;">✍️</div>
            <h3>Writes Appeals</h3>
            <p>Generates specific, cited legal arguments. Download as PDF or editable Word Doc.</p>
        </div>
        """, unsafe_allow_html=True)

    st.stop()

# --- PAGE 2: LOGIN ---
if st.session_state.page == "login":
    if st.button("← Back to Home"): navigate_to("landing")
    
    c1, c2, c3 = st.columns([1,1,1])
    with c2:
        st.markdown("<br>", unsafe_allow_html=True)
        with st.container(border=True):
            st.markdown("### 👨‍⚕️ Doctor Login")
            username = st.text_input("Username")
            password = st.text_input("Password", type="password")
            
            if st.button("Sign In", use_container_width=True):
                if username in USERS and USERS[username]["password"] == password:
                    st.session_state.user = USERS[username]
                    navigate_to("app")
                else:
                    st.error("Invalid Username or Password")
    st.stop()

# --- PAGE 3: THE APP ---
current_user = st.session_state.user
if not current_user: navigate_to("landing")

with st.sidebar:
    st.title("🏥 AppealOS")
    st.markdown("---")
    st.markdown(f"### 👋 Welcome, \n**{current_user['name']}**")
    st.caption(current_user['role'])
    st.markdown("---")
    if st.button("Log Out"):
        st.session_state.user = None
        navigate_to("landing")

# FUNCTIONS
def extract_from_pdf(f):
    try:
        with pdfplumber.open(f) as pdf: t = "".join([p.extract_text() for p in pdf.pages])
        p = f"Extract: 1.Patient 2.Insurance 3.Reason from: {t[:3000]}"
        return client.chat.completions.create(model="gpt-4o", messages=[{"role":"user", "content":p}]).choices[0].message.content
    except: return "Error"

def research(ins, proc):
    try: return "\n".join([r['content'] for r in tavily.search(query=f"{ins} policy {proc} 2024", max_results=3)['results']])
    except: return "Manual Search Needed"

def create_files(txt, pat):
    pdf = FPDF(); pdf.add_page(); pdf.set_font("Arial", size=11); pdf.multi_cell(0, 6, txt.encode('latin-1','replace').decode('latin-1'))
    doc = Document(); doc.add_paragraph(txt); b = BytesIO(); doc.save(b); b.seek(0)
    return pdf.output(dest="S").encode('latin-1'), b

# MAIN UI
st.title("My Workspace")

with st.container(border=True):
    uf = st.file_uploader("📂 Upload Denial", type="pdf")
    if uf and 'scan' not in st.session_state:
        st.session_state['scan'] = extract_from_pdf(uf)
        st.success("Scanned")

if 'scan' in st.session_state: st.info(st.session_state['scan'])

c1, c2, c3 = st.columns(3)
with c1: pn = st.text_input("Patient", "John Doe")
with c2: ins = st.text_input("Insurance")
with c3: proc = st.text_input("Procedure")

col_left, col_right = st.columns([1,1])

with col_left:
    st.subheader("Clinical Notes")
    if hasattr(st, "audio_input"):
        av = st.audio_input("Dictate")
    else:
        av = None
        st.warning("Update Streamlit")
        
    if av: 
        st.session_state['v_txt'] = client.audio.transcriptions.create(model="whisper-1", file=av).text
        st.success("Saved")

with col_right:
    st.subheader("Actions")
    if st.button("✨ Generate Appeal", type="primary", use_container_width=True):
        vn = st.session_state.get('v_txt')
        if vn:
            with st.status("Researching..."): pol = research(ins, proc)
            with st.spinner("Writing..."):
                pmt = f"Write appeal. Author: {current_user['name']}. Pat: {pn}. Ins: {ins}. Note: {vn}. Pol: {pol}"
                st.session_state['final'] = client.chat.completions.create(model="gpt-4o", messages=[{"role":"user", "content":pmt}]).choices[0].message.content
        else: st.warning("Dictate notes first.")

if 'final' in st.session_state:
    st.markdown("---")
    txt = st.text_area("Draft", st.session_state['final'], height=300)
    
    try:
        pdf, doc = create_files(txt, pn)
        files_ok = True
    except:
        files_ok = False
        st.error("Error creating files")

    if files_ok:
        b1, b2, b3 = st.columns(3)
        with b1:
            if st.button("💾 Save to DB"):
                if supabase:
                    try:
                        data = {
                            "patient_name": pn, 
                            "final_letter": txt, 
                            "created_at": str(datetime.datetime.now()),
                            "doctor_name": current_user['name']
                        }
                        supabase.table("appeals").insert(data).execute()
                        st.toast(f"Saved by {current_user['name']}")
                    except Exception as e:
                        st.error(f"DB Error: {e}")
                else:
                    st.warning("Database not connected")
        with b2: st.download_button("PDF", pdf, "appeal.pdf")
        with b3: st.download_button("Word", doc, "appeal.docx")

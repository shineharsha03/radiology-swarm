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

# --- USER DATABASE ---
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

# --- CSS THEME ---
def local_css():
    st.markdown(
        """
        <style>
            @import url('https://fonts.googleapis.com/css2?family=Inter:wght@300;400;600;800&display=swap');
            
            .stApp {
                background-color: #f8fafc;
            }
            
            h1, h2, h3, h4, h5, h6 {
                color: #0f172a !important;
                font-family: 'Inter', sans-serif !important;
            }
            
            p, div, span, label, li {
                color: #334155 !important;
                font-family: 'Inter', sans-serif !important;
            }
            
            input[type="text"], input[type="password"], textarea {
                background-color: #ffffff !important;
                color: #0f172a !important;
                border: 1px solid #cbd5e1 !important;
            }
            
            .stTextInput > label, .stTextArea > label {
                color: #0f172a !important;
                font-weight: 600 !important;
            }
            
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

            @media (min-width: 768px) { .hero-header { font-size: 3.5rem; } }
            @media (max-width: 768px) { .hero-header { font-size: 2.5rem; } }
            
            .feature-card {
                background-color: #ffffff !important;
                padding: 1.5rem;
                border-radius: 12px;
                box-shadow: 0 4px 6px -1px rgba(0, 0, 0, 0.1);
                border: 1px solid #cbd5e1;
                text-align: center;
            }
            
            .feature-card h3 { color: #0f172a !important; }
            .feature-card p { color: #334155 !important; }
            
            div.stButton > button:first-child { 
                background: #2563eb !important; 
                color: #ffffff !important;
                border-radius: 8px; 
                border: none; 
                padding: 0.6rem 1.2rem; 
                font-weight: 600; 
            }
            
            [data-testid="stVerticalBlockBorderWrapper"] { 
                border-radius: 12px; 
                padding: 2rem; 
                background: #ffffff;
                border: 1px solid #e2e8f0; 
                box-shadow: 0 4px 6px -1px rgba(0, 0, 0, 0.05); 
            }
        </style>
        """, 
        unsafe_allow_html=True
    )

local_css()

# --- STATE MANAGEMENT ---
if 'page' not in st.session_state: 
    st.session_state.page = "landing"
if 'user' not in st.session_state: 
    st.session_state.user = None

def navigate_to(page):
    st.session_state.page = page
    st.rerun()

# --- CREDENTIALS ---
try:
    api_key = st.secrets["OPENAI_API_KEY"]
    tavily_key = st.secrets["TAVILY_API_KEY"]
    supabase_url = st.secrets.get("SUPABASE_URL", "")
    supabase_key = st.secrets.get("SUPABASE_KEY", "")
except:
    st.error("🚨 Secrets Missing. Check .streamlit/secrets.toml")
    st.stop()

client = OpenAI(api_key=api_key)
from tavily import TavilyClient
tavily = TavilyClient(api_key=tavily_key)
try:
    from supabase import create_client
    supabase = create_client(supabase_url, supabase_key)
except: 
    supabase = None

# --- PAGE 1: LANDING PAGE ---
if st.session_state.page == "landing":
    
    # Navbar
    c1, c2 = st.columns([1, 5])
    with c1: 
        st.markdown("### 🏥 AppealOS")

    # Hero Section
    st.markdown("<br>", unsafe_allow_html=True)
    
    st.markdown(
        '<div class="hero-header">Fight Insurance Denials<br>in Seconds.</div>', 
        unsafe_allow_html=True
    )
    
    st.markdown(
        """
        <div class="hero-sub">
        AppealOS is an AI agent that <b>reads denial letters</b>, 
        <b>researches payer policies</b> (Aetna, BCBS, etc.), 
        and <b>writes legal-grade appeals</b> instantly.
        </div>
        """, 
        unsafe_allow_html=True
    )
    
    # Call to Action
    col1, col2, col3 = st.columns([1, 1, 1])
    with col2:
        if st.button("🚀 Launch Workspace", use_container_width=True):
            navigate_to("login")
    
    # Feature Grid
    st.markdown("<br><br>", unsafe_allow_html=True)
    f1, f2, f3 = st.columns(3)
    
    with f1:
        st.markdown(
            """
            <div class="feature-card">
                <div style="font-size: 2.5rem;">📄</div>
                <h3>Reads Documents</h3>
                <p>Upload any PDF denial letter. Our Computer Vision extracts codes.</p>
            </div>
            """, 
            unsafe_allow_html=True
        )
    
    with f2:
        st.markdown(
            """
            <div class="feature-card">
                <div style="font-size: 2.5rem;">🧠</div>
                <h3>Researches Policy</h3>
                <p>The AI Agent browses live insurance websites to find exact coverage rules.</p>
            </div>
            """, 
            unsafe_allow_html=True
        )
        
    with f3:
        st.markdown(
            """
            <div class="feature-card">
                <div style="font-size: 2.5rem;">✍️</div>
                <h3>Writes Appeals</h3>
                <p>Generates specific, cited legal arguments. Download as PDF or Word.</p>
            </div>
            """, 
            unsafe_allow_html=True
        )

    st.stop()

# --- PAGE 2: LOGIN ---
if st.session_state.page == "login":
    if st.button("← Back to Home"): 
        navigate_to("landing")
    
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
if not current_user: 
    navigate_to("landing")

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
        with pdfplumber.open(f) as pdf: 
            t = "".join([p.extract_text() for p in pdf.pages])
        
        prompt_text = f"Extract: 1.Patient 2.Insurance 3.Reason from: {t[:3000]}"
        
        response = client.chat.completions.create(
            model="gpt-4o", 
            messages=[{"role":"user", "content":prompt_text}]
        )
        return response.choices[0].message.content
    except: 
        return "Error"

def research(ins, proc):
    try: 
        search_query = f"{ins} policy {proc} 2024"
        results = tavily.search(query=search_query, max_results=3)['results']
        return "\n".join([r['content'] for r in results])
    except: 
        return "Manual Search Needed"

def create_files(txt, pat):
    pdf = FPDF()
    pdf.add_page()
    pdf.set_font("Arial", size=11)
    
    clean_txt = txt.encode('latin-1','replace').decode('latin-1')
    pdf.multi_cell(0, 6, clean_txt)
    
    doc = Document()
    doc.add_paragraph(txt)
    b = BytesIO()
    doc.save(b)
    b.seek(0)
    
    return pdf.output(dest="S").encode('latin-1'), b

# MAIN UI
st.title("My Workspace")

with st.container(border=True):
    uf = st.file_uploader("📂 Upload Denial", type="pdf")
    if uf and 'scan' not in st.session_state:
        st.session_state['scan'] = extract_from_pdf(uf)
        st.success("Scanned")

if 'scan' in st.session_state: 
    st.info(st.session_state['scan'])

c1, c2, c3 = st.columns(3)
with c1: 
    pn = st.text_input("Patient", "John Doe")
with c2: 
    ins = st.text_input("Insurance")
with c3: 
    proc = st.text_input("Procedure")

col_left, col_right = st.columns([1,1])

with col_left:
    st.subheader("Clinical Notes")
    if hasattr(st, "audio_input"):
        av = st.audio_input("Dictate")
    else:
        av = None
        st.warning("Update Streamlit")
        
    if av: 
        transcription = client.audio.transcriptions.create(
            model="whisper-1", 
            file=av
        )
        st.session_state['v_txt'] = transcription.text
        st.success("Saved")

with col_right:
    st.subheader("Actions")
    if st.button("✨ Generate Appeal", type="primary", use_container_width=True):
        vn = st.session_state.get('v_txt')
        if vn:
            with st.status("Researching..."): 
                pol = research(ins, proc)
            with st.spinner("Writing..."):
                
                final_prompt = f"""
                Write appeal. 
                Author: {current_user['name']}. 
                Pat: {pn}. 
                Ins: {ins}. 
                Note: {vn}. 
                Pol: {pol}
                """
                
                response = client.chat.completions.create(
                    model="gpt-4o", 
                    messages=[{"role":"user", "content":final_prompt}]
                )
                st.session_state['final'] = response.choices[0].message.content
        else: 
            st.warning("Dictate notes first.")

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
        with b2: 
            st.download_button("PDF", pdf, "appeal.pdf")
        with b3: 
            st.download_button("Word", doc, "appeal.docx")

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
    page_title="AppealOS | AI for Healthcare", 
    layout="wide", 
    page_icon="🏥",
    initial_sidebar_state="collapsed"
)

# --- MODERN CSS THEME (Glassmorphism) ---
def local_css():
    st.markdown("""
    <style>
        @import url('https://fonts.googleapis.com/css2?family=Inter:wght@300;400;600;800&display=swap');
        
        /* Global Font */
        html, body, [class*="css"] { font-family: 'Inter', sans-serif; color: #1e293b; }
        
        /* Landing Page Hero */
        .hero-header { 
            font-size: 3.5rem; 
            font-weight: 800; 
            color: #0f172a; 
            text-align: center; 
            line-height: 1.1; 
            margin-bottom: 1rem;
        }
        .hero-sub { 
            font-size: 1.2rem; 
            color: #475569; 
            text-align: center; 
            margin-bottom: 3rem; 
            max-width: 800px;
            margin-left: auto; 
            margin-right: auto;
        }
        
        /* Modern Cards (Glassmorphism) */
        [data-testid="stVerticalBlockBorderWrapper"] {
            border-radius: 16px; 
            padding: 2rem; 
            background: rgba(255, 255, 255, 0.9);
            border: 1px solid #e2e8f0;
            box-shadow: 0 10px 15px -3px rgba(0, 0, 0, 0.05);
            backdrop-filter: blur(10px);
        }
        
        /* Buttons */
        div.stButton > button:first-child {
            background: linear-gradient(135deg, #2563eb 0%, #1d4ed8 100%);
            color: white; 
            border-radius: 50px; 
            border: none;
            padding: 0.75rem 2rem; 
            font-weight: 600;
            font-size: 1rem;
            transition: all 0.3s ease;
            box-shadow: 0 4px 6px -1px rgba(37, 99, 235, 0.2);
        }
        div.stButton > button:first-child:hover { 
            transform: translateY(-2px);
            box-shadow: 0 10px 15px -3px rgba(37, 99, 235, 0.3);
        }
        
        /* Sidebar Styling */
        [data-testid="stSidebar"] {
            background-color: #f8fafc;
            border-right: 1px solid #e2e8f0;
        }
    </style>
    """, unsafe_allow_html=True)

local_css()

# --- STATE MANAGEMENT ---
if 'page' not in st.session_state:
    st.session_state.page = "landing"
if 'authenticated' not in st.session_state:
    st.session_state.authenticated = False

def navigate_to(page):
    st.session_state.page = page
    st.rerun()

# --- 1. CREDENTIALS ---
try:
    api_key = st.secrets["OPENAI_API_KEY"]
    supabase_url = st.secrets.get("SUPABASE_URL", "")
    supabase_key = st.secrets.get("SUPABASE_KEY", "")
    clinic_password = st.secrets["CLINIC_PASSWORD"]
    tavily_key = st.secrets["TAVILY_API_KEY"]
except KeyError:
    st.error("🚨 System Error: Secrets missing.")
    st.stop()

client = OpenAI(api_key=api_key)
from tavily import TavilyClient
tavily = TavilyClient(api_key=tavily_key)
try:
    from supabase import create_client
    supabase = create_client(supabase_url, supabase_key)
except:
    supabase = None

# --- PAGE 1: THE LANDING PAGE ---
if st.session_state.page == "landing":
    
    # Navbar (Fake)
    c1, c2 = st.columns([1, 4])
    with c1:
        st.markdown("### 🏥 AppealOS")
    with c2:
        st.write("") # Spacer

    # Hero Section
    st.markdown("<br>", unsafe_allow_html=True)
    st.markdown('<div class="hero-header">Stop Denials.<br>Start Revenue.</div>', unsafe_allow_html=True)
    st.markdown('<div class="hero-sub">The AI-powered revenue cycle manager that researches policies, writes medical appeals, and recovers lost revenue in seconds.</div>', unsafe_allow_html=True)
    
    # Call to Action
    col1, col2, col3 = st.columns([1, 1, 1])
    with col2:
        if st.button("🚀 Launch App", use_container_width=True):
            navigate_to("login")
    
    # Features Grid
    st.markdown("<br><br>", unsafe_allow_html=True)
    f1, f2, f3 = st.columns(3)
    
    with f1:
        with st.container(border=True):
            st.markdown("### 🤖 AI Researcher")
            st.write("Automatically searches Aetna, Cigna, and BCBS policies in real-time.")
    
    with f2:
        with st.container(border=True):
            st.markdown("### 👁️ Document Vision")
            st.write("Drag & drop denial PDFs. The AI extracts codes and patient data instantly.")
            
    with f3:
        with st.container(border=True):
            st.markdown("### 📝 Legal Writer")
            st.write("Generates medical necessity letters citing specific clinical guidelines.")
            
    st.stop()


# --- PAGE 2: LOGIN SCREEN ---
if st.session_state.page == "login":
    
    if st.button("← Back to Home"):
        navigate_to("landing")

    if not st.session_state.authenticated:
        c1, c2, c3 = st.columns([1,1,1])
        with c2:
            st.markdown("<br><br>", unsafe_allow_html=True)
            with st.container(border=True):
                st.markdown("### 🔐 Client Portal")
                st.text_input("Access Key", type="password", key="password_input")
                
                if st.button("Sign In", use_container_width=True):
                    if st.session_state.password_input == clinic_password:
                        st.session_state.authenticated = True
                        st.rerun()
                    else:
                        st.error("Invalid Key")
        st.stop()


# --- PAGE 3: THE APP (Only if Authenticated) ---

# Sidebar Navigation
with st.sidebar:
    st.markdown("### 🏥 AppealOS")
    st.caption("Enterprise Edition")
    st.markdown("---")
    st.info("🟢 System Active")
    if st.button("Log Out"):
        st.session_state.authenticated = False
        navigate_to("landing")

# Core Functions (Same as before)
def extract_from_pdf(uploaded_file):
    try:
        with pdfplumber.open(uploaded_file) as pdf:
            text = ""
            for page in pdf.pages:
                text += page.extract_text() or ""
        prompt = f"Analyze this denial letter. Extract: 1. Patient 2. Insurance 3. Reason. Text: {text[:4000]}"
        response = client.chat.completions.create(model="gpt-4o", messages=[{"role":"user", "content": prompt}])
        return response.choices[0].message.content
    except: return "Error reading PDF"

def research_policy(insurance, procedure):
    try:
        q = f"{insurance} coverage policy {procedure} medical necessity 2024"
        res = tavily.search(query=q, search_depth="advanced", max_results=3)
        return "\n".join([r['content'] for r in res['results']])
    except: return "Search failed"

def create_pdf(text, p):
    pdf = FPDF(); pdf.add_page(); pdf.set_font("Arial", size=11)
    pdf.multi_cell(0, 6, text.encode('latin-1', 'replace').decode('latin-1'))
    return pdf.output(dest="S").encode("latin-1")

def create_docx(text, p):
    doc = Document(); doc.add_paragraph(text)
    b = BytesIO(); doc.save(b); b.seek(0); return b

# Main UI
st.title("AppealOS Dashboard")

# App Layout
with st.container(border=True):
    uploaded_file = st.file_uploader("📂 Upload Denial Letter (PDF)", type="pdf")
    if uploaded_file and 'pdf_analyzed' not in st.session_state:
        with st.spinner("Scanning..."):
            st.session_state['pdf_analysis'] = extract_from_pdf(uploaded_file)
            st.session_state['pdf_analyzed'] = True
            st.success("Scanned")

if 'pdf_analysis' in st.session_state:
    st.info(f"**Findings:** {st.session_state['pdf_analysis']}")

c1, c2, c3 = st.columns(3)
with c1: patient_name = st.text_input("Patient Name", value="John Doe")
with c2: insurance_name = st.text_input("Insurance")
with c3: procedure_name = st.text_input("Procedure")

c_left, c_right = st.columns([1, 1], gap="large")

with c_left:
    st.subheader("1. Defense")
    audio_val = st.audio_input("Dictate Notes")
    if audio_val:
        with st.spinner("Transcribing..."):
            t = client.audio.transcriptions.create(model="whisper-1", file=audio_val)
            st.session_state['voice_result'] = t.text
        st.success("Saved")

with c_right:
    st.subheader("2. Resolution")
    if st.button("✨ Generate Package", type="primary", use_container_width=True):
        vn = st.session_state.get('voice_result')
        if vn:
            with st.status("🕵️ AI Researching...", expanded=True):
                pol = research_policy(insurance_name, procedure_name)
                st.write(pol)
            
            with st.spinner("Drafting..."):
                prompt = f"Write appeal. Patient: {patient_name}. Ins: {insurance_name}. Notes: {vn}. Policy: {pol}"
                r = client.chat.completions.create(model="gpt-4o", messages=[{"role":"user", "content": prompt}])
                st.session_state['final_letter'] = r.choices[0].message.content
        else: st.warning("Need dictation.")

    if 'final_letter' in st.session_state:
        st.markdown("---")
        lc = st.text_area("Draft", st.session_state['final_letter'], height=300)
        try:
            pdf = create_pdf(lc, patient_name)
            doc = create_docx(lc, patient_name)
            
            b1, b2, b3 = st.columns(3)
            with b1: 
                if st.button("💾 Save"):
                    if supabase: supabase.table("appeals").insert({"patient_name":patient_name, "final_letter":lc}).execute()
                    st.toast("Saved")
            with b2: st.download_button("📄 PDF", pdf, "appeal.pdf")
            with b3: st.download_button("📝 Word", doc, "appeal.docx")
        except: st.error("File error")

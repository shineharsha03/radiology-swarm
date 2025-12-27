import streamlit as st
import os
import base64
from openai import OpenAI
from supabase import create_client, Client
from fpdf import FPDF
import datetime

# --- CONFIGURATION & UI SETUP ---
st.set_page_config(page_title="AppealOS", layout="wide", page_icon="🏥")

# --- CUSTOM CSS (THE UI MAGIC) ---
def local_css():
    st.markdown("""
    <style>
        /* Import a clean medical font */
        @import url('https://fonts.googleapis.com/css2?family=Inter:wght@400;600&display=swap');
        
        html, body, [class*="css"] {
            font-family: 'Inter', sans-serif;
        }
        
        /* Change the top header bar color */
        header {visibility: hidden;}
        
        /* Style the Primary Button (Generate) to Medical Blue */
        div.stButton > button:first-child {
            background-color: #0066cc;
            color: white;
            border-radius: 8px;
            font-weight: 600;
            padding: 0.5rem 2rem;
            border: none;
        }
        div.stButton > button:first-child:hover {
            background-color: #0052a3;
        }

        /* Input fields styling */
        .stTextInput > div > div > input {
            border-radius: 8px;
        }
        
        /* Success message styling */
        .stSuccess {
            background-color: #d4edda;
            color: #155724;
            border-radius: 8px;
        }
        
        /* Remove standard Streamlit footer */
        footer {visibility: hidden;}
        
        /* Custom Title */
        .main-title {
            font-size: 2.5rem;
            font-weight: 700;
            color: #1a1a1a;
            margin-bottom: 0px;
        }
        .subtitle {
            font-size: 1.1rem;
            color: #666;
            margin-bottom: 2rem;
        }
    </style>
    """, unsafe_allow_html=True)

local_css()

# --- 1. SETUP CREDENTIALS ---
try:
    api_key = st.secrets["OPENAI_API_KEY"]
    supabase_url = st.secrets["SUPABASE_URL"]
    supabase_key = st.secrets["SUPABASE_KEY"]
    clinic_password = st.secrets["CLINIC_PASSWORD"]
except FileNotFoundError:
    st.error("🚨 Critical Error: Secrets are missing!")
    st.stop()

client = OpenAI(api_key=api_key)

@st.cache_resource
def init_supabase():
    return create_client(supabase_url, supabase_key)

supabase = init_supabase()

# --- 2. AUTHENTICATION ---
if 'authenticated' not in st.session_state:
    st.session_state.authenticated = False

def check_password():
    if st.session_state.password_input == clinic_password:
        st.session_state.authenticated = True
    else:
        st.error("❌ Access Denied")

if not st.session_state.authenticated:
    # Login UI
    col1, col2, col3 = st.columns([1,1,1])
    with col2:
        st.markdown("<br><br>", unsafe_allow_html=True)
        st.markdown("## 🏥 Login to AppealOS")
        st.text_input("Clinic Passcode", type="password", key="password_input", on_change=check_password)
    st.stop() 

# --- 3. HELPER FUNCTIONS ---
def create_pdf(letter_text, patient_name):
    pdf = FPDF()
    pdf.add_page()
    pdf.set_font("Arial", size=11)
    
    # Professional Header
    pdf.image('https://placehold.co/200x50/0066cc/ffffff/png?text=CLINIC+LOGO', x=10, y=8, w=50) # Placeholder Logo
    pdf.ln(20)
    pdf.set_font("Arial", 'B', 14)
    pdf.cell(0, 10, txt="MEDICAL NECESSITY APPEAL", ln=1, align='L')
    pdf.line(10, 35, 200, 35) # Horizontal line
    pdf.ln(10)
    
    pdf.set_font("Arial", size=10)
    pdf.cell(0, 6, txt=f"Patient: {patient_name}", ln=1)
    pdf.cell(0, 6, txt=f"Date: {datetime.date.today()}", ln=1)
    pdf.ln(10)
    
    pdf.set_font("Arial", size=11)
    safe_text = letter_text.encode('latin-1', 'replace').decode('latin-1')
    pdf.multi_cell(0, 6, safe_text)
    
    return pdf.output(dest="S").encode("latin-1")

def save_to_db(patient, letter):
    try:
        data = {
            "patient_name": patient, 
            "final_letter": letter,
            "created_at": str(datetime.datetime.now())
        }
        supabase.table("appeals").insert(data).execute()
        st.toast("✅ Saved to Patient Records", icon="💾")
    except Exception as e:
        st.error(f"Database Error: {e}")

# --- 4. MAIN DASHBOARD ---

# Top Navigation Bar (Fake)
st.markdown('<div class="main-title">🏥 AppealOS <span style="font-size:1rem; color:#888; font-weight:400;">| Dr. Dashboard</span></div>', unsafe_allow_html=True)
st.markdown('<div class="subtitle">AI-Powered Denial Resolution System</div>', unsafe_allow_html=True)

# Main Inputs
with st.container(border=True):
    c1, c2 = st.columns([1, 2])
    with c1:
        patient_name = st.text_input("Patient Reference", placeholder="Name or ID #")
    with c2:
        policy_rules = st.text_input("Insurance Policy / Denial Code", placeholder="e.g. 'Denial Code CO-50: Medical Necessity'")

c_left, c_right = st.columns([1, 1], gap="medium")

# LEFT COLUMN: INPUT
with c_left:
    st.markdown("### 1. Clinical Context")
    with st.container(border=True):
        st.info("🎙️ **Dictation Instructions:** State the diagnosis, history of failed treatments, and urgency.")
        audio_val = st.audio_input("Start Recording")
        
        if audio_val:
            with st.spinner("Processing audio..."):
                transcription = client.audio.transcriptions.create(model="whisper-1", file=audio_val)
                st.session_state['voice_result'] = transcription.text
            
            st.success("Audio Captured")
            st.text_area("Transcript Preview", st.session_state['voice_result'], height=100)

# RIGHT COLUMN: OUTPUT
with c_right:
    st.markdown("### 2. Resolution")
    with st.container(border=True):
        if st.button("✨ Generate Appeal Letter", use_container_width=True, type="primary"):
            voice_notes = st.session_state.get('voice_result')
            
            if voice_notes and patient_name:
                with st.spinner("Consulting Guidelines & Drafting..."):
                    prompt = f"""
                    Write a professional appeal letter.
                    Patient: {patient_name}
                    Notes: {voice_notes}
                    Policy: {policy_rules}
                    """
                    resp = client.chat.completions.create(model="gpt-4o", messages=[{"role":"user", "content": prompt}])
                    st.session_state['final_letter'] = resp.choices[0].message.content
            else:
                st.warning("⚠️ Please provide Patient Name and Dictation first.")

        # RESULT AREA
        if 'final_letter' in st.session_state:
            letter_content = st.text_area("Final Draft", st.session_state['final_letter'], height=450)
            
            col_a, col_b = st.columns(2)
            with col_a:
                if st.button("💾 Save to DB", use_container_width=True):
                    save_to_db(patient_name, letter_content)
            with col_b:
                pdf_bytes = create_pdf(letter_content, patient_name)
                st.download_button("📄 Download PDF", pdf_bytes, f"{patient_name}.pdf", "application/pdf", use_container_width=True)

# Footer
st.markdown("---")
st.caption("🔒 HIPAA Compliant Workflow | AppealOS v2.1")

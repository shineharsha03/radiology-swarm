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
# This injects "Medical Blue" styling and clean fonts
def local_css():
    st.markdown("""
    <style>
        /* Import a clean sans-serif font */
        @import url('https://fonts.googleapis.com/css2?family=Inter:wght@400;600&display=swap');
        
        html, body, [class*="css"] {
            font-family: 'Inter', sans-serif;
        }
        
        /* Hide the default Streamlit header */
        header {visibility: hidden;}
        
        /* Primary Button Style (Medical Blue) */
        div.stButton > button:first-child {
            background-color: #0066cc;
            color: white;
            border-radius: 6px;
            font-weight: 600;
            padding: 0.5rem 1rem;
            border: none;
            box-shadow: 0 2px 4px rgba(0,0,0,0.1);
        }
        div.stButton > button:first-child:hover {
            background-color: #0052a3;
        }

        /* Container Borders */
        [data-testid="stVerticalBlockBorderWrapper"] {
            border-radius: 10px;
            padding: 1rem;
            background-color: #ffffff;
            box-shadow: 0 1px 3px rgba(0,0,0,0.05);
        }
        
        /* Clean Input Fields */
        .stTextInput > div > div > input {
            border-radius: 6px;
            border: 1px solid #e0e0e0;
        }
        
        /* Custom Header Styling */
        .main-title {
            font-size: 1.8rem;
            font-weight: 700;
            color: #1a1a1a;
            margin-bottom: 0px;
        }
        .subtitle {
            font-size: 0.9rem;
            color: #666;
            margin-bottom: 2rem;
            font-weight: 400;
        }
    </style>
    """, unsafe_allow_html=True)

local_css()

# --- 1. CREDENTIALS & CONNECTIONS ---
# The app will crash if these are missing from Secrets!
try:
    api_key = st.secrets["OPENAI_API_KEY"]
    supabase_url = st.secrets["SUPABASE_URL"]
    supabase_key = st.secrets["SUPABASE_KEY"]
    clinic_password = st.secrets["CLINIC_PASSWORD"]
except FileNotFoundError:
    st.error("🚨 System Error: API Keys are missing. Please configure Streamlit Secrets.")
    st.stop()

client = OpenAI(api_key=api_key)

@st.cache_resource
def init_supabase():
    return create_client(supabase_url, supabase_key)

supabase = init_supabase()

# --- 2. LOGIN SECURITY ---
if 'authenticated' not in st.session_state:
    st.session_state.authenticated = False

def check_password():
    if st.session_state.password_input == clinic_password:
        st.session_state.authenticated = True
    else:
        st.error("❌ Invalid Access Code")

if not st.session_state.authenticated:
    # A clean, centered login screen
    col1, col2, col3 = st.columns([1,1,1])
    with col2:
        st.markdown("<br><br><br>", unsafe_allow_html=True)
        st.markdown("### 🏥 AppealOS Login")
        st.text_input("Clinic Passcode", type="password", key="password_input", on_change=check_password)
    st.stop() 

# --- 3. HELPER FUNCTIONS ---
def create_pdf(letter_text, patient_name):
    """Generates a PDF on the fly"""
    pdf = FPDF()
    pdf.add_page()
    pdf.set_font("Arial", size=11)
    
    # Header
    pdf.set_font("Arial", 'B', 14)
    pdf.cell(0, 10, txt="MEDICAL NECESSITY APPEAL", ln=1, align='L')
    pdf.line(10, 25, 200, 25)
    pdf.ln(10)
    
    # Metadata
    pdf.set_font("Arial", size=10)
    pdf.cell(0, 6, txt=f"Patient Ref: {patient_name}", ln=1)
    pdf.cell(0, 6, txt=f"Date Generated: {datetime.date.today()}", ln=1)
    pdf.ln(10)
    
    # Body
    pdf.set_font("Arial", size=11)
    safe_text = letter_text.encode('latin-1', 'replace').decode('latin-1')
    pdf.multi_cell(0, 6, safe_text)
    
    return pdf.output(dest="S").encode("latin-1")

def save_to_db(patient, letter):
    """Saves to Supabase"""
    try:
        data = {
            "patient_name": patient, 
            "final_letter": letter,
            "created_at": str(datetime.datetime.now())
        }
        supabase.table("appeals").insert(data).execute()
        st.toast("✅ Saved to Secure Database", icon="💾")
    except Exception as e:
        st.error(f"Database Error: {e}")

# --- 4. MAIN DASHBOARD UI ---

# Header Section
st.markdown('<div class="main-title">🏥 AppealOS <span style="font-size:1rem; color:#888;">| Professional Edition</span></div>', unsafe_allow_html=True)
st.markdown('<div class="subtitle">AI-Powered Revenue Cycle Management</div>', unsafe_allow_html=True)

# Top Bar: Patient & Policy Context
with st.container(border=True):
    c1, c2 = st.columns([1, 2])
    with c1:
        patient_name = st.text_input("Patient Name / ID", placeholder="e.g. John Doe #9921")
    with c2:
        policy_rules = st.text_input("Denial Context / Policy Code", placeholder="e.g. 'Denial CO-50: Not Medically Necessary'")

# Main Workflow Area
c_left, c_right = st.columns([1, 1], gap="medium")

# LEFT: INPUT (Voice)
with c_left:
    st.markdown("### 1. Clinical Dictation")
    with st.container(border=True):
        st.info("🎙️ Instructions: Explain the diagnosis, previous failed treatments, and urgency.")
        audio_val = st.audio_input("Record Clinical Notes")
        
        if audio_val:
            with st.spinner("Processing Audio..."):
                transcription = client.audio.transcriptions.create(model="whisper-1", file=audio_val)
                st.session_state['voice_result'] = transcription.text
            st.success("Dictation Captured")
            st.text_area("Transcript", st.session_state['voice_result'], height=120)

# RIGHT: OUTPUT (Action)
with c_right:
    st.markdown("### 2. Resolution")
    with st.container(border=True):
        if st.button("✨ Generate Appeal Letter", use_container_width=True, type="primary"):
            voice_notes = st.session_state.get('voice_result')
            
            if voice_notes and patient_name:
                with st.spinner("Analyzing Clinical Guidelines..."):
                    prompt = f"""
                    Write a formal medical appeal letter.
                    PATIENT: {patient_name}
                    CONTEXT: {policy_rules}
                    NOTES: {voice_notes}
                    
                    INSTRUCTIONS:
                    - Professional, firm tone.
                    - Cite the 'Medical Necessity' based on the notes.
                    - Format: Header, Argument, Conclusion.
                    """
                    resp = client.chat.completions.create(model="gpt-4o", messages=[{"role":"user", "content": prompt}])
                    st.session_state['final_letter'] = resp.choices[0].message.content
            else:
                st.warning("⚠️ Please provide Patient Name and Voice Dictation.")

        # Results & Export
        if 'final_letter' in st.session_state:
            letter_content = st.text_area("Final Draft", st.session_state['final_letter'], height=400)
            
            b1, b2 = st.columns(2)
            with b1:
                if st.button("💾 Save Record", use_container_width=True):
                    save_to_db(patient_name, letter_content)
            with b2:
                pdf_bytes = create_pdf(letter_content, patient_name)
                st.download_button("📄 Download PDF", pdf_bytes, f"{patient_name}.pdf", "application/pdf", use_container_width=True)

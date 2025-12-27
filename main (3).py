import streamlit as st
import os
import base64
from openai import OpenAI
from supabase import create_client, Client
from fpdf import FPDF
import datetime

# --- CONFIGURATION ---
st.set_page_config(page_title="Clinic AppealOS", layout="wide", page_icon="🏥")

# --- 1. SETUP CREDENTIALS ---
# These must be in your Streamlit Secrets!
try:
    api_key = st.secrets["OPENAI_API_KEY"]
    supabase_url = st.secrets["SUPABASE_URL"]
    supabase_key = st.secrets["SUPABASE_KEY"]
    clinic_password = st.secrets["CLINIC_PASSWORD"]
except FileNotFoundError:
    st.error("🚨 Critical Error: Secrets are missing! Please add API Keys to Streamlit Dashboard.")
    st.stop()

client = OpenAI(api_key=api_key)

# Initialize Supabase (Database)
@st.cache_resource
def init_supabase():
    return create_client(supabase_url, supabase_key)

supabase = init_supabase()

# --- 2. AUTHENTICATION (Login Screen) ---
if 'authenticated' not in st.session_state:
    st.session_state.authenticated = False

def check_password():
    if st.session_state.password_input == clinic_password:
        st.session_state.authenticated = True
    else:
        st.error("❌ Incorrect Access Code")

if not st.session_state.authenticated:
    st.markdown("<br><br><br>", unsafe_allow_html=True)
    st.markdown("<h1 style='text-align: center;'>🏥 Clinic AppealOS</h1>", unsafe_allow_html=True)
    st.markdown("<h3 style='text-align: center;'>Secure Staff Login</h3>", unsafe_allow_html=True)
    
    col1, col2, col3 = st.columns([1,1,1])
    with col2:
        st.text_input("Enter Clinic Access Code", type="password", key="password_input", on_change=check_password)
    st.stop() 

# --- 3. HELPER FUNCTIONS ---

def create_pdf(letter_text, patient_name):
    """Generates a professional PDF letterhead"""
    pdf = FPDF()
    pdf.add_page()
    pdf.set_font("Arial", size=11)
    
    # Simple Letterhead
    pdf.set_font("Arial", 'B', 14)
    pdf.cell(0, 10, txt="MEDICAL NECESSITY APPEAL", ln=1, align='C')
    pdf.ln(5)
    
    pdf.set_font("Arial", size=10)
    pdf.cell(0, 10, txt=f"Patient Reference: {patient_name}", ln=1)
    pdf.cell(0, 10, txt=f"Date: {datetime.date.today()}", ln=1)
    pdf.ln(10)
    
    # Body Content
    pdf.set_font("Arial", size=11)
    # Handle simple encoding to prevent crashes
    safe_text = letter_text.encode('latin-1', 'replace').decode('latin-1')
    pdf.multi_cell(0, 6, safe_text)
    
    return pdf.output(dest="S").encode("latin-1")

def save_to_db(patient, letter):
    """Saves the case to Supabase"""
    try:
        data = {
            "patient_name": patient, 
            "final_letter": letter,
            "created_at": str(datetime.datetime.now())
        }
        # Assuming you created a table named 'appeals'
        supabase.table("appeals").insert(data).execute()
        st.toast("✅ Case Saved to Database!", icon="💾")
    except Exception as e:
        st.error(f"Database Error: {e}")

# --- 4. THE MAIN APP INTERFACE ---

# Sidebar
with st.sidebar:
    st.title("👨‍⚕️ Dr. Dashboard")
    st.markdown("---")
    app_mode = st.radio("Navigation", ["New Appeal", "Patient Records"])
    st.markdown("---")
    st.caption("v2.0 | Voice & Policy Engine")

# MODE 1: NEW APPEAL
if app_mode == "New Appeal":
    st.title("🎙️ Voice-to-Appeal Engine")
    st.markdown("Dictate the clinical context. The AI will cross-reference your policy and write the letter.")
    
    # Patient Context
    col_pt, col_pol = st.columns(2)
    with col_pt:
        patient_name = st.text_input("Patient Name / ID", placeholder="e.g. Jane Doe #5521")
    with col_pol:
        policy_rules = st.text_area("Insurance Policy Rule (Optional)", height=40, 
                                  placeholder="Paste specific denial reason or policy rule here...")

    st.markdown("---")

    # TWO COLUMN WORKFLOW
    col1, col2 = st.columns([1, 1])

    # LEFT: The Voice Input
    with col1:
        st.header("1. Clinical Dictation")
        st.info("Describe the diagnosis, history, and why this treatment is urgent.")
        
        audio_val = st.audio_input("Record Notes", key="voice_recorder")
        
        if audio_val:
            with st.spinner("Transcribing your voice..."):
                transcription = client.audio.transcriptions.create(model="whisper-1", file=audio_val)
                st.session_state['voice_result'] = transcription.text
                st.success("Transcription Complete")
        
        # Show Transcription for review
        if 'voice_result' in st.session_state:
            st.text_area("Transcribed Notes:", st.session_state['voice_result'], height=200)

    # RIGHT: The Output
    with col2:
        st.header("2. Generated Appeal")
        
        if st.button("Generate Professional Appeal", type="primary"):
            voice_notes = st.session_state.get('voice_result')
            
            if voice_notes:
                with st.spinner("Analyzing Medical Necessity..."):
                    # GPT-4 Logic
                    prompt = f"""
                    You are an expert Insurance Appeals Specialist. Write a formal appeal letter.
                    
                    PATIENT: {patient_name}
                    CLINICAL DICTATION: "{voice_notes}"
                    INSURANCE POLICY CONTEXT: "{policy_rules if policy_rules else 'Standard Medical Necessity Guidelines'}"
                    
                    INSTRUCTIONS:
                    - Use a professional, firm tone.
                    - Argue why the denial is incorrect based on the clinical notes.
                    - Cite the policy rule if provided.
                    - Structure: Subject Line, Introduction, Clinical Argument, Policy Justification, Conclusion.
                    """
                    
                    response = client.chat.completions.create(
                        model="gpt-4o",
                        messages=[{"role": "user", "content": prompt}]
                    )
                    st.session_state['final_letter'] = response.choices[0].message.content
            else:
                st.error("⚠️ Please record a voice note first.")

        # Display Final Result
        if 'final_letter' in st.session_state:
            letter_content = st.text_area("Final Draft (Editable)", st.session_state['final_letter'], height=400)
            
            # Action Buttons
            b1, b2 = st.columns(2)
            with b1:
                if st.button("💾 Save to Records"):
                    save_to_db(patient_name, letter_content)
            with b2:
                pdf_bytes = create_pdf(letter_content, patient_name)
                st.download_button(
                    label="📄 Download PDF",
                    data=pdf_bytes,
                    file_name=f"Appeal_{patient_name}.pdf",
                    mime="application/pdf"
                )

# MODE 2: DATABASE VIEW
elif app_mode == "Patient Records":
    st.title("📂 Case History")
    
    try:
        # Fetch last 10 records
        response = supabase.table("appeals").select("*").order("created_at", desc=True).limit(10).execute()
        
        if response.data:
            for case in response.data:
                with st.expander(f"Patient: {case['patient_name']} - {case['created_at'][:10]}"):
                    st.markdown(f"**Final Letter:**")
                    st.text(case['final_letter'])
        else:
            st.info("No appeals saved yet.")
            
    except Exception as e:
        st.warning("Database not connected yet. Add SUPABASE keys to secrets to enable history.")

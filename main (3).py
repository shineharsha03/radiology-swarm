import streamlit as st
import os
from openai import OpenAI
from supabase import create_client
from fpdf import FPDF
from tavily import TavilyClient
import pdfplumber
import datetime

# --- CONFIGURATION ---
st.set_page_config(page_title="AppealOS", layout="wide", page_icon="🏥")

# --- CUSTOM CSS ---
def local_css():
    st.markdown("""
    <style>
        @import url('https://fonts.googleapis.com/css2?family=Inter:wght@400;600&display=swap');
        html, body, [class*="css"] { font-family: 'Inter', sans-serif; }
        div.stButton > button:first-child {
            background-color: #0066cc; color: white; border-radius: 6px; border: none;
            padding: 0.5rem 1rem; font-weight: 600;
        }
        div.stButton > button:first-child:hover { background-color: #0052a3; }
        .main-title { font-size: 1.8rem; font-weight: 700; color: #1a1a1a; margin-bottom: 0px; }
    </style>
    """, unsafe_allow_html=True)

local_css()

# --- 1. CREDENTIALS ---
try:
    api_key = st.secrets["OPENAI_API_KEY"]
    supabase_url = st.secrets.get("SUPABASE_URL", "")
    supabase_key = st.secrets.get("SUPABASE_KEY", "")
    clinic_password = st.secrets["CLINIC_PASSWORD"]
    tavily_key = st.secrets["TAVILY_API_KEY"]
except KeyError:
    st.error("🚨 Critical Error: Secrets are missing.")
    st.stop()

client = OpenAI(api_key=api_key)
tavily = TavilyClient(api_key=tavily_key)
try:
    supabase = create_client(supabase_url, supabase_key)
except:
    supabase = None

# --- 2. LOGIN SECURITY ---
if 'authenticated' not in st.session_state:
    st.session_state.authenticated = False

def check_password():
    if st.session_state.password_input == clinic_password:
        st.session_state.authenticated = True
    else:
        st.error("❌ Invalid Access Code")

if not st.session_state.authenticated:
    col1, col2, col3 = st.columns([1,1,1])
    with col2:
        st.markdown("<br><br><br>", unsafe_allow_html=True)
        st.markdown("### 🏥 AppealOS Login")
        st.text_input("Clinic Passcode", type="password", key="password_input", on_change=check_password)
    st.stop() 

# --- 3. INTELLIGENT AGENTS ---

def extract_from_pdf(uploaded_file):
    """Reads the PDF and asks AI to find the details."""
    try:
        # A. Read Text
        with pdfplumber.open(uploaded_file) as pdf:
            text = ""
            for page in pdf.pages:
                text += page.extract_text()
        
        # B. Analyze with AI
        prompt = f"""
        Analyze this medical denial letter. Extract the following 4 fields into a simple summary:
        1. Patient Name
        2. Insurance Company Name
        3. Procedure Name / Code being denied
        4. Denial Reason (The specific rule or code cited)
        
        DENIAL LETTER TEXT:
        {text[:4000]}
        """
        response = client.chat.completions.create(model="gpt-4o", messages=[{"role":"user", "content": prompt}])
        return response.choices[0].message.content
    except Exception as e:
        return f"Error reading PDF: {e}"

def research_policy(insurance_name, procedure_name):
    """Searches web for policies."""
    try:
        query = f"{insurance_name} clinical coverage policy for {procedure_name} medical necessity requirements 2024"
        response = tavily.search(query=query, search_depth="advanced", max_results=3)
        context = ""
        for result in response['results']:
            context += f"- {result['content']}\n"
        return context
    except:
        return "Search failed."

# --- 4. MAIN DASHBOARD UI ---

st.markdown('<div class="main-title">🏥 AppealOS <span style="font-size:1rem; color:#888;">| Enterprise</span></div>', unsafe_allow_html=True)

# SECTION A: UPLOAD (The New Feature)
with st.container(border=True):
    uploaded_file = st.file_uploader("📂 Upload Denial Letter (PDF)", type="pdf")
    
    if uploaded_file and 'pdf_analyzed' not in st.session_state:
        with st.spinner("🧠 AI is reading the denial letter..."):
            analysis = extract_from_pdf(uploaded_file)
            st.session_state['pdf_analysis'] = analysis
            st.session_state['pdf_analyzed'] = True
            st.success("✅ Extracted Details from PDF")

# SECTION B: CONFIRM DETAILS
with st.container(border=True):
    # If PDF was uploaded, show the analysis
    if 'pdf_analysis' in st.session_state:
        st.info("💡 **AI Extracted These Details:**")
        st.write(st.session_state['pdf_analysis'])
        st.markdown("---")

    c1, c2, c3 = st.columns(3)
    with c1:
        patient_name = st.text_input("Patient Name", placeholder="Start typing...")
    with c2:
        insurance_name = st.text_input("Insurance Carrier", placeholder="e.g. Aetna")
    with c3:
        procedure_name = st.text_input("Procedure / Denial", placeholder="e.g. Crown")

# SECTION C: WORKFLOW
c_left, c_right = st.columns([1, 1], gap="medium")

with c_left:
    st.markdown("### 1. Clinical Defense")
    st.info("🎙️ Explain why this treatment is medically necessary.")
    audio_val = st.audio_input("Record Dictation")
    
    if audio_val:
        with st.spinner("Transcribing..."):
            transcription = client.audio.transcriptions.create(model="whisper-1", file=audio_val)
            st.session_state['voice_result'] = transcription.text
        st.success("Captured")

with c_right:
    st.markdown("### 2. Resolution")
    if st.button("✨ Generate Appeal", type="primary", use_container_width=True):
        voice_notes = st.session_state.get('voice_result')
        
        if voice_notes and patient_name:
            # 1. RESEARCH
            with st.status("🕵️ Researching Guidelines...", expanded=True) as status:
                policy_context = research_policy(insurance_name, procedure_name)
                st.write(policy_context)
                status.update(label="✅ Policy Found!", state="complete", expanded=False)
            
            # 2. WRITE
            with st.spinner("Drafting Letter..."):
                prompt = f"""
                Write a medical appeal.
                PATIENT: {patient_name}
                INSURANCE: {insurance_name}
                PROCEDURE: {procedure_name}
                CLINICAL NOTES: {voice_notes}
                POLICY RULES FOUND: {policy_context}
                
                INSTRUCTIONS:
                - Professional tone.
                - Use the policy rules to justify the claim.
                """
                resp = client.chat.completions.create(model="gpt-4o", messages=[{"role":"user", "content": prompt}])
                st.session_state['final_letter'] = resp.choices[0].message.content
        else:
            st.warning("Please provide Patient Name and Dictation.")

    # DOWNLOAD & SAVE
    if 'final_letter' in st.session_state:
        letter_content = st.text_area("Final Draft", st.session_state['final_letter'], height=400)
        
        # Save to DB
        if st.button("💾 Save to Database", use_container_width=True):
            if supabase:
                supabase.table("appeals").insert({
                    "patient_name": patient_name, 
                    "final_letter": letter_content, 
                    "created_at": str(datetime.datetime.now())
                }).execute()
                st.toast("Saved!", icon="💾")

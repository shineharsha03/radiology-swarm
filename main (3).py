import streamlit as st
import os
from openai import OpenAI
from supabase import create_client
from fpdf import FPDF
from tavily import TavilyClient
import pdfplumber
from docx import Document
from io import BytesIO
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
    try:
        with pdfplumber.open(uploaded_file) as pdf:
            text = ""
            for page in pdf.pages:
                text += page.extract_text() or ""
        
        prompt = f"""
        Analyze this medical denial letter. Extract these 3 fields:
        1. Patient Name
        2. Insurance Company
        3. Denial Reason (The specific rule or code cited)
        
        TEXT: {text[:4000]}
        """
        response = client.chat.completions.create(model="gpt-4o", messages=[{"role":"user", "content": prompt}])
        return response.choices[0].message.content
    except Exception as e:
        return f"Error reading PDF: {e}"

def research_policy(insurance_name, procedure_name):
    try:
        query = f"{insurance_name} clinical coverage policy for {procedure_name} medical necessity requirements 2024"
        response = tavily.search(query=query, search_depth="advanced", max_results=3)
        context = ""
        for result in response['results']:
            context += f"- {result['content']}\n"
        return context
    except:
        return "Search failed."

# --- 4. FILE GENERATORS (SAFE MODE) ---
def create_pdf(text, patient):
    try:
        pdf = FPDF()
        pdf.add_page()
        pdf.set_font("Arial", size=11)
        # Fix special characters that crash PDF generation
        safe_text = text.encode('latin-1', 'replace').decode('latin-1')
        pdf.multi_cell(0, 6, safe_text)
        return pdf.output(dest="S").encode("latin-1")
    except Exception as e:
        return None

def create_docx(text, patient):
    try:
        doc = Document()
        doc.add_heading('Medical Necessity Appeal', 0)
        doc.add_paragraph(f"Patient Ref: {patient}")
        doc.add_paragraph(f"Date: {datetime.date.today()}")
        doc.add_paragraph("------------------------------------------------")
        # Split by newlines to keep formatting
        for para in text.split('\n'):
            doc.add_paragraph(para)
        
        buffer = BytesIO()
        doc.save(buffer)
        buffer.seek(0)
        return buffer
    except Exception as e:
        return None

# --- 5. MAIN UI ---

st.markdown('<div class="main-title">🏥 AppealOS <span style="font-size:1rem; color:#888;">| Enterprise</span></div>', unsafe_allow_html=True)

# SECTION A: UPLOAD
with st.container(border=True):
    uploaded_file = st.file_uploader("📂 Upload Denial Letter (PDF)", type="pdf")
    if uploaded_file and 'pdf_analyzed' not in st.session_state:
        with st.spinner("🧠 AI is reading the denial letter..."):
            analysis = extract_from_pdf(uploaded_file)
            st.session_state['pdf_analysis'] = analysis
            st.session_state['pdf_analyzed'] = True
            st.success("✅ Extracted Details")

# SECTION B: INPUTS
with st.container(border=True):
    if 'pdf_analysis' in st.session_state:
        st.info(f"AI Found: {st.session_state['pdf_analysis']}")

    c1, c2, c3 = st.columns(3)
    with c1: patient_name = st.text_input("Patient Name", value="John Doe")
    with c2: insurance_name = st.text_input("Insurance Carrier")
    with c3: procedure_name = st.text_input("Procedure / Denial")

# SECTION C: WORKFLOW
c_left, c_right = st.columns([1, 1], gap="medium")

with c_left:
    st.markdown("### 1. Clinical Defense")
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
            # Research
            with st.status("🕵️ Researching Guidelines...", expanded=True) as status:
                policy_context = research_policy(insurance_name, procedure_name)
                st.write(policy_context)
                status.update(label="✅ Policy Found!", state="complete", expanded=False)
            
            # Write
            with st.spinner("Drafting Letter..."):
                prompt = f"""
                Write a formal appeal letter.
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
            st.warning("Missing Data.")

    # SECTION D: DOWNLOADS (DEBUGGED)
    if 'final_letter' in st.session_state:
        letter_content = st.text_area("Final Draft", st.session_state['final_letter'], height=400)
        
        # We generate the files OUTSIDE the columns first to check for errors
        pdf_bytes = create_pdf(letter_content, patient_name)
        docx_file = create_docx(letter_content, patient_name)
        
        b1, b2, b3 = st.columns(3)
        
        with b1:
            if st.button("💾 Save to Database", use_container_width=True):
                if supabase:
                    supabase.table("appeals").insert({
                        "patient_name": patient_name, 
                        "final_letter": letter_content, 
                        "created_at": str(datetime.datetime.now())
                    }).execute()
                    st.toast("Saved!", icon="💾")
        
        with b2:
            if pdf_bytes:
                st.download_button("📄 Download PDF", pdf_bytes, f"{patient_name}.pdf", "application/pdf", use_container_width=True)
            else:
                st.error("PDF Failed")
            
        with b3:
            if docx_file:
                st.download_button("📝 Download Word", docx_file, f"{patient_name}.docx", "application/vnd.openxmlformats-officedocument.wordprocessingml.document", use_container_width=True)
            else:
                st.error("Word Failed")

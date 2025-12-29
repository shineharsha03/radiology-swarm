import streamlit as st
import os
from openai import OpenAI
from fpdf import FPDF
import pdfplumber
from docx import Document
from io import BytesIO
import datetime

# --- CONFIGURATION & PAGE SETUP ---
st.set_page_config(
    page_title="AppealOS | AI Revenue Cycle Manager", 
    layout="wide", 
    page_icon="🏥",
    initial_sidebar_state="expanded"
)

# --- CUSTOM CSS (PROFESSIONAL THEME) ---
def local_css():
    st.markdown("""
    <style>
        @import url('https://fonts.googleapis.com/css2?family=Inter:wght@400;600&display=swap');
        html, body, [class*="css"] { font-family: 'Inter', sans-serif; }
        
        /* Clean Headers */
        h1, h2, h3 { color: #0f172a; }
        
        /* Primary Button Style */
        div.stButton > button:first-child {
            background-color: #2563eb; 
            color: white; 
            border-radius: 8px; 
            border: none;
            padding: 0.6rem 1.2rem; 
            font-weight: 600;
            box-shadow: 0 4px 6px -1px rgba(0, 0, 0, 0.1);
        }
        div.stButton > button:first-child:hover { background-color: #1d4ed8; }
        
        /* Cards/Containers */
        [data-testid="stVerticalBlockBorderWrapper"] {
            border-radius: 12px; 
            padding: 1.5rem; 
            background-color: #ffffff;
            border: 1px solid #e2e8f0;
            box-shadow: 0 1px 3px rgba(0,0,0,0.05);
        }
    </style>
    """, unsafe_allow_html=True)

local_css()

# --- 1. CREDENTIALS & CONNECTIONS ---
try:
    api_key = st.secrets["OPENAI_API_KEY"]
    supabase_url = st.secrets.get("SUPABASE_URL", "")
    supabase_key = st.secrets.get("SUPABASE_KEY", "")
    clinic_password = st.secrets["CLINIC_PASSWORD"]
    tavily_key = st.secrets["TAVILY_API_KEY"]
except KeyError:
    st.error("🚨 System Error: API Keys are missing. Please check settings.")
    st.stop()

client = OpenAI(api_key=api_key)

# Connect to Tavily
from tavily import TavilyClient
tavily = TavilyClient(api_key=tavily_key)

# Connect to Supabase
try:
    from supabase import create_client
    supabase = create_client(supabase_url, supabase_key)
except:
    supabase = None

# --- 2. SIDEBAR & LOGOUT ---
with st.sidebar:
    st.markdown("## 🏥 AppealOS")
    st.caption("AI-Powered Denial Management")
    st.markdown("---")
    st.markdown("**User:** Dr. Admin")
    st.markdown("**Clinic:** Downtown Medical")
    st.markdown("---")
    st.info("System Status: 🟢 Online")
    if st.button("Log Out"):
        st.session_state.authenticated = False
        st.rerun()

# --- 3. LOGIN SECURITY ---
if 'authenticated' not in st.session_state:
    st.session_state.authenticated = False

def check_password():
    if st.session_state.password_input == clinic_password:
        st.session_state.authenticated = True
    else:
        st.error("❌ Access Denied")

if not st.session_state.authenticated:
    st.markdown("<br><br>", unsafe_allow_html=True)
    c1, c2, c3 = st.columns([1,1,1])
    with c2:
        st.markdown("### 🔒 Secure Login")
        st.text_input("Enter Clinic Passcode", type="password", key="password_input", on_change=check_password)
    st.stop() 

# --- 4. CORE AI FUNCTIONS ---
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
        return "Manual Policy Search Required."

# --- 5. FILE GENERATORS ---
def create_pdf(text, patient):
    pdf = FPDF()
    pdf.add_page()
    pdf.set_font("Arial", size=11)
    safe_text = text.encode('latin-1', 'replace').decode('latin-1')
    pdf.multi_cell(0, 6, safe_text)
    return pdf.output(dest="S").encode("latin-1")

def create_docx(text, patient):
    doc = Document()
    doc.add_heading('Medical Necessity Appeal', 0)
    doc.add_paragraph(f"Patient Ref: {patient}")
    doc.add_paragraph(f"Date: {datetime.date.today()}")
    doc.add_paragraph("---")
    for para in text.split('\n'):
        doc.add_paragraph(para)
    buffer = BytesIO()
    doc.save(buffer)
    buffer.seek(0)
    return buffer

# --- 6. MAIN DASHBOARD ---

st.title("AppealOS Dashboard")
st.markdown("Create data-driven appeal letters in seconds.")

# SECTION A: UPLOAD
with st.container():
    uploaded_file = st.file_uploader("📂 Drag & Drop Denial Letter (PDF)", type="pdf")
    if uploaded_file and 'pdf_analyzed' not in st.session_state:
        with st.spinner("🧠 AI is scanning document..."):
            analysis = extract_from_pdf(uploaded_file)
            st.session_state['pdf_analysis'] = analysis
            st.session_state['pdf_analyzed'] = True
            st.success("Analysis Complete")

# SECTION B: CASE DETAILS
with st.expander("📝 Case Details", expanded=True):
    if 'pdf_analysis' in st.session_state:
        st.info(f"**AI Findings:** {st.session_state['pdf_analysis']}")
    
    c1, c2, c3 = st.columns(3)
    with c1: patient_name = st.text_input("Patient Name", value="John Doe")
    with c2: insurance_name = st.text_input("Insurance Carrier", placeholder="e.g. Aetna")
    with c3: procedure_name = st.text_input("Procedure / Denial", placeholder="e.g. Crown")

# SECTION C: WORKFLOW
c_left, c_right = st.columns([1, 1], gap="large")

with c_left:
    st.subheader("1. Clinical Defense")
    st.info("🎙️ **Doctor's Note:** Explain why this treatment is necessary.")
    audio_val = st.audio_input("Record Dictation")
    if audio_val:
        with st.spinner("Transcribing..."):
            transcription = client.audio.transcriptions.create(model="whisper-1", file=audio_val)
            st.session_state['voice_result'] = transcription.text
        st.success("Dictation Saved")

with c_right:
    st.subheader("2. Resolution")
    st.write("AI will research policy guidelines and draft the legal argument.")
    
    if st.button("✨ Generate Appeal Package", type="primary", use_container_width=True):
        voice_notes = st.session_state.get('voice_result')
        
        if voice_notes and patient_name:
            # 1. Research
            with st.status("🕵️ Agent is researching policies...", expanded=True) as status:
                policy_context = research_policy(insurance_name, procedure_name)
                st.write(policy_context)
                status.update(label="✅ Policies Retrieved", state="complete", expanded=False)
            
            # 2. Write
            with st.spinner("Drafting legal arguments..."):
                prompt = f"""
                Write a formal appeal letter.
                PATIENT: {patient_name}
                INSURANCE: {insurance_name}
                PROCEDURE: {procedure_name}
                CLINICAL NOTES: {voice_notes}
                POLICY RULES FOUND: {policy_context}
                INSTRUCTIONS: Professional tone. CITE the policy rules found.
                """
                resp = client.chat.completions.create(model="gpt-4o", messages=[{"role":"user", "content": prompt}])
                st.session_state['final_letter'] = resp.choices[0].message.content
        else:
            st.warning("⚠️ Please record a voice note first.")

    # DOWNLOAD SECTION
    if 'final_letter' in st.session_state:
        st.markdown("---")
        st.subheader("3. Export")
        letter_content = st.text_area("Final Draft", st.session_state['final_letter'], height=400)
        
        # Prepare Files
        try:
            pdf_bytes = create_pdf(letter_content, patient_name)
            docx_file = create_docx(letter_content, patient_name)
            files_ready = True
        except:
            st.error("File generation error.")
            files_ready = False

        col_a, col_b, col_c = st.columns(3)
        
        with col_a:
            if st.button("💾 Save to Record", use_container_width=True):
                if supabase:
                    supabase.table("appeals").insert({
                        "patient_name": patient_name, 
                        "final_letter": letter_content, 
                        "created_at": str(datetime.datetime.now())
                    }).execute()
                    st.toast("Record Saved", icon="💾")

        if files_ready:
            with col_b:
                st.download_button("📄 Download PDF", pdf_bytes, f"{patient_name}.pdf", "application/pdf", use_container_width=True)
            with col_c:
                st.download_button("📝 Download Word", docx_file, f"{patient_name}.docx", "application/vnd.openxmlformats-officedocument.wordprocessingml.document", use_container_width=True)

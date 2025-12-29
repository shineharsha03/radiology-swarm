import streamlit as st
import os
from openai import OpenAI
from supabase import create_client
from fpdf import FPDF
from tavily import TavilyClient
import datetime

# --- CONFIGURATION ---
st.set_page_config(page_title="AppealOS", layout="wide", page_icon="🏥")

# --- CUSTOM CSS ---
def local_css():
    st.markdown("""
    <style>
        @import url('https://fonts.googleapis.com/css2?family=Inter:wght@400;600&display=swap');
        html, body, [class*="css"] { font-family: 'Inter', sans-serif; }
        header {visibility: hidden;}
        div.stButton > button:first-child {
            background-color: #0066cc; color: white; border-radius: 6px; border: none;
            padding: 0.5rem 1rem; font-weight: 600;
        }
        div.stButton > button:first-child:hover { background-color: #0052a3; }
        [data-testid="stVerticalBlockBorderWrapper"] {
            border-radius: 10px; padding: 1rem; background-color: #ffffff;
            box-shadow: 0 1px 3px rgba(0,0,0,0.05);
        }
        .main-title { font-size: 1.8rem; font-weight: 700; color: #1a1a1a; margin-bottom: 0px; }
        .subtitle { font-size: 0.9rem; color: #666; margin-bottom: 2rem; }
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
    st.error("🚨 Critical Error: Secrets are missing (Check TAVILY_API_KEY).")
    st.stop()

client = OpenAI(api_key=api_key)

# Initialize Clients
try:
    supabase = create_client(supabase_url, supabase_key)
except:
    supabase = None

tavily = TavilyClient(api_key=tavily_key)

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

# --- 3. THE RESEARCH AGENT ---
def research_policy(insurance_name, procedure_name):
    """Searches the web for coverage policies"""
    try:
        query = f"{insurance_name} clinical coverage policy for {procedure_name} medical necessity requirements 2024"
        response = tavily.search(query=query, search_depth="advanced", max_results=3)
        
        context_text = ""
        for result in response['results']:
            context_text += f"- SOURCE: {result['title']}\n  CONTENT: {result['content']}\n\n"
            
        return context_text
    except Exception as e:
        return f"Error searching web: {e}"

# --- 4. HELPER FUNCTIONS ---
def create_pdf(letter_text, patient_name):
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
    if not supabase: return
    try:
        data = { "patient_name": patient, "final_letter": letter, "created_at": str(datetime.datetime.now()) }
        supabase.table("appeals").insert(data).execute()
        st.toast("✅ Saved to Secure Database", icon="💾")
    except Exception as e:
        st.error(f"Database Error: {e}")

# --- 5. MAIN DASHBOARD UI ---

st.markdown('<div class="main-title">🏥 AppealOS <span style="font-size:1rem; color:#888;">| Research Edition</span></div>', unsafe_allow_html=True)

# Top Bar
with st.container(border=True):
    c1, c2, c3 = st.columns([1, 1, 2])
    with c1:
        patient_name = st.text_input("Patient Name", placeholder="e.g. Jane Doe")
    with c2:
        insurance_name = st.text_input("Insurance Carrier", placeholder="e.g. Aetna")
    with c3:
        procedure_name = st.text_input("Procedure / Denial", placeholder="e.g. Crown")

# Main Workflow
c_left, c_right = st.columns([1, 1], gap="medium")

# LEFT: INPUT
with c_left:
    st.markdown("### 1. Clinical Context")
    with st.container(border=True):
        st.info("🎙️ **Doctor's Notes:** Explain why the patient needs this treatment.")
        audio_val = st.audio_input("Record Dictation")
        
        if audio_val:
            with st.spinner("Processing Audio..."):
                transcription = client.audio.transcriptions.create(model="whisper-1", file=audio_val)
                st.session_state['voice_result'] = transcription.text
            st.success("Dictation Captured")
            st.text_area("Transcript", st.session_state['voice_result'], height=100)

# RIGHT: OUTPUT
with c_right:
    st.markdown("### 2. Research & Resolution")
    with st.container(border=True):
        
        enable_research = st.checkbox("🕵️ Auto-Find Insurance Policy Rule", value=True)
        
        if st.button("✨ Generate Appeal", use_container_width=True, type="primary"):
            voice_notes = st.session_state.get('voice_result')
            
            if voice_notes and patient_name:
                
                # --- STEP A: THE RESEARCHER (DEBUG MODE) ---
                policy_context = "Standard Medical Necessity Guidelines"
                
                if enable_research and insurance_name and procedure_name:
                    with st.status("🕵️ Researching Insurance Policies...", expanded=True) as status:
                        st.write(f"Searching web for: {insurance_name} + {procedure_name}")
                        try:
                            policy_context = research_policy(insurance_name, procedure_name)
                            
                            # DEBUGGING: SHOW THE RAW DATA
                            st.info("Evidence Found:")
                            st.text_area("RAW RESEARCH DATA", policy_context, height=150)
                            
                            status.update(label="✅ Policy Found!", state="complete", expanded=False)
                        except Exception as e:
                            st.error(f"Search Failed: {e}")
                            status.update(label="❌ Search Failed", state="error")
                
                # --- STEP B: THE WRITER ---
                with st.spinner("Drafting Appeal Letter..."):
                    prompt = f"""
                    Write a formal appeal letter.
                    PATIENT: {patient_name}
                    INSURANCE: {insurance_name}
                    PROCEDURE: {procedure_name}
                    CLINICAL NOTES: {voice_notes}
                    
                    FOUND POLICY RULES (Use this to justify the appeal): 
                    {policy_context}
                    
                    INSTRUCTIONS:
                    - Be professional and firm.
                    - Explicitly quote the policy rules found in the 'RAW RESEARCH DATA' to argue for coverage.
                    """
                    resp = client.chat.completions.create(model="gpt-4o", messages=[{"role":"user", "content": prompt}])
                    st.session_state['final_letter'] = resp.choices[0].message.content
            else:
                st.warning("⚠️ Please provide Patient Name and Dictation.")

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

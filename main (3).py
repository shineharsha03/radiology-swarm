import streamlit as st
import os
import base64
from openai import OpenAI

# --- CONFIGURATION ---
st.set_page_config(page_title="Real AI Swarm", layout="wide")

# 1. GET THE API KEY
# This looks for the key in Streamlit Secrets (or Replit Secrets)
api_key = os.environ.get("OPENAI_API_KEY")

if not api_key:
    st.error("🚨 STOP: OpenAI API Key is missing! Go to Streamlit Settings -> Secrets and add it.")
    st.stop()

client = OpenAI(api_key=api_key)

st.title("🐝 Medical Appeal Swarm (LIVE AI)")
st.markdown("### The Digital Insurance Defense Employee")

# --- HELPER: ENCODE IMAGE FOR GPT-4 ---
def encode_image(uploaded_file):
    """Turns the image file into a text format GPT-4 can read."""
    return base64.b64encode(uploaded_file.getvalue()).decode("utf-8")

# --- 2. REAL AI AGENTS ---

def radiologist_agent(uploaded_file):
    """Agent 1: Uses GPT-4o Vision to ACTUALLY analyze the X-Ray."""
    base64_image = encode_image(uploaded_file)

    response = client.chat.completions.create(
        model="gpt-4o",
        messages=[
            {
                "role": "user",
                "content": [
                    {"type": "text", "text": "You are an expert Dentist/Radiologist. Analyze this dental image. Describe the pathology (cavities, bone loss, fractures) specifically to support an insurance claim. Be concise."},
                    {"type": "image_url", "image_url": {"url": f"data:image/jpeg;base64,{base64_image}"}}
                ]
            }
        ],
        max_tokens=300
    )
    return response.choices[0].message.content

def intake_agent(audio_file):
    """Agent 2: Uses Whisper to ACTUALLY transcribe your voice."""
    # Whisper reads the audio file directly
    transcription = client.audio.transcriptions.create(
        model="whisper-1",
        file=audio_file
    )
    return transcription.text

def writer_agent(radiology_report, voice_notes, policy_rules):
    """Agent 3: GPT-4o writes the specific letter using the Policy + Evidence."""

    # Use generic text if user left the policy box blank
    policy_text = policy_rules if policy_rules else "Standard Medical Necessity Guidelines"

    prompt = f"""
    You are an expert Medical Insurance Appeals Specialist. Write a formal appeal letter to an insurance company.

    1. THE INSURANCE POLICY RULE TO CITE:
    "{policy_text}"

    2. THE RADIOLOGY EVIDENCE:
    {radiology_report}

    3. THE DOCTOR'S NOTES:
    {voice_notes}

    INSTRUCTIONS:
    - Write a persuasive, professional appeal letter.
    - Explicitly argue that the patient's condition meets the Policy Rule.
    - Use the specific details from the Radiology Report.
    - Keep the tone firm but polite.
    """

    response = client.chat.completions.create(
        model="gpt-4o",
        messages=[{"role": "user", "content": prompt}]
    )
    return response.choices[0].message.content

# --- 3. THE DASHBOARD ---

col1, col2, col3 = st.columns(3)

# COLUMN 1: RADIOLOGIST
with col1:
    st.header("👁️ Radiologist")
    uploaded_file = st.file_uploader("Upload X-Ray", type=['png', 'jpg', 'jpeg'], key="rad")

    if uploaded_file and st.button("Analyze Image"):
        with st.spinner("Sending to GPT-4 Vision..."):
            try:
                st.session_state['rad_result'] = radiologist_agent(uploaded_file)
                st.success("Analysis Complete")
            except Exception as e:
                st.error(f"Error: {e}")

    if 'rad_result' in st.session_state:
        st.info(st.session_state['rad_result'])

# COLUMN 2: INTAKE NURSE
with col2:
    st.header("👂 Intake Nurse")
    audio_val = st.audio_input("Record Clinical Note", key="voice")

    if audio_val:
        with st.spinner("Sending to Whisper AI..."):
            try:
                st.session_state['voice_result'] = intake_agent(audio_val)
                st.success("Transcribed")
            except Exception as e:
                st.error(f"Error: {e}")

    if 'voice_result' in st.session_state:
        st.info(f"Dictation: '{st.session_state['voice_result']}'")

# COLUMN 3: CASE MANAGER
with col3:
    st.header("🧠 Case Manager")

    # The Researcher Slot
    st.markdown("**🛡️ Insurance Policy Rule**")
    policy_input = st.text_area("Paste Insurance Rule (Optional)", 
        placeholder="Paste the specific policy text here to strengthen the letter...")

    st.markdown("---")

    if st.button("Generate Appeal Letter", type="primary"):
        rad = st.session_state.get('rad_result')
        voice = st.session_state.get('voice_result')

        if rad and voice:
            with st.spinner("Drafting Legal Argument..."):
                final_letter = writer_agent(rad, voice, policy_input)
                st.text_area("Final Appeal Letter", final_letter, height=600)
        else:
            st.warning("⚠️ Please finish the X-Ray analysis and Voice recording first.")
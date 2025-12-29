import streamlit as st
from supabase import create_client

st.title("🚑 Database Connection Doctor")

# 1. READ SECRETS
url = st.secrets.get("SUPABASE_URL", "")
key = st.secrets.get("SUPABASE_KEY", "")

# 2. CHECK FORMAT
st.write(f"**URL Checked:** `{url}`")
if "supabase.com/dashboard" in url:
    st.error("❌ ERROR: You are using the Dashboard Link! Use the Project URL from Settings > API.")
elif "postgres://" in url:
    st.error("❌ ERROR: You are using the Postgres Connection string! Use the URL starting with 'https'.")
elif " " in url:
    st.error("❌ ERROR: You have a hidden space in your URL. Check your secrets.")
else:
    st.success("✅ URL Format looks correct.")

# 3. TEST CONNECTION
if st.button("Test Connection Now"):
    try:
        supabase = create_client(url, key)
        # Try to insert a dummy row
        data = {"patient_name": "Test Connection", "final_letter": "System Check"}
        response = supabase.table("appeals").insert(data).execute()
        st.success("🎉 SUCCESS! Connected and Saved to Database.")
        st.write(response)
    except Exception as e:
        st.error(f"Still Failing. Raw Error below:")
        st.code(str(e))

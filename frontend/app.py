import streamlit as st

st.set_page_config(
    page_title="Automated OMR System",
    page_icon="📝",
    layout="wide"
)

if "token" not in st.session_state:
    st.session_state.token = None

st.title("📊 Automated OMR Evaluation System")
st.markdown("Welcome! Use the sidebar to navigate between different sections:")

if st.session_state.token:
    st.sidebar.success("✅ Logged in")
    if st.sidebar.button("Logout"):
        st.session_state.token = None
else:
    st.sidebar.warning("🔒 Please login first (go to Login Page)")

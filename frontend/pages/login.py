import streamlit as st
from utils.api_client import login

st.set_page_config(page_title="Login", page_icon="🔑")

st.header("🔑 Login")

username = st.text_input("Username")
password = st.text_input("Password", type="password")

if st.button("Login"):
    with st.spinner("Authenticating..."):
        response = login(username, password)
        if "access_token" in response:
            st.session_state.token = response["access_token"]
            st.success("✅ Login successful!")
        else:
            st.error("❌ Invalid credentials")

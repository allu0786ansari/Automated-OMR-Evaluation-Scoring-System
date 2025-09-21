import streamlit as st
from utils.api_client import upload_sheet

st.set_page_config(page_title="Upload OMR Sheets", page_icon="📤")

st.header("📤 Upload OMR Sheets")

exam_id = st.number_input("Enter Exam ID", min_value=1, step=1)
set_no = st.text_input("Enter Set No (e.g., A or B)")

uploaded_file = st.file_uploader("Upload Scanned OMR Sheet", type=["jpg", "jpeg", "png"])

if uploaded_file and st.button("Upload & Process"):
    with st.spinner("Processing OMR sheet..."):
        result = upload_sheet(uploaded_file, exam_id, set_no)
        st.success("✅ Processing complete!")
        st.json(result)

import streamlit as st
from utils.api_client import export_results

st.set_page_config(page_title="Export Reports", page_icon="📑")

st.header("📑 Export Reports")

exam_id = st.number_input("Enter Exam ID", min_value=1, step=1)
format_choice = st.selectbox("Select Export Format", ["excel", "csv"])

if st.button("Export"):
    with st.spinner("Generating report..."):
        response = export_results(exam_id, format_choice)
        if response.status_code == 200:
            filename = f"exam_{exam_id}_results.{format_choice}"
            with open(filename, "wb") as f:
                f.write(response.content)
            st.success(f"✅ Report exported: {filename}")
            st.download_button("Download Report", response.content, file_name=filename)
        else:
            st.error("❌ Failed to export report.")

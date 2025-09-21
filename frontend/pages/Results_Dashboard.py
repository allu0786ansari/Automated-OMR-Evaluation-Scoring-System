import streamlit as st
import pandas as pd
from utils.api_client import get_results

st.set_page_config(page_title="Results Dashboard", page_icon="📊")

st.header("📊 Results Dashboard")

exam_id = st.number_input("Enter Exam ID", min_value=1, step=1)

if st.button("Fetch Results"):
    with st.spinner("Fetching results..."):
        results = get_results(exam_id)
        if results and "students" in results:
            df = pd.DataFrame(results["students"])
            st.dataframe(df, use_container_width=True)

            st.subheader("📈 Performance Summary")
            st.metric("Total Students", len(df))
            st.metric("Average Score", df["score"].mean())
        else:
            st.warning("No results found for this exam.")

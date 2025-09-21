import streamlit as st
import pandas as pd
from utils.api_client import get_flagged

st.set_page_config(page_title="Review Flagged Sheets", page_icon="⚠️")

st.header("⚠️ Review Flagged Sheets")

exam_id = st.number_input("Enter Exam ID", min_value=1, step=1)

if st.button("Fetch Flagged"):
    flagged = get_flagged(exam_id)
    if flagged and "flagged_students" in flagged:
        df = pd.DataFrame(flagged["flagged_students"])
        st.dataframe(df, use_container_width=True)

        st.info("Manually review these sheets and correct ambiguous cases.")
    else:
        st.success("🎉 No flagged sheets found for this exam.")

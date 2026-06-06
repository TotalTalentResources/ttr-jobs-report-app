import streamlit as st
from jobs_engine import generate_report
st.markdown("""
    <style>
    div.stButton > button {
        background-color: #007CA9;
        color: white;
        font-weight: bold;
        border-radius: 10px;
        height: 3.5em;
        font-size: 18px;
    }
    div.stButton > button:hover {
        background-color: #162a68;
        color: white;
    }
    </style>
""", unsafe_allow_html=True)

st.set_page_config(page_title="Jobs Report Generator", layout="wide")

# ✅ Sidebar (inputs)
with st.sidebar:
    st.header("Inputs")

    industry = st.selectbox(
        "Client Industry",
        ["Distribution", "Manufacturing", "Logistics"]
    )

    expected_jobs_k = st.number_input(
        "Expected Jobs (in thousands) REQUIRED",
        min_value=0,
        max_value=500,
        value=0,
        step=5
    )

    generate = st.button("Generate Report", use_container_width=True)
    if st.button("Clear and Start Over"):
        st.rerun()

# ✅ Main page (output)

col1, col2 = st.columns([1, 6])

with col1:
    st.image("TTR_Logo_Icon.png", width=140)

with col2:
    st.markdown("<h1 style='margin-bottom: 0;'>TTR Jobs Report Insights</h1>", unsafe_allow_html=True)
    st.caption("Generate client-ready economic insights in seconds")


# Only run when button clicked
if generate:

    if expected_jobs_k == 0:
        st.warning("⚠️ Please enter an expected jobs value before generating the report.")
    else:
        with st.spinner("Analyzing labor market data..."):
            report = generate_report(industry, expected_jobs_k)

        st.subheader("Generated Client Email")
        st.divider()

        st.markdown(report)

        st.success("✅ Report generated — ready to copy")
        st.caption("Highlight and copy the email above to paste into Outlook or the CRM")

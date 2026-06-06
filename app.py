import streamlit as st
import datetime
from jobs_engine import generate_report

# ✅ Initialize session state
if "report_month" not in st.session_state:
    st.session_state.report_month = None

st.set_page_config(page_title="Jobs Report Generator", layout="wide")

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

    if st.button("Clear and Start Over", use_container_width=True):
        st.session_state.clear()
        st.rerun()


# ✅ ✅ STEP 1 — HANDLE GENERATE FIRST (THIS IS THE KEY)
report = None

if generate:

    if expected_jobs_k == 0:
        st.warning("⚠️ Please enter an expected jobs value before generating the report.")

    else:
        with st.spinner("Analyzing labor market data..."):

            report, payroll_date = generate_report(industry, expected_jobs_k)

            # Convert BLS date
            if payroll_date:
                try:
                    year = payroll_date.split("-")[0]
                    month = payroll_date.split("-")[1].replace("M", "")
                    report_month = datetime.datetime(int(year), int(month), 1).strftime("%B %Y")
                except:
                    report_month = "Latest Release"
            else:
                report_month = "Latest Release"

            st.session_state.report_month = report_month


# ✅ ✅ STEP 2 — NOW RENDER HEADER (NOW IT CAN SEE THE VALUE)
col1, col2 = st.columns([1, 6])

with col1:
    st.image("TTR_Logo_Icon.png", width=140)

with col2:
    st.markdown("<h1 style='margin-bottom: 0;'>TTR Jobs Report Insights</h1>", unsafe_allow_html=True)
    st.caption("Generate client-ready economic insights in seconds")

    if st.session_state.report_month:
        st.caption(f"📊 Jobs Report: {st.session_state.report_month}")


# ✅ ✅ STEP 3 — OUTPUT (ONLY IF REPORT EXISTS)
if report:

    st.subheader("Generated Client Email")
    st.divider()

    st.markdown(report)

    st.success("✅ Report generated — ready to copy")
    st.caption("Highlight and copy the email above to paste into Outlook or the CRM")

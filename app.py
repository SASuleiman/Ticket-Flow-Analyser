import streamlit as st
import pandas as pd

# Set up the page
st.set_page_config(page_title="Ticket SLA Analyzer", layout="wide")
st.title("Ticket SLA Analyzer Dashboard")

# 1. Quick Explanation
st.markdown("""
**What this tool does:** It analyzes your Jira ticket history to determine how many tickets met or breached your Service Level Agreement (SLA).
""")

with st.expander("Need help exporting your CSV from Jira?"):
    st.markdown("""
    1. Go to your Jira board or the **Issues** search page.
    2. Filter to find the tickets you want to analyze.
    3. Click the **Export** icon (usually at the top right).
    4. Select **Export Excel CSV (all fields)**. 
    5. Upload that downloaded file below.
    """)

st.divider()

# Sidebar Setup for SLA and Filters
st.sidebar.header("⚙️ Settings & Filters")
sla_hours = st.sidebar.number_input(
    "1. Set SLA limit (Hours):", 
    min_value=1.0, value=24.0, step=1.0
)

# Main Area Upload
st.subheader("1. Upload Ticket Data")
has_multiple = st.radio("Do you have more than one CSV sheet to upload?", ["No, just one", "Yes, multiple"], horizontal=True)

allowed_files = 1
if has_multiple == "Yes, multiple":
    allowed_files = st.number_input("How many sheets? (Max 4)", min_value=2, max_value=4, value=2)

uploaded_files = st.file_uploader(f"Upload CSV file(s)", type=['csv'], accept_multiple_files=True)

# Exemptions Input
st.subheader("2. Exemptions (Optional)")
exemption_df = pd.DataFrame(columns=["Ticket Key", "Reason for Exemption"])
edited_exemptions = st.data_editor(exemption_df, num_rows="dynamic", use_container_width=True)
exempt_keys = [str(k).strip() for k in edited_exemptions["Ticket Key"].dropna().tolist() if str(k).strip()]

st.divider()

if uploaded_files:
    if len(uploaded_files) > allowed_files:
        st.warning(f"Only processing the first {allowed_files} files.")
        uploaded_files = uploaded_files[:allowed_files]
        
    try:
        # Load and combine all uploaded data
        dfs = [pd.read_csv(file) for file in uploaded_files]
        df = pd.concat(dfs, ignore_index=True)
        
        # Apply date fix and parse
        df['Date of change'] = pd.to_datetime(df['Date of change'].str.replace('Sept', 'Sep'), format='mixed', dayfirst=True)
        
        # Calculate durations and gather extra ticket info for filtering/export
        ticket_times = df.groupby('Key')['Date of change'].agg(['min', 'max'])
        ticket_times['Duration (Hours)'] = (ticket_times['max'] - ticket_times['min']).dt.total_seconds() / 3600
import streamlit as st
import pandas as pd

# Set up the page
st.set_page_config(page_title="Ticket SLA Analyzer", layout="wide")
st.title("Ticket SLA Analyzer")

# 1. Quick Explanation & Example
st.markdown("""
**What this tool does:** It analyzes your Jira ticket history to determine how many tickets met or breached your Service Level Agreement (SLA).

**Example:** If a ticket was moved to *"In Development"* on Monday at 9:00 AM, and finally reached *"Deployment in Progress"* on Tuesday at 10:30 AM, the total time is 25.5 hours. If your SLA is set to 24 hours, the tool will flag this ticket as a breach.
""")

# 2. Quick Guide & CSV Sample (Hidden in a drop-down)
with st.expander("Need help exporting your CSV from Jira?"):
    st.markdown("""
    1. Go to your Jira board or the **Issues** search page.
    2. Filter to find the tickets you want to analyze.
    3. Click the **Export** icon (usually at the top right).
    4. Select **Export Excel CSV (all fields)**. 
    5. Upload that downloaded file below.
    """)
    
    st.markdown("**Sample Expected CSV Format:**\n*(Ensure your export includes at least the 'Key' and 'Date of change' columns)*")
    
    # Visual sample of the expected CSV
    sample_data = {
        "Date of change": ["02 Feb 2026, 10:47:38", "02 Feb 2026, 10:49:09", "02 Feb 2026, 10:47:39"],
        "Key": ["DG-3", "DG-3", "DG-4"],
        "Status": ["TO DO", "CODE/ SECURITY REVIEW", "TO DO"],
        "Status (Changed)": ["IN DEVELOPMENT", "DEPLOYMENT IN PROGRESS", "IN DEVELOPMENT"]
    }
    st.dataframe(pd.DataFrame(sample_data), hide_index=True, use_container_width=True)

st.divider()

# 3. Dynamic SLA Input
st.subheader("1. Define Your SLA")
sla_hours = st.number_input(
    "Enter your SLA limit (in hours):", 
    min_value=1.0, 
    value=24.0, 
    step=1.0, 
    help="For example, enter 24 for a 24-hour SLA, or 48 for a 48-hour SLA."
)

# 4. File uploader
st.subheader("2. Upload Ticket Data")
uploaded_file = st.file_uploader("Upload your Jira CSV export", type=['csv'])

if uploaded_file is not None:
    try:
        # Load and parse data
        df = pd.read_csv(uploaded_file)
        
        # --- FIX APPLIED HERE ---
        df['Date of change'] = pd.to_datetime(df['Date of change'].str.replace('Sept', 'Sep'), format='mixed', dayfirst=True)
        
        # Calculate durations per ticket
        ticket_times = df.groupby('Key')['Date of change'].agg(['min', 'max'])
        ticket_times['duration'] = ticket_times['max'] - ticket_times['min']
        
        # Compute metrics based on custom SLA input
        over_sla_mask = ticket_times['duration'] > pd.Timedelta(hours=sla_hours)
        over_sla_count = over_sla_mask.sum()
        total_tickets = len(ticket_times)
        within_sla_count = total_tickets - over_sla_count
        
        over_sla_rate = (over_sla_count / total_tickets) * 100 if total_tickets > 0 else 0
        within_sla_rate = (within_sla_count / total_tickets) * 100 if total_tickets > 0 else 0
        
        # 5. Expanded Breakdown
        st.success("Analysis Complete!")
        
        col1, col2, col3, col4, col5 = st.columns(5)
        col1.metric("Total Tickets", total_tickets)
        col2.metric(f"Tickets ≤ {sla_hours}h", within_sla_count)
        col3.metric(f"Tickets > {sla_hours}h", over_sla_count)
        col4.metric("Within SLA Rate", f"{within_sla_rate:.2f}%")
        col5.metric("Over SLA Rate", f"{over_sla_rate:.2f}%")

        # Show the actual tickets that failed the SLA
        if over_sla_count > 0:
            st.subheader(f"⚠️ Tickets exceeding {sla_hours} hours")
            # Filter to only the breached tickets and format the duration for readability
            breached_tickets = ticket_times[over_sla_mask].copy()
            breached_tickets['duration'] = breached_tickets['duration'].astype(str)
            st.dataframe(breached_tickets[['duration']], use_container_width=True)
            
    except Exception as e:
        st.error(f"Error processing file. Please ensure it is the correct Jira export format. Details: {e}")
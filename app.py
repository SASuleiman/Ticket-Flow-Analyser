Here is the updated script. I have added the example to the main description and included a visual sample of what the CSV should look like inside the help dropdown. 

Replace your `app.py` with this:

```python
import streamlit as st
import pandas as pd

# Set up the page
st.set_page_config(page_title="Ticket SLA Analyzer", layout="wide")
st.title("Ticket SLA Analyzer")

# 1. Quick Explanation & Example
st.markdown("""
**What this tool does:** It analyzes your Jira ticket history to determine how many tickets took more than 24 hours from their first logged status change to their last.

**Example:** If ticket DG-105 was moved to *"In Development"* on Monday at 9:00 AM, and finally reached *"Deployment in Progress"* on Tuesday at 10:30 AM, the total time is 25.5 hours. The tool will flag this ticket as exceeding the 24-hour SLA.
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

# File uploader
uploaded_file = st.file_uploader("Upload your Jira CSV export", type=['csv'])

if uploaded_file is not None:
    try:
        # Load and parse data
        df = pd.read_csv(uploaded_file)
        df['Date of change'] = pd.to_datetime(df['Date of change'])
        
        # Calculate durations per ticket
        ticket_times = df.groupby('Key')['Date of change'].agg(['min', 'max'])
        ticket_times['duration'] = ticket_times['max'] - ticket_times['min']
        
        # Compute metrics
        over_24h_mask = ticket_times['duration'] > pd.Timedelta(hours=24)
        over_24h_count = over_24h_mask.sum()
        total_tickets = len(ticket_times)
        within_sla = total_tickets - over_24h_count
        percentage = (over_24h_count / total_tickets) * 100 if total_tickets > 0 else 0
        
        # 3. Expanded Breakdown
        st.success("Analysis Complete!")
        
        col1, col2, col3, col4 = st.columns(4)
        col1.metric("Total Tickets", total_tickets)
        col2.metric("Tickets ≤ 24h", within_sla)
        col3.metric("Tickets > 24h", over_24h_count)
        col4.metric("Over 24h Rate", f"{percentage:.2f}%")

        # Show the actual tickets that failed the SLA
        if over_24h_count > 0:
            st.subheader("⚠️ Tickets exceeding 24 hours")
            # Filter to only the breached tickets and format the duration for readability
            breached_tickets = ticket_times[over_24h_mask].copy()
            breached_tickets['duration'] = breached_tickets['duration'].astype(str)
            st.dataframe(breached_tickets[['duration']], use_container_width=True)
            
    except Exception as e:
        st.error(f"Error processing file. Please ensure it is the correct Jira export format. Details: {e}")
```
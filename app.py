import streamlit as st
import pandas as pd

st.title("Ticket SLA Analyzer")
st.write("Calculate the percentage of tickets that took more than 24 hours.")

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
        over_24h = (ticket_times['duration'] > pd.Timedelta(hours=24)).sum()
        total_tickets = len(ticket_times)
        percentage = (over_24h / total_tickets) * 100 if total_tickets > 0 else 0
        
        # Display results
        st.success("Analysis Complete!")
        col1, col2, col3 = st.columns(3)
        col1.metric("Total Tickets", total_tickets)
        col2.metric("Tickets > 24h", over_24h)
        col3.metric("Percentage", f"{percentage:.2f}%")
        
    except Exception as e:
        st.error(f"Error processing file. Ensure it has 'Key' and 'Date of change' columns. Details: {e}")
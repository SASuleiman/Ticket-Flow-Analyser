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

    [🔗 Click here to navigate directly to the Interswitch Issues page on Jira](https://interswitch.atlassian.net/jira/apps/b8361e67-49bc-49c0-846e-cb6f220fd082/afe1f2cb-7969-4b06-b1c0-cd63be89c75b/issue-history)
    """)

st.divider()

# Sidebar Setup for SLA and Filters
st.sidebar.header("⚙️ Settings & Filters")

# REFRESH BUTTON ADDED HERE
if st.sidebar.button("🔄 Refresh Dashboard", help="Click to force the dashboard to reload and recalculate."):
    st.rerun()

st.sidebar.divider()

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
        
        # Get Assignee, Type, Summary, and Issue URL (if it exists)
        cols_to_extract = ['Assignee', 'Issue Type', 'Summary']
        if 'Issue URL' in df.columns:
            cols_to_extract.append('Issue URL')
            
        ticket_info = df.groupby('Key').first()[cols_to_extract]
        tickets_master = ticket_times.join(ticket_info)
        
        # --- INTERACTIVE FILTERS (Sidebar) ---
        st.sidebar.header("🔍 Drill-Down Filters")
        
        assignees = tickets_master['Assignee'].dropna().unique().tolist()
        selected_assignees = st.sidebar.multiselect("Filter by Assignee", assignees, default=assignees)
        
        issue_types = tickets_master['Issue Type'].dropna().unique().tolist()
        selected_types = st.sidebar.multiselect("Filter by Issue Type", issue_types, default=issue_types)
        
        # Apply Filters and Exemptions
        filtered_tickets = tickets_master[
            (tickets_master['Assignee'].isin(selected_assignees)) &
            (tickets_master['Issue Type'].isin(selected_types))
        ]
        
        valid_tickets = filtered_tickets[~filtered_tickets.index.isin(exempt_keys)]
        exempted_tickets = filtered_tickets[filtered_tickets.index.isin(exempt_keys)]
        
        # Compute metrics based on valid, filtered tickets
        over_sla_mask = valid_tickets['Duration (Hours)'] > sla_hours
        over_sla_count = over_sla_mask.sum()
        total_valid_tickets = len(valid_tickets)
        within_sla_count = total_valid_tickets - over_sla_count
        
        over_sla_rate = (over_sla_count / total_valid_tickets) * 100 if total_valid_tickets > 0 else 0
        within_sla_rate = (within_sla_count / total_valid_tickets) * 100 if total_valid_tickets > 0 else 0
        
        # --- METRICS DASHBOARD ---
        st.subheader("📊 Dashboard Results")
        
        col1, col2, col3, col4, col5 = st.columns(5)
        col1.metric("Evaluated Tickets", total_valid_tickets)
        col2.metric(f"Tickets ≤ {sla_hours}h", within_sla_count)
        col3.metric(f"Tickets > {sla_hours}h", over_sla_count)
        col4.metric("Compliance Rate", f"{within_sla_rate:.2f}%")
        col5.metric("SLA Breach Rate", f"{over_sla_rate:.2f}%")

        # --- VISUAL ANALYTICS & EXPORT ---
        if over_sla_count > 0:
            breached_tickets = valid_tickets[over_sla_mask].copy()
            breached_tickets['Duration (Hours)'] = breached_tickets['Duration (Hours)'].round(2)
            
            st.divider()
            col_chart, col_table = st.columns([1, 1.5])
            
            with col_chart:
                st.subheader("📈 Longest Running Tickets")
                # Bar chart of top 10 worst offenders
                top_10 = breached_tickets.sort_values('Duration (Hours)', ascending=False).head(10)
                st.bar_chart(top_10['Duration (Hours)'])
                
            with col_table:
                st.subheader(f"⚠️ SLA Breaches (> {sla_hours} hours)")
                
                # Setup columns to display, prioritizing the clickable URL if available
                display_cols = ['Duration (Hours)', 'Assignee', 'Issue Type', 'Summary']
                if 'Issue URL' in breached_tickets.columns:
                    display_cols.append('Issue URL')
                    
                st.dataframe(
                    breached_tickets[display_cols], 
                    use_container_width=True,
                    column_config={"Issue URL": st.column_config.LinkColumn("Jira Link")} if 'Issue URL' in display_cols else None
                )
                
                # ONE-CLICK EXPORT
                csv_export = breached_tickets.to_csv().encode('utf-8')
                st.download_button(
                    label="📥 Download Breached Tickets (CSV)",
                    data=csv_export,
                    file_name="sla_breaches_report.csv",
                    mime="text/csv",
                )
            
        # Show exempted tickets log at the very bottom
        if not exempted_tickets.empty:
            st.divider()
            st.subheader("🛡️ Exempted Tickets Log")
            exempt_display = exempted_tickets.copy()
            exempt_display['Duration (Hours)'] = exempt_display['Duration (Hours)'].round(2)
            reason_map = dict(zip(edited_exemptions["Ticket Key"].str.strip(), edited_exemptions["Reason for Exemption"]))
            exempt_display['Reason'] = exempt_display.index.map(reason_map)
            
            display_cols_exempt = ['Duration (Hours)', 'Assignee', 'Reason']
            if 'Issue URL' in exempt_display.columns:
                display_cols_exempt.append('Issue URL')
                
            st.dataframe(
                exempt_display[display_cols_exempt], 
                use_container_width=True,
                column_config={"Issue URL": st.column_config.LinkColumn("Jira Link")} if 'Issue URL' in display_cols_exempt else None
            )
            
    except Exception as e:
        st.error(f"Error processing files. Please ensure they are the correct Jira export format. Details: {e}")
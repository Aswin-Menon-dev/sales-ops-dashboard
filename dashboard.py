import streamlit as st
import pandas as pd
import numpy as np
import plotly.express as px
import plotly.graph_objects as go
from datetime import datetime, timedelta
from prophet import Prophet
from io import BytesIO
from fpdf import FPDF
import time

st.set_page_config(page_title="Sales & Operations Dashboard", layout="wide")

# Phase 4 Features: NLP Search, Comment Panel
st.sidebar.markdown("## 🧠 AI Features")
user_query = st.sidebar.text_input("Search (NLP)", placeholder="e.g., show closed deals above $10K")
user_comments = st.sidebar.text_area("📝 Your Comments / Notes")

# Auto-refresh every 5 minutes
REFRESH_INTERVAL = 300
st_autorefresh = st.experimental_rerun if time.time() % REFRESH_INTERVAL < 1 else None

uploaded_files = st.sidebar.file_uploader("Upload Excel Files", type=["xlsx", "xls"], accept_multiple_files=True)

st.sidebar.markdown("---")
st.sidebar.subheader("Google Sheets Integration")
use_google_sheets = st.sidebar.checkbox("Use Google Sheets", value=False)

def load_data():
    sales_frames, ops_frames = [], []
    if use_google_sheets:
        st.info("🔗 Google Sheets integration placeholder.")
        return pd.DataFrame(), pd.DataFrame()
    elif uploaded_files:
        for f in uploaded_files:
            xls = pd.ExcelFile(f)
            if 'Sales' in xls.sheet_names:
                sales_frames.append(xls.parse('Sales'))
            if 'Operations' in xls.sheet_names:
                ops_frames.append(xls.parse('Operations'))
        return (pd.concat(sales_frames, ignore_index=True) if sales_frames else pd.DataFrame(),
                pd.concat(ops_frames, ignore_index=True) if ops_frames else pd.DataFrame())
    else:
        sales = pd.DataFrame({
            'Lead ID': range(1, 21),
            'Lead Source': np.random.choice(['LinkedIn', 'Website', 'Referral', 'Cold Call'], 20),
            'Status': np.random.choice(['New', 'Contacted', 'Qualified', 'Proposal Sent', 'Negotiation', 'Closed-Won', 'Closed-Lost'], 20),
            'Deal Value ($)': np.random.randint(5000, 50000, size=20),
            'Salesperson': np.random.choice(['Alice', 'Bob', 'Carol'], 20),
            'Date Created': pd.date_range(datetime.today() - timedelta(days=60), periods=20).to_pydatetime().tolist(),
            'Date Closed': [datetime.today() - timedelta(days=np.random.randint(1, 30)) if np.random.rand() > 0.5 else None for _ in range(20)]
        })
        ops = sales[sales['Status'] == 'Closed-Won'].copy()
        ops['Project Status'] = np.random.choice(['Planning', 'In Progress', 'Stalled', 'Completed'], len(ops))
        ops['Kickoff Date'] = [d + timedelta(days=3) for d in ops['Date Closed']]
        ops['Expected Completion'] = [d + timedelta(days=30) for d in ops['Kickoff Date']]
        ops['Actual Completion'] = [d + timedelta(days=np.random.randint(25, 40)) for d in ops['Kickoff Date']]
        return sales, ops

sales_data, ops_data = load_data()

st.sidebar.title("Navigation")
section = st.sidebar.radio("Go to", ["Sales Pipeline", "Operations Workflow", "Operations Calendar"])
st.sidebar.markdown("---")
st.sidebar.subheader("Filters")

salespersons = sales_data['Salesperson'].unique().tolist() if not sales_data.empty else []
selected_salesperson = st.sidebar.multiselect("Salesperson", options=salespersons, default=salespersons)

if not sales_data.empty:
    date_range = st.sidebar.date_input("Date Range", [sales_data['Date Created'].min(), sales_data['Date Created'].max()])
else:
    date_range = [datetime.today() - timedelta(days=30), datetime.today()]

filtered_sales = sales_data[
    (sales_data['Salesperson'].isin(selected_salesperson)) &
    (sales_data['Date Created'] >= pd.to_datetime(date_range[0])) &
    (sales_data['Date Created'] <= pd.to_datetime(date_range[1]))
] if not sales_data.empty else pd.DataFrame()

st.sidebar.markdown("---")
st.sidebar.subheader("Goal Tracking")
sales_goal = st.sidebar.number_input("Quarterly Sales Goal ($)", min_value=10000, value=300000)
ops_goal = st.sidebar.number_input("Monthly Project Goal", min_value=1, value=10)

sales_total = filtered_sales[filtered_sales['Status'] == 'Closed-Won']['Deal Value ($)'].sum() if not filtered_sales.empty and 'Status' in filtered_sales.columns else 0
ops_total = len(ops_data) if not ops_data.empty else 0

sales_progress = round((sales_total / sales_goal) * 100, 2) if sales_goal > 0 else 0
ops_progress = round((ops_total / ops_goal) * 100, 2) if ops_goal > 0 else 0

if section == "Sales Pipeline":
    st.title("🔄 Sales Pipeline Overview")
    col1, col2, col3 = st.columns(3)
    col1.metric("Total Leads", len(filtered_sales))
    col2.metric("Closed-Won", (filtered_sales['Status'] == 'Closed-Won').sum() if 'Status' in filtered_sales.columns else "N/A")
    col3.metric("Total Deal Value ($)", f"{sales_total:,.0f}")
    st.progress(min(sales_progress / 100, 1.0), text=f"Sales Goal: {sales_progress}% of ${sales_goal:,.0f}")

    chart_type = st.selectbox("📊 Select Chart Type", ["Pie", "Bar", "Line", "Histogram"], index=0)
    if not filtered_sales.empty and 'Lead Source' in filtered_sales.columns:
        chart_data = filtered_sales.groupby('Lead Source')['Deal Value ($)'].sum().reset_index()

        if chart_type == "Pie":
            fig = px.pie(chart_data, names='Lead Source', values='Deal Value ($)', title='Revenue by Lead Source')
        elif chart_type == "Bar":
            fig = px.bar(chart_data, x='Lead Source', y='Deal Value ($)', title='Revenue by Lead Source', text_auto=True)
        elif chart_type == "Line":
            fig = px.line(chart_data, x='Lead Source', y='Deal Value ($)', title='Revenue by Lead Source')
        elif chart_type == "Histogram":
            fig = px.histogram(filtered_sales, x='Deal Value ($)', title='Distribution of Deal Values by Source', color='Lead Source')

        st.plotly_chart(fig, use_container_width=True)

    st.subheader("🔍 Drill-down: Individual Deals")
    st.dataframe(filtered_sales)

elif section == "Operations Workflow":
    st.title("🛠 Operations Workflow Overview")
    col1, col2, col3 = st.columns(3)
    col1.metric("Active Projects", len(ops_data))
    col2.metric("Completed Projects", (ops_data['Project Status'] == 'Completed').sum() if 'Project Status' in ops_data.columns else "N/A")
    col3.metric("SLA Breaches", (ops_data['Actual Completion'] > ops_data['Expected Completion']).sum() if 'Actual Completion' in ops_data.columns and 'Expected Completion' in ops_data.columns else "N/A")
    st.progress(min(ops_progress / 100, 1.0), text=f"Operations Goal: {ops_progress}% of {ops_goal} projects")

    chart_type_ops = st.selectbox("📊 Select Operations Chart Type", ["Bar", "Pie", "Histogram"], index=0)
    if not ops_data.empty and 'Project Status' in ops_data.columns:
        ops_status_data = ops_data['Project Status'].value_counts().reset_index()
        ops_status_data.columns = ['Status', 'Count']

        if chart_type_ops == "Bar":
            fig_ops = px.bar(ops_status_data, x='Status', y='Count', color='Status', text_auto=True, title="Project Status Distribution")
        elif chart_type_ops == "Pie":
            fig_ops = px.pie(ops_status_data, names='Status', values='Count', title="Project Status Distribution")
        elif chart_type_ops == "Histogram":
            fig_ops = px.histogram(ops_data, x='Project Status', title="Project Status Histogram")

        st.plotly_chart(fig_ops, use_container_width=True)

    st.subheader("🔍 Drill-down: Operations Projects")
    st.dataframe(ops_data)

elif section == "Operations Calendar":
    st.title("📅 Project Timeline View")
    if not ops_data.empty and {'Kickoff Date', 'Expected Completion'}.issubset(ops_data.columns):
        timeline_data = ops_data[['Lead ID', 'Kickoff Date', 'Expected Completion']].copy()
        timeline_data.rename(columns={
            'Lead ID': 'Task', 'Kickoff Date': 'Start', 'Expected Completion': 'Finish'
        }, inplace=True)
        fig = px.timeline(timeline_data, x_start='Start', x_end='Finish', y='Task')
        fig.update_yaxes(autorange="reversed")
        st.plotly_chart(fig, use_container_width=True)
    else:
        st.warning("No timeline data available or missing columns.")

if user_query:
    st.markdown(f"#### 🔍 Search Query: `{user_query}` (feature in progress)")
    st.info("This will soon allow natural-language filtering and summarization.")

if user_comments:
    st.markdown("---")
    st.markdown(f"#### 💬 Your Notes")
    st.code(user_comments, language='markdown')

st.markdown("---")
st.markdown("<p style='text-align:center; color:gray;'>This is a prototype (Developed by Aswin Menon)</p>", unsafe_allow_html=True)

import streamlit as st
import pandas as pd
import plotly.express as px
import requests
from datetime import datetime, timedelta
import urllib3

# Suppress SSL warnings
urllib3.disable_warnings(urllib3.exceptions.InsecureRequestWarning)

# --- CONFIG ---
API_SECRET = "$4.4$1e90022d47b1211e828b665475bc72b3eb1a84eb"
SERVER = "zahratun-jondor.iiko.it"
BASE_URL = f"https://{SERVER}/resto/api"

st.set_page_config(page_title="Zahratun Jondor Analytics", layout="wide")

# --- API FUNCTIONS ---
def get_token():
    url = f"{BASE_URL}/auth/access_token?apiSecret={API_SECRET}"
    try:
        res = requests.get(url, timeout=10, verify=False)
        if res.status_code == 200:
            return res.text.replace('"', '').strip()
    except Exception as e:
        st.error(f"Connection Error: {e}")
    return None

def test_connection():
    url = f"https://{SERVER}/resto/api/auth/access_token?apiSecret={API_SECRET}"
    res = requests.get(url, verify=False)
    st.write(f"Статус: {res.status_code}")
    st.write(f"Ответ: {res.text}")
    # Define date range
    date_from = (datetime.now() - timedelta(days=7)).strftime("%Y-%m-%d")
    date_to = datetime.now().strftime("%Y-%m-%d")
    
    params = {
        "key": token,
        "reportType": "SALES",
        "groupByRowFields": "Date.Typed",
        "aggregateFields": "DishCostAfterDiscount.Sum,UniqTransId.Count",
        "from": date_from,
        "to": date_to
    }
    
    try:
        res = requests.get(url, params=params, headers=headers, timeout=20, verify=False)
        if res.status_code == 200:
            raw_data = res.json()
            # iiko OLAP JSON structure usually has a 'data' list of dicts
            if 'data' in raw_data:
                df = pd.DataFrame(raw_data['data'])
                # Rename columns based on your query order
                df.columns = ['Дата', 'Выручка', 'Чеки']
                df['Дата'] = pd.to_datetime(df['Дата']).dt.date
                return df
        else:
            st.error(f"Server returned error {res.status_code}: {res.text}")
    except Exception as e:
        st.error(f"Data Fetch Error: {e}")
    return None

# --- UI ---
st.title("📊 Zahratun Jondor: Live Analytics")

if st.sidebar.button("🔄 Sync Data"):
    with st.spinner("Connecting to iiko..."):
        token = get_token()
        if token:
            df = get_data(token)
            if df is not None:
                st.session_state['df'] = df
                st.success("Data Updated!")
        else:
            st.error("Failed to authenticate. Check API Key or Server access.")

# Display Data if it exists in session
if 'df' in st.session_state:
    df = st.session_state['df']
    
    col1, col2 = st.columns(2)
    with col1:
        total_rev = df['Выручка'].sum()
        st.metric("Weekly Revenue", f"{total_rev:,.0f} UZS")
    with col2:
        total_orders = df['Чеки'].sum()
        st.metric("Total Checks", f"{total_orders}")

    st.plotly_chart(px.line(df, x='Дата', y='Выручка', title="Revenue Trend"), use_container_width=True)
    st.dataframe(df, use_container_width=True)

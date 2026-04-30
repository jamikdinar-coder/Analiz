import streamlit as st
import pandas as pd
import plotly.express as px
import requests
import urllib3
from datetime import datetime, timedelta
from typing import Optional, Tuple, Dict, Any

# Suppress insecure request warnings for self-signed certificates
urllib3.disable_warnings(urllib3.exceptions.InsecureRequestWarning)

# ==================== CONFIGURATION ====================
SERVER = "zahratun-jondor.iiko.it"

# Priority: Secrets > Manual strings
USER_LOGIN: str = st.secrets.get("USER_LOGIN", "jamshid")
USER_PASS: str = st.secrets.get("USER_PASS", "02051987")

# ====================== SESSION ======================
@st.cache_data(ttl=600, show_spinner=False)
def get_iiko_session() -> Optional[Tuple[requests.Session, str, str]]:
    session = requests.Session()
    # Check both HTTPS and HTTP (standard iiko ports)
    urls = [
        f"https://{SERVER}/resto/api/auth/login",
        f"http://{SERVER}:8080/resto/api/auth/login",
    ]
    for url in urls:
        try:
            resp = session.get(
                url,
                params={"login": USER_LOGIN, "pass": USER_PASS},
                timeout=10,
                verify=False
            )
            if resp.status_code == 200:
                token = resp.text.strip().strip('"')
                if token and len(token) > 5:
                    base_url = url.split("/resto")[0]
                    return session, token, base_url
        except Exception:
            continue
    return None

# ====================== DATA FETCHING ======================
@st.cache_data(ttl=300, show_spinner="Fetching data from iiko...")
def fetch_sales(period_days: int = 7) -> Optional[pd.DataFrame]:
    session_data = get_iiko_session()
    if not session_data:
        st.error("❌ Authentication failed. Check server status and credentials.")
        return None

    session, token, base_url = session_data
    today = datetime.now()

    # Period logic
    if period_days == 999:  # This Month
        date_from = today.replace(day=1).strftime("%Y-%m-%d")
        date_to = today.strftime("%Y-%m-%d")
    elif period_days == 998:  # Last Month
        first_day_this_month = today.replace(day=1)
        last_day_prev_month = first_day_this_month - timedelta(days=1)
        date_from = last_day_prev_month.replace(day=1).strftime("%Y-%m-%d")
        date_to = last_day_prev_month.strftime("%Y-%m-%d")
    else:
        date_from = (today - timedelta(days=period_days)).strftime("%Y-%m-%d")
        date_to = today.strftime("%Y-%m-%d")

    params = {
        "key": token,
        "reportType": "SALES",
        "groupByRowFields": "OpenDate.Typed",
        "aggregateFields": "Sum,UniqOrderId.Count",
        "from": date_from,
        "to": date_to,
        "buildSummary": "false"
    }

    try:
        response = session.get(
            f"{base_url}/resto/api/reports/olap",
            params=params,
            headers={"Accept": "application/json"},
            timeout=20,
            verify=False
        )
        
        if response.status_code != 200:
            st.error(f"API Error {response.status_code}: {response.text[:100]}")
            return None

        raw = response.json()
        if not raw.get("data"):
            return pd.DataFrame()

        df = pd.DataFrame(raw["data"])
        
        # Mapping columns based on iiko OLAP response order
        df.columns = ["Дата", "Выручка", "Чеки"]
        
        # Type Conversion
        df["Дата"] = pd.to_datetime(df["Дата"]).dt.date
        df["Выручка"] = pd.to_numeric(df["Выручка"], errors="coerce").fillna(0)
        df["Чеки"] = pd.to_numeric(df["Чеки"], errors="coerce").fillna(0).astype(int)
        
        # Derived Metric
        df["Средний чек"] = (df["Выручка"] / df["Чеки"]).fillna(0).round(0)
        
        return df.sort_values("Дата").reset_index(drop=True)

    except Exception as e:
        st.error(f"Connection Error: {e}")
        return None

# ====================== UI SETUP ======================
st.set_page_config(page_title="iiko Sales Analytics", layout="wide")
st.title("📊 iiko Sales Analytics")

with st.sidebar:
    st.header("Settings")
    period_option = st.selectbox(
        "Period Selection:",
        options=["Last 7 days", "Last 14 days", "Last 30 days", "This Month", "Last Month"],
        index=0
    )
    
    period_map = {
        "Last 7 days": 7, "Last 14 days": 14, "Last 30 days": 30,
        "This Month": 999, "Last Month": 998
    }
    
    if st.button("🔄 Refresh Data", use_container_width=True):
        st.cache_data.clear()
        st.rerun()

# Execution
df = fetch_sales(period_days=period_map[period_option])

if df is not None and not df.empty:
    # Key Metrics
    m1, m2, m3, m4 = st.columns(4)
    m1.metric("Total Revenue", f"{df['Выручка'].sum():,.0f} UZS")
    m2.metric("Total Orders", f"{df['Чеки'].sum():,}")
    m3.metric("Avg. Ticket", f"{(df['Выручка'].sum() / df['Чеки'].sum()):,.0f} UZS")
    m4.metric("Days Active", len(df))

    # Visualization
    tab1, tab2 = st.tabs(["📈 Revenue Trend", "🧾 Volume & Avg. Ticket"])
    
    with tab1:
        fig_rev = px.bar(df, x="Дата", y="Выручка", text_auto='.2s', title="Daily Revenue")
        st.plotly_chart(fig_rev, use_container_width=True)
        
    with tab2:
        fig_vol = px.line(df, x="Дата", y=["Чеки", "Средний чек"], markers=True, title="Order Count vs Avg. Ticket")
        st.plotly_chart(fig_vol, use_container_width=True)

    # Raw Data Table
    with st.expander("View Detailed Table"):
        st.dataframe(df, use_container_width=True, hide_index=True)
        
elif df is not None and df.empty:
    st.warning("No data found for the selected range.")

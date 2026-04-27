import streamlit as st
import pandas as pd
import plotly.express as px
import requests
from datetime import datetime, timedelta

# --- ÊÎÍÔÈÃÓÐÀÖÈß ---
API_SECRET = "$4.4$1e90022d47b1211e828b665475bc72b3eb1a84eb"
ORGANIZATION_ID = "5930393"
BASE_URL = "https://iiko.biz:9900/api/0/"

st.set_page_config(page_title="Zahratun Analytics Live", layout="wide")

# --- ÔÓÍÊÖÈÈ API ---
def get_access_token():
    """Ïîëó÷àåì âðåìåííûé òîêåí äëÿ ðàáîòû"""
    url = f"{BASE_URL}auth/access_token?apiSecret={API_SECRET}"
    try:
        response = requests.get(url, timeout=10)
        return response.text.replace('"', '')
    except:
        return None

def get_access_token():
    """Получаем временный токен с исправлением кодировки"""
    url = f"{BASE_URL}auth/access_token?apiSecret={API_SECRET}"
    try:
        response = requests.get(url, timeout=10)
        # ИСПРАВЛЕНИЕ ТУТ: принудительно ставим кодировку, чтобы не было ошибки utf-8
        response.encoding = 'windows-1251' 
        return response.text.replace('"', '').strip()
    except Exception as e:
        st.error(f"Ошибка сетевого запроса: {e}")
        return None
        
    payload = {
        "reportType": "SALES",
        "groupByRowFields": ["Date.Typed"],
        "aggregateFields": ["DishCostAfterDiscount.Sum", "UniqTransId.Count"],
        "filters": {
            "Date.Typed": {
                "filterType": "DateRange",
                "periodType": "CUSTOM",
                "from": (datetime.now() - timedelta(days=7)).strftime("%Y-%m-%d"),
                "to": datetime.now().strftime("%Y-%m-%d")
            }
        }
    }
    
    try:
        res = requests.post(url, json=payload)
        data = res.json()
        # Ïðåâðàùàåì îòâåò iiko â òàáëèöó Pandas
        df = pd.DataFrame(data['data'])
        df.columns = ['Äàòà', 'Âûðó÷êà', '×åêè']
        df['Äàòà'] = pd.to_datetime(df['Äàòà']).dt.date
        return df
    except:
        return None

# --- ÈÍÒÅÐÔÅÉÑ ---
st.title("?? Zahratun Jondor: Live Analytics")
st.sidebar.header("Óïðàâëåíèå")

if st.sidebar.button("Îáíîâèòü äàííûå èç iiko"):
    token = get_access_token()
    if token:
        df_sales = get_real_sales(token)
        
        if df_sales is not None:
            st.success(f"Äàííûå îáíîâëåíû â {datetime.now().strftime('%H:%M:%S')}")
            
            # Îñíîâíûå KPI
            total_rev = df_sales['Âûðó÷êà'].sum()
            total_checks = df_sales['×åêè'].sum()
            avg_check = total_rev / total_checks if total_checks > 0 else 0
            
            c1, c2, c3 = st.columns(3)
            c1.metric("Âûðó÷êà (7 äí)", f"{total_rev:,.0f} ñóì")
            c2.metric("Âñåãî ÷åêîâ", f"{total_checks}")
            c3.metric("Ñðåäíèé ÷åê", f"{avg_check:,.0f} ñóì")
            
            # Ãðàôèê
            st.subheader("Äèíàìèêà âûðó÷êè")
            fig = px.line(df_sales, x='Äàòà', y='Âûðó÷êà', markers=True, template="plotly_dark")
            st.plotly_chart(fig, use_container_width=True)
            
            # Òàáëèöà
            st.subheader("Äåòàëèçàöèÿ ïî äíÿì")
            st.dataframe(df_sales, use_container_width=True)
        else:
            st.error("Íå óäàëîñü ïîëó÷èòü äàííûå. Ïðîâåðüòå ïðàâà API â iikoOffice.")
    else:
        st.error("Îøèáêà àâòîðèçàöèè. Ïðîâåðüòå Êëþ÷ API.")
else:
    st.info("Íàæìèòå êíîïêó â ìåíþ ñëåâà, ÷òîáû çàãðóçèòü æèâûå äàííûå èç iiko.")

st.markdown("---")
st.caption("Ñèñòåìà ñèíõðîíèçèðîâàíà ñ ñåðâåðîì Zahratun Jondor ÷åðåç iikoCloud API v.9")

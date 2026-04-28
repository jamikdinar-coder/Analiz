import streamlit as st
import pandas as pd
import plotly.express as px
import requests
from datetime import datetime, timedelta
import urllib3

# Отключаем проверку SSL-сертификатов (важно для локальных серверов)
urllib3.disable_warnings(urllib3.exceptions.InsecureRequestWarning)

# Твои данные
API_SECRET = "$4.4$1e90022d47b1211e828b665475bc72b3eb1a84eb"
SERVER = "zahratun-jondor.iiko.it"

st.set_page_config(page_title="Zahratun Jondor Analytics", layout="wide")

def get_token():
    # Пробуем 3 разных варианта адреса, которые могут быть на твоем сервере
    variants = [
        f"https://{SERVER}/resto/api/auth/access_token?apiSecret={API_SECRET}",
        f"http://{SERVER}:8080/resto/api/auth/access_token?apiSecret={API_SECRET}", # Иногда API работает на 8080
        f"https://{SERVER}:443/resto/api/auth/access_token?apiSecret={API_SECRET}"
    ]
    
    for url in variants:
        try:
            res = requests.get(url, timeout=10, verify=False)
            if res.status_code == 200:
                return res.text.replace('"', '').strip()
        except:
            continue
    return None

def get_data(token):
    # Если токен получен, запрашиваем отчет
    url = f"https://{SERVER}/resto/api/reports/olap"
    params = {
        "key": token,
        "reportType": "SALES",
        "groupByRowFields": "Date.Typed",
        "aggregateFields": "DishCostAfterDiscount.Sum,UniqTransId.Count",
        "from": (datetime.now() - timedelta(days=7)).strftime("%Y-%m-%d"),
        "to": datetime.now().strftime("%Y-%m-%d")
    }
    
    try:
        res = requests.get(url, params=params, timeout=20, verify=False)
        if res.status_code == 200:
            data = res.json()
            if 'data' in data:
                df = pd.DataFrame(data['data'])
                df.columns = ['Дата', 'Выручка', 'Чеки']
                df['Дата'] = pd.to_datetime(df['Дата']).dt.date
                return df
        st.error(f"Ошибка отчета ({res.status_code})")
    except:
        st.error("Ошибка при получении данных отчета")
    return None

# --- ИНТЕРФЕЙС ---
st.title("📊 Zahratun Jondor: Live")

if st.sidebar.button("🔄 Синхронизировать"):
    token = get_token()
    if token:
        df = get_data(token)
        if df is not None:
            st.success("Данные обновлены!")
            st.metric("Выручка за неделю", f"{df['Выручка'].sum():,.0f} сум")
            st.plotly_chart(px.bar(df, x='Дата', y='Выручка'))
            st.dataframe(df)
    else:
        st.error("❌ Не удалось найти API iiko. Возможно, внешний доступ к серверу закрыт.")

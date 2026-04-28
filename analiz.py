import streamlit as st
import pandas as pd
import plotly.express as px
import requests
from datetime import datetime, timedelta

# Твои данные
API_SECRET = "$4.4$1e90022d47b1211e828b665475bc72b3eb1a84eb"
SERVER = "zahratun-jondor.iiko.it"

st.set_page_config(page_title="Zahratun Analytics Pro", layout="wide")

def get_token():
    # Мы пробуем все варианты путей, которые бывают в iiko 9.4
    variants = [
        f"https://{SERVER}/resto/api/auth/access_token?apiSecret={API_SECRET}",
        f"https://{SERVER}:443/resto/api/auth/access_token?apiSecret={API_SECRET}",
        f"https://{SERVER}/api/0/auth/access_token?apiSecret={API_SECRET}"
    ]
    
    for url in variants:
        try:
            res = requests.get(url, timeout=10)
            if res.status_code == 200:
                # Убираем кавычки, если они есть
                return res.text.replace('"', '').strip()
        except:
            continue
    return None

def get_data(token):
    # Если токен получили, пробуем забрать отчет
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
        res = requests.get(url, params=params, timeout=20)
        if res.status_code == 200:
            data = res.json()
            if 'data' in data and data['data']:
                df = pd.DataFrame(data['data'])
                df.columns = ['Дата', 'Выручка', 'Чеки']
                df['Дата'] = pd.to_datetime(df['Дата']).dt.date
                return df
        st.error(f"Сервер ответил ({res.status_code}): {res.text[:100]}")
    except Exception as e:
        st.error(f"Ошибка отчета: {e}")
    return None

# --- ИНТЕРФЕЙС ---
st.title("📊 Zahratun Jondor: Live Analytics")

if st.sidebar.button("🔄 Обновить из iiko"):
    with st.spinner('Проверяю все каналы связи с Jondor...'):
        token = get_token()
        if token:
            df = get_data(token)
            if df is not None:
                st.success("✅ Соединение установлено, данные получены!")
                
                col1, col2 = st.columns(2)
                col1.metric("Выручка (7д)", f"{df['Выручка'].sum():,.0f} сум")
                col2.metric("Всего чеков", f"{df['Чеки'].sum()}")
                
                st.plotly_chart(px.area(df, x='Дата', y='Выручка', title="Продажи"))
                st.dataframe(df, use_container_width=True)
        else:
            st.error("❌ Не удалось найти API. Проверь, запущен ли iikoServer на компьютере в ресторане.")
else:
    st.info("Нажмите кнопку для синхронизации.")

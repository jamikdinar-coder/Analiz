import streamlit as st
import pandas as pd
import plotly.express as px
import requests
from datetime import datetime, timedelta

# Данные твоего сервера из скриншотов
API_SECRET = "$4.4$1e90022d47b1211e828b665475bc72b3eb1a84eb"
BASE_URL = "https://zahratun-jondor.iiko.it:443/resto/api/" 

st.set_page_config(page_title="Zahratun Analytics", layout="wide")

def get_token():
    """Получение токена с правильной кодировкой для русского языка"""
    url = f"{BASE_URL}auth/access_token?apiSecret={API_SECRET}"
    try:
        response = requests.get(url, timeout=10)
        # iiko часто отдает в cp1251, принудительно ставим её
        response.encoding = 'cp1251' 
        return response.text.replace('"', '').strip()
    except Exception as e:
        st.error(f"Ошибка соединения: {e}")
        return None

def get_data(token):
    """Запрос продаж за неделю"""
    url = f"{BASE_URL}reports/olap?access_token={token}"
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
        res = requests.post(url, json=payload, timeout=15)
        res.encoding = 'cp1251'
        raw_data = res.json()
        df = pd.DataFrame(raw_data['data'])
        df.columns = ['Дата', 'Выручка', 'Чеки']
        df['Дата'] = pd.to_datetime(df['Дата']).dt.date
        return df
    except Exception as e:
        st.error(f"Ошибка данных: {e}")
        return None

# --- ИНТЕРФЕЙС ---
st.title("📊 Zahratun Jondor: Оперативный отчет")

if st.sidebar.button("🔄 Обновить данные iiko"):
    token = get_token()
    if token:
        df = get_data(token)
        if df is not None:
            st.success("Данные успешно загружены!")
            
            # Метрики
            c1, c2 = st.columns(2)
            c1.metric("Выручка за неделю", f"{df['Выручка'].sum():,.0f} сум")
            c2.metric("Всего чеков", f"{df['Чеки'].sum()}")
            
            # График
            fig = px.line(df, x='Дата', y='Выручка', markers=True, title="Продажи по дням")
            st.plotly_chart(fig, use_container_width=True)
            
            st.dataframe(df, use_container_width=True)
    else:
        st.error("Не удалось подключиться. Проверьте API ключ.")
else:
    st.info("Нажмите кнопку 'Обновить данные' в боковом меню.")

import streamlit as st
import pandas as pd
import plotly.express as px
import requests
from datetime import datetime, timedelta

# Твои данные
API_SECRET = "$4.4$1e90022d47b1211e828b665475bc72b3eb1a84eb"
# Убираем все лишнее из базового адреса
BASE_URL = "https://zahratun-jondor.iiko.it/resto/api" 

st.set_page_config(page_title="Zahratun Jondor Analytics", layout="wide")

def get_token():
    # Пробуем получить токен. Если первый путь не сработает (404), попробуем запасной.
    urls = [
        f"{BASE_URL}/auth/access_token?apiSecret={API_SECRET}",
        f"https://zahratun-jondor.iiko.it/resto/api/auth/access_token?apiSecret={API_SECRET}"
    ]
    for url in urls:
        try:
            res = requests.get(url, timeout=10)
            if res.status_code == 200:
                return res.text.replace('"', '').strip()
        except:
            continue
    return None

def get_data(token):
    # OLAP отчет. Передаем ключ именно так, как просила прошлая ошибка
    url = f"{BASE_URL}/reports/olap"
    
    params = {
        "key": token,
        "reportType": "SALES",
        "groupByRowFields": "Date.Typed",
        "aggregateFields": "DishCostAfterDiscount.Sum,UniqTransId.Count",
        "from": (datetime.now() - timedelta(days=7)).strftime("%Y-%m-%d"),
        "to": datetime.now().strftime("%Y-%m-%d")
    }
    
    try:
        # Пробуем GET, так как он более стабилен для этой версии
        res = requests.get(url, params=params, timeout=20)
        if res.status_code == 200:
            raw = res.json()
            if 'data' in raw and raw['data']:
                df = pd.DataFrame(raw['data'])
                df.columns = ['Дата', 'Выручка', 'Чеки']
                df['Дата'] = pd.to_datetime(df['Дата']).dt.date
                return df
        st.error(f"Сервер ответил ({res.status_code}): {res.text[:100]}")
    except Exception as e:
        st.error(f"Ошибка: {e}")
    return None

# --- ИНТЕРФЕЙС ---
st.title("📊 Zahratun Jondor: Оперативный отчет")

if st.sidebar.button("🔄 Обновить данные iiko"):
    with st.spinner('Подключение к серверу...'):
        token = get_token()
        if token:
            df = get_data(token)
            if df is not None:
                st.success("Данные получены!")
                c1, c2 = st.columns(2)
                c1.metric("Выручка (7д)", f"{df['Выручка'].sum():,.0f} сум")
                c2.metric("Чеков", f"{df['Чеки'].sum()}")
                st.plotly_chart(px.line(df, x='Дата', y='Выручка', markers=True))
                st.dataframe(df)
        else:
            st.error("Не удалось получить Token. Проверьте связь с сервером.")

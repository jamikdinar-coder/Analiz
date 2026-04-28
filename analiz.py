import streamlit as st
import pandas as pd
import plotly.express as px
import requests
from datetime import datetime, timedelta

# Твои данные из скриншотов
API_SECRET = "$4.4$1e90022d47b1211e828b665475bc72b3eb1a84eb"
SERVER_HOST = "zahratun-jondor.iiko.it"

st.set_page_config(page_title="Zahratun Jondor Analytics", layout="wide")

def get_token():
    # Пробуем два самых частых варианта пути для версии 9.4
    paths = [
        f"https://{SERVER_HOST}/resto/api/auth/access_token?apiSecret={API_SECRET}",
        f"https://{SERVER_HOST}:443/resto/api/auth/access_token?apiSecret={API_SECRET}"
    ]
    
    for url in paths:
        try:
            res = requests.get(url, timeout=10)
            if res.status_code == 200:
                # Очищаем токен от кавычек и пробелов
                return res.text.replace('"', '').strip()
        except:
            continue
    return None

def get_data(token):
    # Путь для получения OLAP-отчета
    url = f"https://{SERVER_HOST}/resto/api/reports/olap"
    
    # Параметры запроса (для iiko 9.x часто лучше работает GET)
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
            raw = res.json()
            if 'data' in raw and raw['data']:
                df = pd.DataFrame(raw['data'])
                df.columns = ['Дата', 'Выручка', 'Чеки']
                df['Дата'] = pd.to_datetime(df['Дата']).dt.date
                return df
        st.error(f"Сервер ответил ({res.status_code}): {res.text[:100]}")
    except Exception as e:
        st.error(f"Ошибка при загрузке отчета: {e}")
    return None

# --- ИНТЕРФЕЙС ---
st.title("📊 Zahratun Jondor: Оперативный отчет")

if st.sidebar.button("🔄 Обновить данные iiko"):
    with st.spinner('Подключаюсь к филиалу Jondor...'):
        token = get_token()
        if token:
            df = get_data(token)
            if df is not None:
                st.success("Данные успешно синхронизированы!")
                
                col1, col2, col3 = st.columns(3)
                rev = df['Выручка'].sum()
                checks = df['Чеки'].sum()
                
                col1.metric("Выручка (7д)", f"{rev:,.0f} сум")
                col2.metric("Чеков", f"{checks}")
                col3.metric("Средний чек", f"{(rev/checks if checks > 0 else 0):,.0f}")
                
                st.plotly_chart(px.area(df, x='Дата', y='Выручка', title="Продажи за неделю"))
                st.dataframe(df, use_container_width=True)
        else:
            st.error("Не удалось получить Token. Проверьте, включен ли сервер в Jondor.")
else:
    st.info("Нажмите кнопку слева, чтобы затянуть данные из iiko.")

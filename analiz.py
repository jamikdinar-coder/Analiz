import streamlit as st
import pandas as pd
import plotly.express as px
import requests
from datetime import datetime, timedelta

# Твои данные
API_SECRET = "$4.4$1e90022d47b1211e828b665475bc72b3eb1a84eb"
# Исправил базовый адрес: убираем /api/ в конце, будем добавлять его в функциях
BASE_URL = "https://zahratun-jondor.iiko.it:443/resto/api" 

st.set_page_config(page_title="Zahratun Jondor Analytics", layout="wide")

def get_token():
    # Для получения токена обычно используется GET
    url = f"{BASE_URL}/auth/access_token?apiSecret={API_SECRET}"
    try:
        response = requests.get(url, timeout=15)
        response.encoding = 'cp1251'
        return response.text.replace('"', '').strip()
    except Exception as e:
        st.error(f"Ошибка авторизации: {e}")
        return None

def get_data(token):
    # В некоторых версиях путь может быть /reports/olap, в других /v2/reports/olap
    # Попробуем самый надежный для v.9
    url = f"{BASE_URL}/reports/olap?access_token={token}"
    
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
        # Если POST выдает 405, iiko может ждать данные в GET параметрах, 
        # но для OLAP это редкость. Скорее всего, дело в адресе.
        res = requests.post(url, json=payload, timeout=25)
        
        if res.status_code == 200:
            raw_data = res.json()
            df = pd.DataFrame(raw_data['data'])
            df.columns = ['Дата', 'Выручка', 'Чеки']
            df['Дата'] = pd.to_datetime(df['Дата']).dt.date
            return df
        else:
            # Выводим подробности, если снова будет ошибка
            st.error(f"Сервер iiko ответил: {res.status_code}. Текст: {res.text[:100]}")
            return None
    except Exception as e:
        st.error(f"Ошибка при обработке отчета: {e}")
        return None

# --- ИНТЕРФЕЙС ---
st.title("📊 Zahratun Jondor: Оперативный отчет")

if st.sidebar.button("🔄 Обновить данные iiko"):
    with st.spinner('Запрос к Zahratun Jondor...'):
        token = get_token()
        if token:
            df = get_data(token)
            if df is not None:
                st.success("Данные успешно получены!")
                
                # Метрики
                total_rev = df['Выручка'].sum()
                total_checks = df['Чеки'].sum()
                c1, c2, c3 = st.columns(3)
                c1.metric("Выручка (7д)", f"{total_rev:,.0f} сум")
                c2.metric("Чеков", f"{total_checks}")
                c3.metric("Средний чек", f"{(total_rev/total_checks if total_checks > 0 else 0):,.0f}")
                
                # График
                fig = px.area(df, x='Дата', y='Выручка', title="Продажи за неделю")
                st.plotly_chart(fig, use_container_width=True)
                
                st.dataframe(df, use_container_width=True)
        else:
            st.error("Не удалось получить ключ доступа (Token).")
else:
    st.info("Нажмите кнопку слева для загрузки.")

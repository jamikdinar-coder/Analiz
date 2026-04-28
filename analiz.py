import streamlit as st
import pandas as pd
import plotly.express as px
import requests
from datetime import datetime, timedelta

# Твои данные из скриншотов
API_SECRET = "$4.4$1e90022d47b1211e828b665475bc72b3eb1a84eb"
BASE_URL = "https://zahratun-jondor.iiko.it:443/resto/api/"

st.set_page_config(page_title="Zahratun Jondor Live", layout="wide")

def get_token():
    url = f"{BASE_URL}auth/access_token?apiSecret={API_SECRET}"
    try:
        response = requests.get(url, timeout=15)
        # Если сервер прислал ошибку кодировки, пробуем cp1251
        response.encoding = response.apparent_encoding if response.encoding is None else response.encoding
        return response.text.replace('"', '').strip()
    except Exception as e:
        st.error(f"Ошибка связи: {e}")
        return None

def get_data(token):
    url = f"{BASE_URL}reports/olap?access_token={token}"
    
    # Расширенный запрос: Выручка и количество чеков
    payload = {
        "reportType": "SALES",
        "buildSummary": "false",
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
        res = requests.post(url, json=payload, timeout=20)
        # Важно: проверяем, что ответ не пустой
        if res.status_code == 200 and res.text:
            raw_data = res.json()
            if 'data' in raw_data and raw_data['data']:
                df = pd.DataFrame(raw_data['data'])
                df.columns = ['Дата', 'Выручка', 'Чеки']
                df['Дата'] = pd.to_datetime(df['Дата']).dt.date
                return df
            else:
                st.warning("Сервер iiko вернул пустой отчет (данных за неделю нет).")
                return None
        else:
            st.error(f"Сервер iiko ответил кодом {res.status_code}")
            return None
    except Exception as e:
        st.error(f"Ошибка обработки данных: {e}")
        return None

# --- ИНТЕРФЕЙС ---
st.title("📊 Zahratun Jondor: Оперативный отчет")

if st.sidebar.button("🔄 Обновить данные iiko"):
    with st.spinner('Связываюсь с сервером Zahratun...'):
        token = get_token()
        if token:
            df = get_data(token)
            if df is not None:
                st.success("Данные успешно получены!")
                
                # Метрики
                c1, c2, c3 = st.columns(3)
                total_rev = df['Выручка'].sum()
                total_checks = df['Чеки'].sum()
                c1.metric("Выручка (7д)", f"{total_rev:,.0f} сум")
                c2.metric("Чеков", f"{total_checks}")
                c3.metric("Средний чек", f"{(total_rev/total_checks if total_checks > 0 else 0):,.0f}")
                
                # График
                fig = px.bar(df, x='Дата', y='Выручка', color='Выручка', title="Продажи по дням")
                st.plotly_chart(fig, use_container_width=True)
                
                st.dataframe(df, use_container_width=True)
        else:
            st.error("Авторизация не удалась. Проверьте ключ API.")
else:
    st.info("Нажмите кнопку в меню слева для загрузки данных.")

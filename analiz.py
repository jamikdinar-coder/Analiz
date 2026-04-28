import streamlit as st
import pandas as pd
import plotly.express as px
import requests
from datetime import datetime, timedelta

# Твои данные из скриншотов
API_SECRET = "$4.4$1e90022d47b1211e828b665475bc72b3eb1a84eb"
BASE_URL = "https://zahratun-jondor.iiko.it:443/resto/api"

st.set_page_config(page_title="Zahratun Jondor Analytics", layout="wide")

def get_token():
    """Получение токена авторизации"""
    url = f"{BASE_URL}/auth/access_token?apiSecret={API_SECRET}"
    try:
        response = requests.get(url, timeout=15)
        response.encoding = 'cp1251'
        token = response.text.replace('"', '').strip()
        return token
    except Exception as e:
        st.error(f"Ошибка входа: {e}")
        return None

def get_olap_data(token):
    """Запрос данных по продажам с исправленным параметром 'key'"""
    url = f"{BASE_URL}/reports/olap"
    
    date_to = datetime.now().strftime("%Y-%m-%d")
    date_from = (datetime.now() - timedelta(days=7)).strftime("%Y-%m-%d")
    
    # ИСПРАВЛЕНИЕ: меняем 'access_token' на 'key', как просит сервер
    params = {
        "key": token, 
        "reportType": "SALES",
        "groupByRowFields": "Date.Typed",
        "aggregateFields": "DishCostAfterDiscount.Sum,UniqTransId.Count",
        "from": date_from,
        "to": date_to
    }
    
    try:
        res = requests.get(url, params=params, timeout=25)
        
        if res.status_code == 200:
            data = res.json()
            if 'data' in data and data['data']:
                df = pd.DataFrame(data['data'])
                df.columns = ['Дата', 'Выручка', 'Чеки']
                df['Дата'] = pd.to_datetime(df['Дата']).dt.date
                return df
            else:
                return "EMPTY"
        
        st.error(f"Ошибка сервера ({res.status_code}): {res.text[:150]}")
        return None
    except Exception as e:
        st.error(f"Ошибка обработки: {e}")
        return None

# --- ГЛАВНЫЙ ИНТЕРФЕЙС ---
st.title("📊 Zahratun Jondor: Оперативный отчет")

if st.sidebar.button("🔄 Обновить данные iiko"):
    with st.spinner('Синхронизация с Zahratun Jondor...'):
        token = get_token()
        if token:
            result = get_olap_data(token)
            
            if isinstance(result, pd.DataFrame):
                st.success("Данные успешно загружены!")
                
                # Метрики
                c1, c2, c3 = st.columns(3)
                total_rev = result['Выручка'].sum()
                total_checks = result['Чеки'].sum()
                c1.metric("Выручка (7 дн)", f"{total_rev:,.0f} сум")
                c2.metric("Чеков", f"{total_checks}")
                c3.metric("Средний чек", f"{(total_rev/total_checks if total_checks > 0 else 0):,.0f} сум")
                
                # График
                fig = px.area(result, x='Дата', y='Выручка', markers=True, title="Выручка по дням")
                st.plotly_chart(fig, use_container_width=True)
                
                st.dataframe(result, use_container_width=True)
            elif result == "EMPTY":
                st.warning("Сервер подключен, но за последние 7 дней данных о продажах не найдено.")
        else:
            st.error("Не удалось получить ключ доступа.")
else:
    st.info("Нажмите кнопку 'Обновить данные' для загрузки из iiko.")

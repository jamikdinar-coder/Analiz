import streamlit as st
import pandas as pd
import plotly.express as px
import requests
import json
from datetime import datetime, timedelta

# --- КОНФИГУРАЦИЯ ---
API_SECRET = "$4.4$1e90022d47b1211e828b665475bc72b3eb1a84eb"
# Исправленный адрес сервера (без лишних слешей)
BASE_URL = "https://zahratun-jondor.iiko.it:443/resto/api"

st.set_page_config(page_title="Zahratun Jondor Analytics", layout="wide")

def get_token():
    """Получение токена авторизации"""
    url = f"{BASE_URL}/auth/access_token?apiSecret={API_SECRET}"
    try:
        response = requests.get(url, timeout=15)
        response.encoding = 'cp1251'
        return response.text.replace('"', '').strip()
    except Exception as e:
        st.error(f"Ошибка входа: {e}")
        return None

def get_olap_data(token):
    """Запрос данных по продажам"""
    # Для v.9 пробуем передать параметры через URL (Query Params), так как POST дает 405
    url = f"{BASE_URL}/reports/olap"
    
    # Определяем даты
    date_to = datetime.now().strftime("%Y-%m-%d")
    date_from = (datetime.now() - timedelta(days=7)).strftime("%Y-%m-%d")
    
    params = {
        "access_token": token,
        "reportType": "SALES",
        "groupByRowFields": "Date.Typed",
        "aggregateFields": "DishCostAfterDiscount.Sum,UniqTransId.Count",
        "from": date_from,
        "to": date_to
    }
    
    try:
        # Пробуем GET запрос, так как POST был отклонен сервером
        res = requests.get(url, params=params, timeout=25)
        
        if res.status_code == 200:
            data = res.json()
            if 'data' in data:
                df = pd.DataFrame(data['data'])
                df.columns = ['Дата', 'Выручка', 'Чеки']
                df['Дата'] = pd.to_datetime(df['Дата']).dt.date
                return df
        
        # Если GET не сработал, выводим что сказал сервер для отладки
        st.error(f"Ошибка сервера ({res.status_code}): {res.text[:150]}")
        return None
    except Exception as e:
        st.error(f"Ошибка обработки: {e}")
        return None

# --- ГЛАВНЫЙ ИНТЕРФЕЙС ---
st.title("📊 Zahratun Jondor: Оперативный отчет")

if st.sidebar.button("🔄 Обновить данные iiko"):
    with st.spinner('Запрашиваю данные у iiko...'):
        token = get_token()
        if token:
            df = get_olap_data(token)
            if df is not None and not df.empty:
                st.success("Данные успешно синхронизированы!")
                
                # Метрики
                c1, c2, c3 = st.columns(3)
                total_rev = df['Выручка'].sum()
                total_checks = df['Чеки'].sum()
                c1.metric("Выручка (7 дн)", f"{total_rev:,.0f} сум")
                c2.metric("Всего чеков", f"{total_checks}")
                c3.metric("Средний чек", f"{(total_rev/total_checks if total_checks > 0 else 0):,.0f} сум")
                
                # График
                fig = px.line(df, x='Дата', y='Выручка', markers=True, 
                             line_shape='spline', title="Динамика продаж")
                st.plotly_chart(fig, use_container_width=True)
                
                # Таблица
                st.dataframe(df, use_container_width=True)
            else:
                st.info("Данных за выбранный период не найдено.")
        else:
            st.error("Не удалось получить доступ к серверу.")
else:
    st.info("Нажмите кнопку 'Обновить данные' для старта.")

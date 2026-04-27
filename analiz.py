import streamlit as st
import pandas as pd
import plotly.express as px
import requests
from datetime import datetime, timedelta

# --- 1. НАСТРОЙКИ ПОДКЛЮЧЕНИЯ (из твоих данных) ---
API_SECRET = "$4.4$1e90022d47b1211e828b665475bc72b3eb1a84eb"
# Правильный адрес сервера из твоего скриншота
BASE_URL = "https://zahratun-jondor.iiko.it:443/resto/api/" 

st.set_page_config(page_title="Zahratun Analytics", layout="wide")

# --- 2. ФУНКЦИИ ДЛЯ РАБОТЫ С API ---

def get_access_token():
    """Получение токена с исправлением ошибки кодировки UTF-8"""
    url = f"{BASE_URL}auth/access_token?apiSecret={API_SECRET}"
    try:
        response = requests.get(url, timeout=10)
        # Принудительно ставим кодировку cp1251, чтобы не было ошибки декодирования
        response.encoding = 'cp1251' 
        token = response.text.replace('"', '').strip()
        return token
    except Exception as e:
        st.error(f"Ошибка подключения к серверу: {e}")
        return None

def get_sales_report(token):
    """Запрос реальных продаж через OLAP-отчет"""
    url = f"{BASE_URL}reports/olap?access_token={token}"
    
    # Запрашиваем данные за последние 7 дней
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
        data = res.json()
        
        # Обработка данных в таблицу
        df = pd.DataFrame(data['data'])
        df.columns = ['Дата', 'Выручка', 'Чеки']
        df['Дата'] = pd.to_datetime(df['Дата']).dt.date
        return df
    except Exception as e:
        st.error(f"Ошибка получения данных: {e}")
        return None

# --- 3. ИНТЕРФЕЙС САЙТА ---

st.title("📊 Zahratun Jondor: Панель Управления")
st.markdown("---")

# Боковая панель
with st.sidebar:
    st.header("Настройки")
    btn_update = st.button("🔄 Обновить данные из iiko")
    st.info(f"Версия iiko: v.9\nID: 5930393")

if btn_update:
    with st.spinner('Синхронизация с сервером...'):
        token = get_access_token()
        
        if token:
            df = get_sales_report(token)
            
            if df is not None and not df.empty:
                # Расчет KPI
                total_rev = df['Выручка'].sum()
                total_checks = df['Чеки'].sum()
                avg_check = total_rev / total_checks if total_checks > 0 else 0
                
                # Вывод метрик
                c1, c2, c3 = st.columns(3)
                c1.metric("Выручка (7 дн)", f"{total_rev:,.0f} сум")
                c2.metric("Чеков за неделю", f"{total_checks}")
                c3.metric("Средний чек", f"{avg_check:,.0f} сум")
                
                # График выручки
                st.subheader("Динамика продаж")
                fig = px.area(df, x='Дата', y='Выручка', 
                             title="Выручка по дням",
                             line_shape='spline',
                             color_discrete_sequence=['#00CC96'])
                st.plotly_chart(fig, use_container_width=True)
                
                # Таблица данных
                with st.expander("Посмотреть таблицу данных"):
                    st.dataframe(df.sort_values('Дата', ascending=False), use_container_width=True)
            else:
                st.warning("Сервер ответил успешно, но данных за этот период нет.")
        else:
            st.error("Не удалось авторизоваться. Проверьте статус сервера iiko.")

else:
    # Состояние покоя
    st.image("https://ru.iiko.help/download/attachments/70549591/image2019-11-20_12-28-21.png", width=100)
    st.write("Нажмите кнопку **Обновить данные**, чтобы получить актуальную информацию из iikoCloud.")

st.markdown("---")
st.caption(f"Zahratun Analytics v2.0 | Последняя проверка: {datetime.now().strftime('%H:%M:%S')}")

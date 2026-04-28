import streamlit as st
import pandas as pd
import plotly.express as px
import requests
from datetime import datetime, timedelta
import urllib3

# Отключаем проверку SSL (для локальных и самоподписанных сертификатов iiko)
urllib3.disable_warnings(urllib3.exceptions.InsecureRequestWarning)

# --- ДАННЫЕ ПОДКЛЮЧЕНИЯ ---
API_SECRET = "$4.4$1e90022d47b1211e828b665475bc72b3eb1a84eb"
SERVER = "zahratun-jondor.iiko.it"

st.set_page_config(page_title="Zahratun Jondor Analytics", layout="wide")

def get_session():
    """
    Авторизация и получение сессии. 
    Используем requests.Session(), чтобы куки (cookie key) сохранялись автоматически.
    """
    session = requests.Session()
    # Пробуем порты: 443 (стандарт), 8080 (iiko), 443 (http)
    variants = [
        f"https://{SERVER}/resto/api/auth/access_token?apiSecret={API_SECRET}",
        f"http://{SERVER}:8080/resto/api/auth/access_token?apiSecret={API_SECRET}",
        f"https://{SERVER}:8080/resto/api/auth/access_token?apiSecret={API_SECRET}"
    ]
    
    for url in variants:
        try:
            res = session.get(url, timeout=10, verify=False)
            if res.status_code == 200:
                token = res.text.replace('"', '').strip()
                return session, token
        except Exception:
            continue
    return None, None

def get_report_data(session, token):
    """Получение OLAP-отчета"""
    # Базовый URL определяем по тому, как прошла авторизация (в данном примере берем https)
    url = f"https://{SERVER}/resto/api/reports/olap"
    
    params = {
        "key": token, # Токен в строке запроса
        "reportType": "SALES",
        "groupByRowFields": "Date.Typed",
        "aggregateFields": "DishCostAfterDiscount.Sum,UniqTransId.Count",
        "from": (datetime.now() - timedelta(days=7)).strftime("%Y-%m-%d"),
        "to": datetime.now().strftime("%Y-%m-%d")
    }
    
    try:
        # Передаем сессию, которая уже содержит куки авторизации
        res = session.get(url, params=params, verify=False, timeout=20)
        if res.status_code == 200:
            # Если сервер прислал XML (стандартно для iiko), пытаемся прочитать как JSON
            try:
                data = res.json()
                if 'data' in data:
                    df = pd.DataFrame(data['data'])
                    df.columns = ['Дата', 'Выручка', 'Чеки']
                    df['Дата'] = pd.to_datetime(df['Дата']).dt.date
                    return df
            except:
                st.error("Сервер прислал данные в формате XML вместо JSON. Нужно настроить заголовки.")
    except Exception as e:
        st.error(f"Ошибка при получении отчета: {e}")
    return None

# --- ИНТЕРФЕЙС ---
st.title("📊 Zahratun Jondor Analytics")

if st.sidebar.button("🔄 Синхронизировать"):
    with st.spinner("Подключение к серверу..."):
        session, token = get_session()
        
        if token:
            st.sidebar.success("Авторизация успешна!")
            df = get_report_data(session, token)
            
            if df is not None:
                st.metric("Выручка за неделю", f"{df['Выручка'].sum():,.0f} сум")
                st.plotly_chart(px.bar(df, x='Дата', y='Выручка'))
                st.dataframe(df)
                
                # Логаут в конце сессии (как в вашей документации)
                logout_url = f"https://{SERVER}/resto/api/logout?key={token}"
                session.get(logout_url, verify=False)
        else:
            st.error("❌ Сбой подключения.")
            st.info("""
            **Почему это не работает прямо сейчас?**
            Браузер и код получают отказ (Connection Refused). 
            1. Порт 8080 на сервере zahratun-jondor.iiko.it закрыт.
            2. Сервер не принимает запросы с вашего текущего IP.
            
            **Решение:** Покажите ваш скриншот с ошибкой «Connection Refused» техподдержке iiko. 
            Они должны «пробросить порт» или добавить ваш IP в список разрешенных.
            """)

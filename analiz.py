import streamlit as st
import pandas as pd
import plotly.express as px
import requests
from datetime import datetime, timedelta
import urllib3

# Отключаем проверку SSL
urllib3.disable_warnings(urllib3.exceptions.InsecureRequestWarning)

# --- ДАННЫЕ ПОДКЛЮЧЕНИЯ ---
SERVER = "zahratun-jondor.iiko.it"
USER_LOGIN = "jamshid"
USER_PASS = "02051987"

st.set_page_config(page_title="Zahratun Jondor Analytics", layout="wide")

def get_auth_token():
    """
    Авторизация через логин и пароль (классический API iiko).
    """
    # Пробуем разные варианты URL, так как сервер может быть настроен по-разному
    urls = [
        f"https://{SERVER}/resto/api/auth/login?login={USER_LOGIN}&pass={USER_PASS}",
        f"http://{SERVER}:8080/resto/api/auth/login?login={USER_LOGIN}&pass={USER_PASS}"
    ]
    
    session = requests.Session()
    for url in urls:
        try:
            res = session.get(url, timeout=10, verify=False)
            if res.status_code == 200:
                # iiko возвращает токен в виде простой строки
                token = res.text.replace('"', '').strip()
                return session, token, url.split('/resto')[0]
        except Exception:
            continue
    return None, None, None

def get_sales_data(session, token, base_url):
    """Запрос OLAP отчета по продажам"""
    url = f"{base_url}/resto/api/reports/olap"
    
    params = {
        "key": token,
        "reportType": "SALES",
        "groupByRowFields": "Date.Typed",
        "aggregateFields": "DishCostAfterDiscount.Sum,UniqTransId.Count",
        "from": (datetime.now() - timedelta(days=7)).strftime("%Y-%m-%d"),
        "to": datetime.now().strftime("%Y-%m-%d")
    }
    
    try:
        # Указываем, что хотим получить JSON
        res = session.get(url, params=params, headers={"Accept": "application/json"}, verify=False)
        if res.status_code == 200:
            data = res.json()
            if 'data' in data:
                df = pd.DataFrame(data['data'])
                df.columns = ['Дата', 'Выручка', 'Чеки']
                df['Дата'] = pd.to_datetime(df['Дата']).dt.date
                return df
    except Exception as e:
        st.error(f"Ошибка получения данных: {e}")
    return None

# --- ИНТЕРФЕЙС ---
st.title("📊 Zahratun Jondor: Оперативная аналитика")

if st.sidebar.button("🔄 Обновить отчет"):
    with st.spinner("Авторизация сотрудника..."):
        session, token, base_url = get_auth_token()
        
        if token:
            st.sidebar.success(f"Вход выполнен: {USER_LOGIN}")
            df = get_sales_data(session, token, base_url)
            
            if df is not None:
                # Отображение результатов
                col1, col2 = st.columns(2)
                col1.metric("Выручка (неделя)", f"{df['Выручка'].sum():,.0f} сум")
                col2.metric("Кол-во чеков", f"{df['Чеки'].sum()}")
                
                st.plotly_chart(px.bar(df, x='Дата', y='Выручка', title="Продажи по дням"))
                st.dataframe(df, use_container_width=True)
                
                # Завершение сессии (Logout)
                session.get(f"{base_url}/resto/api/auth/logout?key={token}", verify=False)
        else:
            st.error("❌ Ошибка подключения.")
            st.warning("Сервер по-прежнему сбрасывает соединение (Connection Refused).")
            st.info("Пожалуйста, убедитесь, что в iikoOffice у пользователя 'jamshid' стоит галочка 'Разрешить вход в iikoFront/iikoOffice' и есть права на работу с API.")

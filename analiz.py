import streamlit as st
import pandas as pd
import plotly.express as px
import requests
from datetime import datetime, timedelta
import urllib3

# Отключаем проверку SSL
urllib3.disable_warnings(urllib3.exceptions.InsecureRequestWarning)

# --- ДАННЫЕ ИЗ ВАШЕЙ ЛИЦЕНЗИИ ---
API_SECRET = "$4.4$1e90022d47b1211e828b665475bc72b3eb1a84eb"
SERVER = "zahratun-jondor.iiko.it"
ORG_ID = "5930393" # Из вашей лицензии

st.set_page_config(page_title="Zahratun Jondor Analytics", layout="wide")

def get_auth():
    """Пробуем авторизоваться и получить токен"""
    session = requests.Session()
    # Список адресов для проверки (стандартный и порт 8080)
    urls = [
        f"https://{SERVER}/resto/api/auth/access_token?apiSecret={API_SECRET}",
        f"https://{SERVER}:8080/resto/api/auth/access_token?apiSecret={API_SECRET}"
    ]
    
    for url in urls:
        try:
            res = session.get(url, timeout=10, verify=False)
            if res.status_code == 200:
                token = res.text.replace('"', '').strip()
                return session, token, url.replace("/auth/access_token", "")
        except:
            continue
    return None, None, None

def get_sales_report(session, token, base_url):
    """Запрос данных о продажах"""
    report_url = f"{base_url}/reports/olap"
    
    # Параметры для iiko v.9
    params = {
        "key": token,
        "reportType": "SALES",
        "groupByRowFields": "Date.Typed",
        "aggregateFields": "DishCostAfterDiscount.Sum,UniqTransId.Count",
        "from": (datetime.now() - timedelta(days=7)).strftime("%Y-%m-%d"),
        "to": datetime.now().strftime("%Y-%m-%d")
    }
    
    try:
        # Важно: добавляем заголовок для JSON
        res = session.get(report_url, params=params, headers={"Accept": "application/json"}, verify=False)
        if res.status_code == 200:
            data = res.json()
            if 'data' in data:
                df = pd.DataFrame(data['data'])
                df.columns = ['Дата', 'Выручка', 'Чеки']
                df['Дата'] = pd.to_datetime(df['Дата']).dt.date
                return df
        else:
            st.error(f"Ошибка отчета: {res.status_code}")
    except Exception as e:
        st.error(f"Ошибка запроса: {e}")
    return None

# --- ИНТЕРФЕЙС ---
st.title(f"📊 Аналитика: Zahratun Jondor (ID {ORG_ID})")

if st.sidebar.button("🔄 Обновить данные"):
    with st.spinner("Авторизация..."):
        session, token, base_url = get_auth()
        
        if token:
            st.sidebar.success("✅ Подключено!")
            df = get_sales_report(session, token, base_url)
            
            if df is not None:
                # Метрики
                c1, c2 = st.columns(2)
                c1.metric("Выручка (7 дн)", f"{df['Выручка'].sum():,.0f} сум")
                c2.metric("Чеков (7 дн)", f"{df['Чеки'].sum()}")
                
                # График
                st.plotly_chart(px.line(df, x='Дата', y='Выручка', title="Тренд выручки"))
                st.dataframe(df, use_container_width=True)
                
                # Выход (как просили в документации)
                session.get(f"{base_url}/auth/logout?key={token}", verify=False)
        else:
            st.error("❌ Сервер iiko сбрасывает соединение.")
            st.warning("Лицензия API у вас есть, но порт 8080/443 закрыт сетевым экраном iikoCloud.")

import streamlit as st
import pandas as pd
import plotly.express as px
import requests
from datetime import datetime, timedelta
import urllib3

urllib3.disable_warnings(urllib3.exceptions.InsecureRequestWarning)

# Рекомендую вынести это в st.secrets
SERVER = "zahratun-jondor.iiko.it"
USER_LOGIN = st.secrets.get("USER_LOGIN", "jamshid") 
USER_PASS = st.secrets.get("USER_PASS", "02051987")

def get_iiko_session():
    session = requests.Session()
    # Список портов для проверки: 443 (https), 8080 (http)
    urls = [
        f"https://{SERVER}/resto/api/auth/login",
        f"http://{SERVER}:8080/resto/api/auth/login"
    ]
    
    for url in urls:
        try:
            # Передаем параметры через params для чистоты URL
            response = session.get(url, params={'login': USER_LOGIN, 'pass': USER_PASS}, timeout=7, verify=False)
            if response.status_code == 200:
                token = response.text.replace('"', '').strip()
                base_url = url.split('/resto')[0]
                return session, token, base_url
        except Exception:
            continue
    return None, None, None

def fetch_sales(session, token, base_url):
    report_url = f"{base_url}/resto/api/reports/olap"
    
    # Параметры для iiko OLAP
    params = {
        "key": token,
        "reportType": "SALES",
        "groupByRowFields": "Date.Typed",
        "aggregateFields": "DishCostAfterDiscount.Sum,UniqTransId.Count",
        "from": (datetime.now() - timedelta(days=7)).strftime("%Y-%m-%d"),
        "to": datetime.now().strftime("%Y-%m-%d")
    }
    
    try:
        # Явно просим JSON
        res = session.get(report_url, params=params, headers={"Accept": "application/json"}, verify=False)
        if res.status_code == 200:
            raw_data = res.json()
            # Проверка наличия данных в ответе
            if 'data' in raw_data:
                df = pd.DataFrame(raw_data['data'])
                # В iiko порядок колонок соответствует порядку в aggregateFields
                df.columns = ['Дата', 'Выручка', 'Чеки']
                df['Дата'] = pd.to_datetime(df['Дата']).dt.date
                return df
            else:
                st.warning("Сервер вернул пустой отчет.")
        else:
            st.error(f"Ошибка API: {res.status_code}")
    except Exception as e:
        st.error(f"Ошибка обработки данных: {e}")
    return None

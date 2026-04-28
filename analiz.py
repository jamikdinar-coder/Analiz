import streamlit as st
import pandas as pd
import plotly.express as px
import requests
from datetime import datetime, timedelta
import urllib3

# Отключаем предупреждения об SSL
urllib3.disable_warnings(urllib3.exceptions.InsecureRequestWarning)

# --- НАСТРОЙКИ ---
API_SECRET = "$4.4$1e90022d47b1211e828b665475bc72b3eb1a84eb"
SERVER = "zahratun-jondor.iiko.it"

st.set_page_config(page_title="Zahratun Jondor Analytics", layout="wide")

def get_token():
    # Проверяем два самых частых варианта подключения
    urls = [
        f"https://{SERVER}/resto/api/auth/access_token?apiSecret={API_SECRET}",
        f"https://{SERVER}:8080/resto/api/auth/access_token?apiSecret={API_SECRET}"
    ]
    
    last_error = ""
    for url in urls:
        try:
            res = requests.get(url, timeout=10, verify=False)
            if res.status_code == 200:
                return res.text.replace('"', '').strip()
            else:
                last_error = f"Порт {url.split(':')[-1].split('/')[0] if ':' in url else '443'}: {res.status_code} ({res.text})"
        except Exception as e:
            last_error = f"Ошибка подключения: {str(e)}"
    
    st.error(f"❌ Ошибка авторизации: {last_error}")
    return None

def get_data(token):
    # Пытаемся найти работающий базовый URL
    base_urls = [f"https://{SERVER}", f"https://{SERVER}:8080"]
    
    headers = {"Accept": "application/json"}
    params = {
        "key": token,
        "reportType": "SALES",
        "groupByRowFields": "Date.Typed",
        "aggregateFields": "DishCostAfterDiscount.Sum,UniqTransId.Count",
        "from": (datetime.now() - timedelta(days=7)).strftime("%Y-%m-%d"),
        "to": datetime.now().strftime("%Y-%m-%d")
    }

    for base in base_urls:
        try:
            url = f"{base}/resto/api/reports/olap"
            res = requests.get(url, params=params, headers=headers, timeout=20, verify=False)
            if res.status_code == 200:
                data = res.json()
                if 'data' in data:
                    df = pd.DataFrame(data['data'])
                    df.columns = ['Дата', 'Выручка', 'Чеки']
                    df['Дата'] = pd.to_datetime(df['Дата']).dt.date
                    return df
        except:
            continue
    return None

# --- ИНТЕРФЕЙС ---
st.title("📊 Zahratun Jondor: Аналитика")

# Используем session_state, чтобы данные не исчезали при нажатии кнопок
if 'data_frame' not in st.session_state:
    st.session_state['data_frame'] = None

with st.sidebar:
    st.header("Управление")
    if st.button("🔄 Обновить данные"):
        with st.spinner("Связываюсь с iiko..."):
            token = get_token()
            if token:
                df = get_data(token)
                if df is not None:
                    st.session_state['data_frame'] = df
                    st.success("Данные успешно получены!")

# Отображение данных
df = st.session_state['data_frame']

if df is not None:
    # Метрики
    col1, col2, col3 = st.columns(3)
    total_rev = df['Выручка'].sum()
    total_checks = df['Чеки'].sum()
    avg_check = total_rev / total_checks if total_checks > 0 else 0

    col1.metric("Выручка за 7 дней", f"{total_rev:,.0f} сум")
    col2.metric("Всего чеков", f"{total_checks}")
    col3.metric("Средний чек", f"{avg_check:,.0f} сум")

    # График
    st.subheader("График выручки по дням")
    fig = px.bar(df, x='Дата', y='Выручка', color='Выручка', 
                 labels={'Выручка': 'Сумма (сум)', 'Дата': 'День'},
                 template="plotly_white")
    st.plotly_chart(fig, use_container_width=True)

    # Таблица
    st.subheader("Детальные данные")
    st.dataframe(df, use_container_width=True)
else:
    st.info("Нажмите кнопку 'Обновить данные' в боковом меню, чтобы загрузить отчет.")
    st.warning("⚠️ Если авторизация не проходит: проверьте, открыт ли порт 8080 на вашем сервере iiko.")

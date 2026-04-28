import streamlit as st
import pandas as pd
import plotly.express as px
import requests
from datetime import datetime, timedelta
import urllib3

# Отключаем предупреждения о небезопасном соединении (так как сервер iiko локальный)
urllib3.disable_warnings(urllib3.exceptions.InsecureRequestWarning)

# Твои данные
API_SECRET = "$4.4$1e90022d47b1211e828b665475bc72b3eb1a84eb"
SERVER = "zahratun-jondor.iiko.it"

st.set_page_config(page_title="Zahratun Analytics", layout="wide")

def get_token():
    # Пробуем варианты с портом и без, отключая проверку SSL
    urls = [
        f"https://{SERVER}/resto/api/auth/access_token?apiSecret={API_SECRET}",
        f"https://{SERVER}:443/resto/api/auth/access_token?apiSecret={API_SECRET}"
    ]
    for url in urls:
        try:
            # verify=False игнорирует проблемы с сертификатом сервера
            res = requests.get(url, timeout=10, verify=False)
            if res.status_code == 200:
                return res.text.replace('"', '').strip()
        except:
            continue
    return None

def get_data(token):
    url = f"https://{SERVER}/resto/api/reports/olap"
    params = {
        "key": token,
        "reportType": "SALES",
        "groupByRowFields": "Date.Typed",
        "aggregateFields": "DishCostAfterDiscount.Sum,UniqTransId.Count",
        "from": (datetime.now() - timedelta(days=7)).strftime("%Y-%m-%d"),
        "to": datetime.now().strftime("%Y-%m-%d")
    }
    try:
        res = requests.get(url, params=params, timeout=20, verify=False)
        if res.status_code == 200:
            raw = res.json()
            if 'data' in raw and raw['data']:
                df = pd.DataFrame(raw['data'])
                df.columns = ['Дата', 'Выручка', 'Чеки']
                df['Дата'] = pd.to_datetime(df['Дата']).dt.date
                return df
        st.error(f"Сервер ответил ({res.status_code}): {res.text[:100]}")
    except Exception as e:
        st.error(f"Ошибка отчета: {e}")
    return None

# --- ИНТЕРФЕЙС ---
st.title("📊 Zahratun Jondor: Live Analytics")

if st.sidebar.button("🔄 Обновить из iiko"):
    with st.spinner('Пробиваюсь к серверу в Жондоре...'):
        token = get_token()
        if token:
            df = get_data(token)
            if df is not None:
                st.success("✅ Соединение установлено!")
                c1, c2 = st.columns(2)
                c1.metric("Выручка (7д)", f"{df['Выручка'].sum():,.0f} сум")
                c2.metric("Чеков", f"{df['Чеки'].sum()}")
                st.plotly_chart(px.line(df, x='Дата', y='Выручка', markers=True))
                st.dataframe(df, use_container_width=True)
        else:
            st.error("❌ Сервер iiko недоступен. Проверь: запущен ли iikoServer и открыт ли порт 443 для внешних запросов.")
else:
    st.info("Нажмите кнопку для загрузки данных.")

import streamlit as st
import pandas as pd
import plotly.express as px
import requests
from datetime import datetime, timedelta

# --- КОНФИГУРАЦИЯ ---
API_SECRET = "$4.4$1e90022d47b1211e828b665475bc72b3eb1a84eb"
ORGANIZATION_ID = "5930393"
BASE_URL = "https://iiko.biz:9900/api/0/"

st.set_page_config(page_title="Zahratun Analytics Live", layout="wide")

# --- ФУНКЦИИ API ---
def get_access_token():
    """Получаем временный токен для работы"""
    url = f"{BASE_URL}auth/access_token?apiSecret={API_SECRET}"
    try:
        response = requests.get(url, timeout=10)
        return response.text.replace('"', '')
    except:
        return None

def get_real_sales(token):
    """Запрашиваем реальные продажи через OLAP"""
    url = f"{BASE_URL}reports/olap?access_token={token}"
    
    # Запрос данных за последнюю неделю
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
        res = requests.post(url, json=payload)
        data = res.json()
        # Превращаем ответ iiko в таблицу Pandas
        df = pd.DataFrame(data['data'])
        df.columns = ['Дата', 'Выручка', 'Чеки']
        df['Дата'] = pd.to_datetime(df['Дата']).dt.date
        return df
    except:
        return None

# --- ИНТЕРФЕЙС ---
st.title("?? Zahratun Jondor: Live Analytics")
st.sidebar.header("Управление")

if st.sidebar.button("Обновить данные из iiko"):
    token = get_access_token()
    if token:
        df_sales = get_real_sales(token)
        
        if df_sales is not None:
            st.success(f"Данные обновлены в {datetime.now().strftime('%H:%M:%S')}")
            
            # Основные KPI
            total_rev = df_sales['Выручка'].sum()
            total_checks = df_sales['Чеки'].sum()
            avg_check = total_rev / total_checks if total_checks > 0 else 0
            
            c1, c2, c3 = st.columns(3)
            c1.metric("Выручка (7 дн)", f"{total_rev:,.0f} сум")
            c2.metric("Всего чеков", f"{total_checks}")
            c3.metric("Средний чек", f"{avg_check:,.0f} сум")
            
            # График
            st.subheader("Динамика выручки")
            fig = px.line(df_sales, x='Дата', y='Выручка', markers=True, template="plotly_dark")
            st.plotly_chart(fig, use_container_width=True)
            
            # Таблица
            st.subheader("Детализация по дням")
            st.dataframe(df_sales, use_container_width=True)
        else:
            st.error("Не удалось получить данные. Проверьте права API в iikoOffice.")
    else:
        st.error("Ошибка авторизации. Проверьте Ключ API.")
else:
    st.info("Нажмите кнопку в меню слева, чтобы загрузить живые данные из iiko.")

st.markdown("---")
st.caption("Система синхронизирована с сервером Zahratun Jondor через iikoCloud API v.9")
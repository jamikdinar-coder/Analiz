import streamlit as st
import pandas as pd
import plotly.express as px          # ← ИСПРАВЛЕНИЕ 1: добавлен импорт
import requests
from datetime import datetime, timedelta
import urllib3
from typing import Optional, Tuple, Dict, Any

urllib3.disable_warnings(urllib3.exceptions.InsecureRequestWarning)

# ==================== КОНФИГУРАЦИЯ ====================
SERVER = "zahratun-jondor.iiko.it"

USER_LOGIN: str = st.secrets.get("USER_LOGIN", "jamshid")
USER_PASS: str = st.secrets.get("USER_PASS", "02051987")


# ====================== СЕССИЯ ======================
@st.cache_data(ttl=600, show_spinner=False)
def get_iiko_session() -> Optional[Tuple[requests.Session, str, str]]:
    session = requests.Session()
    urls = [
        f"https://{SERVER}/resto/api/auth/login",
        f"http://{SERVER}:8080/resto/api/auth/login",
    ]
    for url in urls:
        try:
            resp = session.get(
                url,
                params={"login": USER_LOGIN, "pass": USER_PASS},
                timeout=10,
                verify=False
            )
            if resp.status_code == 200:
                token = resp.text.strip().strip('"')
                if token and len(token) > 5:
                    base_url = url.split("/resto")[0]
                    return session, token, base_url
        except Exception:
            continue
    st.error("❌ Не удалось подключиться к iiko. Проверьте сервер и учётные данные.")
    return None


# ====================== ДАННЫЕ ======================
@st.cache_data(ttl=300, show_spinner="Загрузка данных из iiko...")
def fetch_sales(period_days: int = 7, force_refresh: bool = False) -> Optional[pd.DataFrame]:
    session_data = get_iiko_session()
    if not session_data:
        return None

    session, token, base_url = session_data
    today = datetime.now()

    # ИСПРАВЛЕНИЕ 2: date_to теперь всегда определён
    if period_days == 999:  # Этот месяц
        date_from = today.replace(day=1).strftime("%Y-%m-%d")
        date_to = today.strftime("%Y-%m-%d")
    elif period_days == 998:  # Прошлый месяц
        first_day_this_month = today.replace(day=1)
        date_from = (first_day_this_month - timedelta(days=1)).replace(day=1).strftime("%Y-%m-%d")
        date_to = (first_day_this_month - timedelta(days=1)).strftime("%Y-%m-%d")
    else:
        date_from = (today - timedelta(days=period_days)).strftime("%Y-%m-%d")
        date_to = today.strftime("%Y-%m-%d")

    params: Dict[str, Any] = {
        "key": token,
        "reportType": "SALES",
        "groupByRowFields": "OpenDate.Typed",
        "aggregateFields": "Sum,UniqOrderId.Count",
        "from": date_from,
        "to": date_to,
        "buildSummary": "false"
    }

    try:
        response = session.get(
            f"{base_url}/resto/api/reports/olap",
            params=params,
            headers={"Accept": "application/json"},
            timeout=15,
            verify=False
        )
        if response.status_code != 200:
            st.error(f"Ошибка API: {response.status_code}")
            return None

        raw = response.json()
        if not raw or "data" not in raw or not raw["data"]:
            st.warning("Нет данных за выбранный период.")
            return None

        df = pd.DataFrame(raw["data"])
        df.columns = ["Дата", "Выручка", "Чеки"]
        df["Дата"] = pd.to_datetime(df["Дата"]).dt.date
        df["Выручка"] = pd.to_numeric(df["Выручка"], errors="coerce").round(0)
        df["Чеки"] = pd.to_numeric(df["Чеки"], errors="coerce").astype("Int64")
        df["Средний чек"] = (df["Выручка"] / df["Чеки"]).round(0)
        df = df.sort_values("Дата").reset_index(drop=True)
        return df

    except Exception as e:
        st.error(f"Ошибка при получении данных: {e}")
        return None


# ====================== ИНТЕРФЕЙС ======================
st.set_page_config(page_title="Продажи — iiko", layout="wide")
st.title("📊 Анализ продаж из iiko")

with st.sidebar:
    st.header("Настройки отчёта")
    period_option = st.selectbox(
        "Выберите период:",
        options=[
            "Последние 7 дней",
            "Последние 14 дней",
            "Последние 30 дней",
            "Этот месяц",
            "Прошлый месяц"
        ],
        index=0
    )
    period_map = {
        "Последние 7 дней": 7,
        "Последние 14 дней": 14,
        "Последние 30 дней": 30,
        "Этот месяц": 999,
        "Прошлый месяц": 998
    }
    selected_days = period_map[period_option]
    if st.button("🔄 Обновить данные", type="primary"):
        st.cache_data.clear()
        st.rerun()

df = fetch_sales(period_days=selected_days)

if df is not None and not df.empty:
    col1, col2, col3, col4 = st.columns(4)
    with col1:
        st.metric("Общая выручка", f"{df['Выручка'].sum():,.0f} ₽")
    with col2:
        st.metric("Всего чеков", f"{df['Чеки'].sum():,}")
    with col3:
        st.metric("Средний чек", f"{df['Средний чек'].mean():,.0f} ₽")
    with col4:
        st.metric("Дней в отчёте", len(df))

    st.subheader("Динамика продаж")
    tab1, tab2 = st.tabs(["Выручка", "Чеки и средний чек"])
    with tab1:
        fig1 = px.bar(df, x="Дата", y="Выручка", title="Выручка по дням")
        st.plotly_chart(fig1, use_container_width=True)
    with tab2:
        fig2 = px.line(df, x="Дата", y=["Чеки", "Средний чек"],
                       title="Количество чеков и средний чек", markers=True)
        st.plotly_chart(fig2, use_container_width=True)

    st.subheader("Детальные данные")
    st.dataframe(
        df.style.format({"Выручка": "{:,.0f}", "Средний чек": "{:,.0f}"}),
        use_container_width=True,
        hide_index=True
    )
else:
    st.info("Загрузка данных... Если данные не появляются, нажмите кнопку «Обновить данные».")

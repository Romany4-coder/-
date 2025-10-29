import streamlit as st
import pandas as pd
import plotly.express as px
import os  # Для дебага пути.

# Загрузка данных.
@st.cache_data(ttl=3600)  # Кэш на 1 час, авто-очистка.
def load_data(file_name):
    if os.path.exists(file_name):
        print(f"Файл найден: {file_name}")  # Отладка в логах.
        df = pd.read_excel(file_name, sheet_name='Обработанные данные')
        df['Товар_код'] = df['Товар Наименование'].str.extract(r'^(\d+)').astype('Int64')
        return df
    else:
        st.error(f"Файл не найден: {file_name}. Проверьте загрузку в репозиторий.")
        return pd.DataFrame()  # Пустой DF, чтобы app не крашился.

# Конфиг.
st.set_page_config(page_title="Аналитика Оборачиваемости", layout="wide", initial_sidebar_state="expanded")
st.title("🚀 Дашборд: Оборачиваемость vs Таргеты по Месяцам")
st.markdown("---")

# Загрузка (новое имя файла).
file_path = 'Processed_Data.xlsx'  # Английское имя — фикс кодировки.
df_data = load_data(file_path)
if df_data.empty:
    st.stop()  # Остановить, если файл не найден.

# Sidebar.
st.sidebar.header("🔍 Фильтры")
categories = st.sidebar.multiselect("Категория", options=sorted(df_data['Категория'].dropna().unique()), default=sorted(df_data['Категория'].dropna().unique()))
months = st.sidebar.multiselect("Месяц", options=sorted(df_data['Месяц'].unique()), default=sorted(df_data['Месяц'].unique()))
product_codes = st.sidebar.multiselect("Код Товара", options=sorted(df_data['Товар_код'].dropna().unique()), default=[])
product_names = st.sidebar.selectbox("Наименование Товара", options=['Все'] + sorted(df_data['Товар Наименование'].unique().tolist()))

# Фильтрация.
filtered_data = df_data[
    (df_data['Категория'].isin(categories)) &
    (df_data['Месяц'].isin(months)) &
    (df_data['Товар_код'].isin(product_codes) if product_codes else True) &
    (df_data['Категория'].notna())
]
if product_names != 'Все':
    filtered_data = filtered_data[filtered_data['Товар Наименование'] == product_names]

# Pivot (агрегация).
if not filtered_data.empty:
    pivot_filtered = pd.pivot_table(
        filtered_data,
        values=['Оборачиваемость', 'VPO Target', 'VPO min Target'],
        index=['Категория', 'Товар_код', 'Товар Наименование', 'Месяц'],
        aggfunc={'Оборачиваемость': 'mean', 'VPO Target': 'first', 'VPO min Target': 'first'},
        fill_value=0
    ).round(2).reset_index()
else:
    pivot_filtered = pd.DataFrame()

# Таблица.
col1, col2 = st.columns([2, 1])
with col1:
    st.subheader("📊 Агрегированная Таблица (1 строка на товар-месяц)")
    if not pivot_filtered.empty:
        st.dataframe(pivot_filtered[['Категория', 'Товар_код', 'Товар Наименование', 'Месяц', 'Оборачиваемость', 
                                    'VPO Target', 'VPO min Target']], use_container_width=True)
    else:
        st.info("Нет данных по фильтрам.")

# График 1.
with col2:
    st.subheader("📈 Оборачиваемость vs Таргеты")
    if not pivot_filtered.empty:
        plot_data = pivot_filtered.melt(id_vars=['Категория', 'Товар_код', 'Товар Наименование', 'Месяц'], 
                                        value_vars=['Оборачиваемость', 'VPO Target', 'VPO min Target'],
                                        var_name='Метрика', value_name='Значение')
        fig1 = px.line(plot_data, x='Месяц', y='Значение', color='Метрика', title="Динамика по Месяцам", markers=True,
                       color_discrete_map={'Оборачиваемость': 'blue', 'VPO Target': 'green', 'VPO min Target': 'orange'})
        fig1.update_xaxes(title="Месяц")
        fig1.update_yaxes(title="Значение")
        st.plotly_chart(fig1, use_container_width=True)
    else:
        st.info("Нет данных для графика.")

# График 2.
st.subheader("🎯 % Достижения Таргета")
if not pivot_filtered.empty and pivot_filtered['VPO Target'].sum() > 0:
    perf_pivot = pivot_filtered.copy()
    perf_pivot['% Достижения'] = (perf_pivot['Оборачиваемость'] / perf_pivot['VPO Target'] * 100).round(1)
    fig2 = px.bar(perf_pivot, x='Месяц', y='% Достижения', color='% Достижения', title="Достижение Таргета (%)",
                  color_continuous_scale=['red', 'yellow', 'green'], hover_data=['Категория', 'Товар Наименование'])
    fig2.update_yaxes(title="% Достижения", range=[0, 200])
    st.plotly_chart(fig2, use_container_width=True)
else:
    st.warning("Нет данных для %.")

# Инсайты.
st.subheader("📋 Ключевые Инсайты")
if not pivot_filtered.empty:
    avg_turnover = pivot_filtered['Оборачиваемость'].mean().round(2)
    avg_target = pivot_filtered['VPO Target'].mean().round(2)
    achievement = (avg_turnover / avg_target * 100).round(1) if avg_target > 0 else 0
    col1, col2, col3 = st.columns(3)
    col1.metric("Средняя Оборачиваемость", f"{avg_turnover}")
    col2.metric("Средний Таргет", f"{avg_target}")
    col3.metric("Среднее Достижение", f"{achievement}%", delta=f"{achievement - 100:+.1f}%")
else:
    st.info("Выберите фильтры.")

# Футер.
st.markdown("---")
st.caption("💡 Дашборд на Streamlit + Plotly. Фильтры в реальном времени. Фикс: Английское имя файла.")

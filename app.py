import streamlit as st
import pandas as pd
import plotly.express as px
import plotly.graph_objects as go

# Загрузка данных (только лист "Обработанные данные" — robust, без pivot-листа).
@st.cache_data  # Кэш для скорости — перезагружается при изменении файла.
def load_data(file_path):
    df = pd.read_excel(file_path, sheet_name='Обработанные данные')
    return df

# Конфиг: Красивый дизайн.
st.set_page_config(page_title="Аналитика Оборачиваемости", layout="wide", initial_sidebar_state="expanded")
st.title("🚀 Дашборд: Оборачиваемость vs Таргеты по Месяцам")
st.markdown("---")

# Загрузка данных.
file_path = r'C:\Users\40216390\OneDrive - Pepsico\Desktop\Customer Callobaration\FIX PRICE\Обработанные данные.xlsx'  # Твой путь.
df_data = load_data(file_path)

# Sidebar: Фильтры (красиво с иконками).
st.sidebar.header("🔍 Фильтры")
categories = st.sidebar.multiselect("Категория", options=sorted(df_data['Категория'].dropna().unique()), default=sorted(df_data['Категория'].dropna().unique()))
months = st.sidebar.multiselect("Месяц", options=sorted(df_data['Месяц'].unique()), default=sorted(df_data['Месяц'].unique()))
product_codes = st.sidebar.multiselect("Код Товара", options=sorted(df_data['Товар_код'].unique()))
product_names = st.sidebar.selectbox("Наименование Товара", options=['Все'] + sorted(df_data['Товар Наименование'].unique().tolist()))

# Фильтрация данных (только с категорией, чтобы избежать NaN).
filtered_data = df_data[
    (df_data['Категория'].isin(categories)) &
    (df_data['Месяц'].isin(months)) &
    (df_data['Товар_код'].isin(product_codes) if product_codes else True) &
    (df_data['Категория'].notna())  # Фильтр NaN категорий
]
if product_names != 'Все':
    filtered_data = filtered_data[filtered_data['Товар Наименование'] == product_names]

# Динамический pivot для графиков (на filtered_data — фикс KeyError).
if not filtered_data.empty:
    pivot_filtered = pd.pivot_table(
        filtered_data,
        values=['Оборачиваемость', 'VPO Target', 'VPO min Target'],
        index=['Категория', 'Товар_код', 'Товар Наименование', 'Месяц'],
        aggfunc={
            'Оборачиваемость': 'mean',
            'VPO Target': 'first',
            'VPO min Target': 'first'
        },
        fill_value=0  # Для NaN в таргетах
    ).round(2).reset_index()
else:
    pivot_filtered = pd.DataFrame()  # Пустой для empty фильтров.

# Основная панель: Таблица для деталей.
col1, col2 = st.columns([2, 1])
with col1:
    st.subheader("📊 Детальная Таблица (Фильтрованная)")
    if not filtered_data.empty:
        st.dataframe(filtered_data[['Категория', 'Товар_код', 'Товар Наименование', 'Месяц', 'Оборачиваемость', 
                                   'VPO Target', 'VPO min Target', 'Дата']], use_container_width=True)
    else:
        st.info("Нет данных по фильтрам. Попробуйте расширить выбор.")

# График 1: Линейный — Оборачиваемость vs Таргеты по Месяцам (melt для длинного формата).
with col2:
    st.subheader("📈 Оборачиваемость vs Таргеты")
    if not pivot_filtered.empty:
        # Melt для графика: Месяц | Метрика | Значение.
        plot_data = pivot_filtered.melt(id_vars=['Категория', 'Товар_код', 'Товар Наименование', 'Месяц'], 
                                        value_vars=['Оборачиваемость', 'VPO Target', 'VPO min Target'],
                                        var_name='Метрика', value_name='Значение')
        fig1 = px.line(plot_data, x='Месяц', y='Значение', color='Метрика', 
                       title="Динамика по Месяцам", markers=True,
                       color_discrete_map={'Оборачиваемость': 'blue', 'VPO Target': 'green', 'VPO min Target': 'orange'})
        fig1.update_xaxes(title="Месяц", tickvals=sorted(months))
        fig1.update_yaxes(title="Значение")
        st.plotly_chart(fig1, use_container_width=True)
    else:
        st.info("Нет данных для графика.")

# График 2: Бар — % Достижения Таргета (оборачиваемость / VPO Target * 100).
st.subheader("🎯 % Достижения Таргета")
if not pivot_filtered.empty and 'VPO Target' in pivot_filtered.columns and pivot_filtered['VPO Target'].sum() > 0:
    perf_pivot = pivot_filtered.copy()
    perf_pivot['% Достижения'] = (perf_pivot['Оборачиваемость'] / perf_pivot['VPO Target'] * 100).round(1)
    fig2 = px.bar(perf_pivot, x='Месяц', y='% Достижения', color='% Достижения',
                  color_continuous_scale=['red', 'yellow', 'green'],  # Красный <50%, зеленый >100%.
                  title="Достижение Таргета (%)", hover_data=['Категория', 'Товар Наименование'])
    fig2.update_yaxes(title="% Достижения", range=[0, 200])
    st.plotly_chart(fig2, use_container_width=True)
else:
    st.warning("Нет данных для % достижения (проверьте таргеты).")

# Инфо: Ключевые метрики (на filtered_data).
st.subheader("📋 Ключевые Инсайты")
if not filtered_data.empty:
    avg_turnover = filtered_data['Оборачиваемость'].mean().round(2)
    avg_target = filtered_data['VPO Target'].dropna().mean().round(2)
    achievement = (avg_turnover / avg_target * 100).round(1) if avg_target > 0 else 0
    col1, col2, col3 = st.columns(3)
    col1.metric("Средняя Оборачиваемость", f"{avg_turnover}")
    col2.metric("Средний Таргет", f"{avg_target}")
    col3.metric("Среднее Достижение", f"{achievement}%", delta=f"{achievement - 100:+.1f}%")
else:
    st.info("Выберите фильтры для инсайтов.")

# Футер.
st.markdown("---")
st.caption("💡 Дашборд на Streamlit + Plotly. Обновлено: 29.10.2025. Фильтры в реальном времени. Фикс: Динамический pivot на df_data.")
import streamlit as st

st.set_page_config('Среднемесячная начисленная заработная плата', layout='wide', initial_sidebar_state='auto')

from data import SalaryService
service = SalaryService()
service.reload_data()

# --------------------------------------------------------------------------

default_select = ['Образование', 'Финансовая деятельность', 'Строительство', 'Средняя']

st.sidebar.header('Фильтр')

branches = st.sidebar.multiselect('Отрасли:', service.get_branches(), default_select)
years = st.sidebar.slider('За период:', min_value=2000, max_value=2023, value=(2000, 2023))
show_infl = st.sidebar.checkbox('С учетом инфляции', value=True)
#show_discount = st.sidebar.checkbox('Рассчитать дисконтирование', value=True)
#show_change = st.sidebar.checkbox('Показать изменение з/п', value=True)

service.set_filter(branches, years[0], years[1])

st.markdown("#### Данные о номинальной начисленной заработной плате по выбранным отраслям:")
st.table(service.get_data())

fig = service.get_salary_plot(show_infl)
st.plotly_chart(fig, use_container_width=True)

st.markdown('##### Наименьшие и наибольшие з/п по отраслям')
st.markdown('Наведите мышь на столбец, чтобы увидеть название')

fig = service.get_min_max_salary_plot()
st.plotly_chart(fig, use_container_width=True)

st.markdown('''##### Выводы
1. З/п по всем отраслям растут. Без учета инфляции, рост номинальной средней з/п более чем в 33 раза за 2000-2023 гг.
2. Наименьшие з/п в легкой промышленности (производство одежды), наибольшие - в добыче нефти и газа.''')

st.markdown(f"#### Заработная плата, дисконтированная к ценам {years[0]} и {years[1]} гг.:")
st.markdown('Более наглядно показывает динамику заработных плат.')

fig = service.get_salary_discount_plot(years[0], years[1])
st.plotly_chart(fig, use_container_width=True)

st.markdown('#### Влияние инфляции на изменение заработной платы')
st.markdown('Динамика роста заработной платы относительно уровня инфляции:')

fig = service.get_salary_change_plots()
st.plotly_chart(fig, use_container_width=True)

st.markdown('''Примерно до кризиса 2008 г. наблюдался рост реальной з/п даже в
условиях высокой (двузначной) инфляции. После этого наблюдается замедление
роста или даже снижение реальной з/п вслед за высокой инфляцией.''')

st.markdown('##### Выводы')
st.markdown('''1. Средняя реальная з/п по всем отраслям выросла в ~4.5 раза за 2000-2023.
2. Рост номинальной средней (без учета инфляции) з/п отличается от скорректированного
показателя более чем в 7 раз. Накопленная инфляция оказывает значительный
эффект на итоговые цифры.
3. До кризиса 2008 реальная з/п росла выше инфляции, несмотря на ее высокий
уровень. После 2008 реальная з/п обычно снижалась вслед за достижением
двузначного уровня инфляции.''')
import sys
import streamlit as st

st.set_page_config('Среднемесячная начисленная заработная плата', layout='wide', initial_sidebar_state='auto')

from data import SalaryService
service = SalaryService()
service.reload_data()

# --------------------------------------------------------------------------

default_select = ['Образование', 'Финансовая деятельность', 'Строительство', 'Средняя']

st.sidebar.header('Фильтр')

branches = st.sidebar.multiselect('Отрасли:', service.get_all_branches(), default_select)
years = st.sidebar.slider('За период:', min_value=2000, max_value=2023, value=(2000, 2023))
show_infl = st.sidebar.checkbox('С учетом накопленной инфляции', value=True)

if years[0] >= years[1]:
    st.write("Год начала должен быть меньше года окончания")
    sys.exit(0)

service.set_filter(branches, years[0], years[1])
#service.reload_data()

st.markdown("#### Данные о номинальной начисленной заработной плате по выбранным отраслям:")
st.table(service.get_data())

st.markdown(f"##### Графическое представление значений номинальной {('и реальной ' if show_infl else '')}заработной платы:");
fig = service.get_salary_plot(years[0], years[1], show_infl)
st.plotly_chart(fig, use_container_width=True)

st.markdown(f"##### Заработная плата, дисконтированная к ценам {years[1]} гг.:")

fig = service.get_salary_discount_plot(years[0], years[1])
st.plotly_chart(fig, use_container_width=True)

st.markdown(f'##### Наименьшие и наибольшие з/п по отраслям по состоянию на {years[1]} г.')
st.markdown('Наведите мышь на столбец, чтобы увидеть название.')

fig = service.get_min_max_salary_plot(years[1])
st.plotly_chart(fig, use_container_width=True)

st.markdown('''##### Выводы
1. З/п по всем отраслям растут. Без учета инфляции, рост номинальной средней з/п более чем в 33 раза за 2000-2023 гг.
2. Наименьшие з/п в легкой промышленности (производство одежды), наибольшие - в добыче нефти и газа.''')

st.markdown('---')
st.markdown('#### Влияние инфляции на изменение з/п')
st.markdown('Динамика роста заработной платы относительно уровня инфляции:')

fig = service.get_salary_change_plots()
st.plotly_chart(fig, use_container_width=True)

st.markdown('''Примерно до кризиса 2008 г. наблюдался рост реальной з/п даже в
условиях высокой (двузначной) инфляции. После этого наблюдается замедление
роста или даже снижение реальной з/п вслед за высокой инфляцией.''')

fig = service.get_salary_change_corr_plot()
st.plotly_chart(fig, use_container_width=True)

st.markdown('##### Выводы')
st.markdown('''1. Средняя реальная з/п по всем отраслям выросла в ~4.5 раза за 2000-2023.
2. Рост номинальной средней (без учета инфляции) з/п отличается от скорректированного
показателя более чем в 7 раз. Накопленная инфляция оказывает значительный
эффект на итоговые цифры.
3. До кризиса 2008 реальная з/п росла выше инфляции, несмотря на ее высокий
уровень. После 2008 реальная з/п обычно снижалась вслед за достижением
двузначного уровня инфляции.''')

st.markdown('#### Дополнительные исследования')
st.markdown('''Посмотрим на зависимость изменения реальной з/п и следующих показателей:
- [Коэффициент Джини](https://ru.wikipedia.org/wiki/%D0%9A%D0%BE%D1%8D%D1%84%D1%84%D0%B8%D1%86%D0%B8%D0%B5%D0%BD%D1%82_%D0%94%D0%B6%D0%B8%D0%BD%D0%B8)
- [Уровень безработицы](https://rosstat.gov.ru/storage/mediabank/Trud-3_15-72.xlsx)
- [Индекс счастья](https://ru.wikipedia.org/wiki/%D0%9C%D0%B5%D0%B6%D0%B4%D1%83%D0%BD%D0%B0%D1%80%D0%BE%D0%B4%D0%BD%D1%8B%D0%B9_%D0%B8%D0%BD%D0%B4%D0%B5%D0%BA%D1%81_%D1%81%D1%87%D0%B0%D1%81%D1%82%D1%8C%D1%8F)
- [ВВП](https://rosstat.gov.ru/storage/mediabank/VVP_god_s_1995.xlsx)''')

st.plotly_chart(service.get_additional_heatmap(years[0], years[1]), use_container_width=True)

st.markdown('---')
st.markdown('##### Выводы')
st.markdown('''1. Сильная корреляция средней з/п с ВВП. Менее выраженная корреляция с индексом счастья
и коэффициентом Джини.
2. Сильная обратная корреляция средней з/п с уровнем безработицы.''')
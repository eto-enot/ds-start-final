import os
import math
import pandas as pd
import streamlit as st
import plotly.graph_objects as go
import plotly.express as px

from sqlalchemy import create_engine
from plotly.subplots import make_subplots

@st.cache_data
def _get_salary_data(_engine):
    query = '''select b."name" as "Отрасль"'''
    for x in range(2000, 2023+1):
        query += f''', (select sd2.salary from salary_data sd2 where sd2.branch_id = b.id and sd2."year" = {x}) as "{x}"'''
	
    query += '''from branch b'''
    return pd.read_sql(query, con=_engine)

@st.cache_data
def _get_inflation_data(_engine):
    query = 'select "year" as "Год", rate as "Всего" from inflation'
    infl = pd.read_sql(query, con=_engine, index_col='Год')
    infl = infl['Всего']
    infl.name = 'Инфляция'
    infl = infl.iloc[1:]
    return infl.sort_index()

@st.cache_data
def _get_additional_data(_engine):
    query = '''select "year" as "Год"
, gini as "Коэф Джини"
, labour as "Уровень безработицы"
, happy as "Индекс счастья"
, gdp as "ВВП"
from additional'''
    add = pd.read_sql(query, con=_engine, index_col='Год')
    return add.sort_index()

@st.cache_data
def _get_new_data(_engine):
    query = 'select * from new_data'
    return pd.read_sql(query, con=_engine)

@st.cache_data
def _get_old_data(_engine):
    query = 'select * from old_data'
    return pd.read_sql(query, con=_engine)

def _get_line(data, name):
    line = data[data['Отрасль'] == name].drop(['Отрасль'], axis=1)
    line = line.squeeze()
    line.index = line.index.map(int)
    return line

def _filter_data(data, branches, year_from, year_to):
    cols = ['Отрасль'] + [str(year) for year in range(year_from, year_to + 1)]
    data = data[cols]
    return data[data['Отрасль'].isin(branches)]

class SalaryService:
    def __init__(self):
        self._data = []
        self._infl = []
        self._data_real = []
        self._add = []
        self._data_filtered = []
        self._infl_filtered = []
        self._data_real_filtered = []
        self._branches_filtered = []
        self._new_data = []
        self._old_data = []
        self._add_filtered = []
        self._show_infl = False

    # старые цены в новые
    def _compound(self, year_from, year_to, sum):
        result = sum
        for x in range(year_from, year_to):
            result *= 1.0 + self._infl.loc[x] / 100.0
        return result

    # новые цены в старые
    def _discount(self, year_from, year_to, sum):
        result = sum
        for x in range(year_from, year_to, -1):
            result /= 1.0 + self._infl.loc[x] / 100.0
        return result

    def reload_data(self):
        def _get_conn_str():
            user = os.environ['DB_USER']
            password = os.environ['DB_PASSWORD']
            host = os.environ['DB_HOST']
            name = os.environ['DB_NAME']
            return f'postgresql://{user}:{password}@{host}/{name}?sslmode=require'
        
        try:
            engine = create_engine(_get_conn_str())
            self._data = _get_salary_data(engine)
            self._infl = _get_inflation_data(engine)
            self._new_data = _get_new_data(engine)
            self._old_data = _get_old_data(engine)
            self._add = _get_additional_data(engine)
        finally:
            engine.dispose()

    def set_filter(self, branches, year_from, year_to):
        self._branches_filtered = branches
        self._data_filtered = _filter_data(self._data, branches, year_from, year_to)
        self._add_filtered = self._add[(self._add.index <= year_to) & (self._add.index >= year_from)]
        self._infl_filtered = self._infl[(self._infl.index <= year_to) & (self._infl.index >= year_from)]

    def get_all_branches(self):
        return self._data['Отрасль'].array
    
    def get_branches(self):
        return self._branches_filtered
    
    def get_data(self):
        return self._data_filtered
    
    def get_infl(self):
        return self._infl_filtered
    
    def get_add(self):
        return self._add_filtered
    
    def _get_data_start(self, year_from, year_to):
        data_start = self.get_data().copy()
        for year in range(year_from, year_to + 1):
            data_start[str(year)] = self._discount(year, year_from, data_start[str(year)])
        return data_start

    def _get_data_end(self, year_from, year_to):
        data_end = self.get_data().copy()
        for year in range(year_from, year_to + 1):
            data_end[str(year)] = self._compound(year, year_to, data_end[str(year)])
        return data_end
    
    def get_salary_plot(self, year_from, year_to, show_infl):
        data = self.get_data()
        data_real = self._get_data_start(year_from, year_to)
        fig = go.Figure()
        axis_type = None
        for name in self.get_branches():
            dt = _get_line(data, name)
            if show_infl:
                dt_real = _get_line(data_real, name)
                fig.add_trace(go.Scatter(x=dt_real.index, y=dt_real.array, name=name + ' с учетом инфл.'))
                fig.add_trace(go.Scatter(x=dt.index, y=dt.array, name=name, line=dict(dash='dot')))
                axis_type = 'log'
            else:
                fig.add_trace(go.Scatter(x=dt.index, y=dt.array, name=name))
        
        fig.update_layout(xaxis_title='год', yaxis_title='з/п, руб.', yaxis_type=axis_type,
                          margin=dict(l=20, r=10, t=40, b=10))
        return fig
    
    def get_salary_discount_plot(self, year_from, year_to):
        data_end = self._get_data_end(year_from, year_to)

        fig = go.Figure()
        for name in self.get_branches():
            dt = _get_line(data_end, name)
            fig.add_trace(go.Scatter(x=dt.index, y=dt.array, name=name))
        
        fig.update_layout(margin=dict(l=20,r=20,b=40,t=50),
                          xaxis_title='год', yaxis_title='з/п, руб.',)

        return fig
    
    def _get_changes(self):
        dt = self.get_data().transpose()
        dt = dt.set_axis(dt.iloc[0], axis='columns')
        dt = dt.iloc[1:]
        dt.index.name = 'Год'
        dt.index = dt.index.map(int)
        dt = dt.pct_change() * 100.0
        dt = dt.iloc[1:]
        return dt
    
    def get_salary_change_plots(self):
        n = 0
        dt, infl = self._get_changes(), self.get_infl()
        fig = make_subplots(rows=math.ceil(len(self.get_branches()) / 2.0), cols=2, subplot_titles=self._branches_filtered)
        for line in self.get_branches():
            bar = dt[line] - self.get_infl()
            row = n // 2 + 1
            col = n % 2 + 1
            fig.add_trace(go.Bar(x=bar.index, y=bar.array, name=line, marker_color='blue'), col=col, row=row)
            if col == 1:
                fig.update_yaxes(title_text='%', row=row, col=col)
            n += 1
        fig.update_layout(showlegend=False, margin=dict(l=20, r=10, t=40, b=10))
        
        return fig
    
    def get_salary_change_corr_plot(self):
        dt, infl = self._get_changes(), self.get_infl()
        dx = dt.subtract(infl[infl.index > 2000], axis=0)
        dx = pd.concat([dx[dx.index <= 2008].corrwith(infl).round(2), dx[dx.index > 2008].corrwith(infl).round(2)], axis=1)
        dx = dx.rename({ 0: 'До 2008', 1: 'После 2008' }, axis=1)
        fig = px.imshow(dx.transpose(), text_auto=True, color_continuous_scale=px.colors.sequential.Blues)
        fig.update_layout(
            title='Зависимость изменения з/п к прошлому году от уровня инфляции',
            xaxis = {
            'tickmode': 'array',
            'tickvals': list(dx.index),
            'ticktext': dx.index.str[:20].tolist(),
            }
        )
        return fig
    
    def get_min_max_salary_plot(self, year):
        if year >= 2017:
            minmax = self._new_data[['Отрасль', str(year)]]
        else:
            minmax = self._old_data[['Отрасль', str(year)]]
        minmax = minmax.set_index('Отрасль')
        minmax = minmax[str(year)].sort_values()

        fig = go.Figure()
        fig.add_trace(go.Bar(x=minmax.index, y=minmax.array))
        fig.update_layout(xaxis_visible=False, margin=dict(l=20,r=20,b=10,t=40), yaxis_title='з/п, руб.')
        
        return fig
    
    def get_additional_heatmap(self, year_from, year_to):
        dt = self._get_data_start(year_from, year_to).transpose()
        dt = dt.rename(columns=dt.iloc[0])
        dt = dt[1:]
        dt.index.name = 'Год'
        dt.index = dt.index.astype(int)
        dt = dt[['Средняя']]

        dt = dt.merge(self.get_add(), left_index=True, right_index=True).corr().round(2)

        return px.imshow(dt, text_auto=True, color_continuous_scale=px.colors.sequential.Blues)

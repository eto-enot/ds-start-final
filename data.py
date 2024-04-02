import os
import math
import pandas as pd
import streamlit as st
import plotly.graph_objects as go

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

def _get_real_data(data, infl):
    data_real = data.copy()
    for year in range(2000, 2023+1):
        data_real[str(year)] /= (1 + infl[year] / 100.0)
    return data_real

@st.cache_data
def _get_new_data(_engine):
    query = 'select * from new_data'
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
        self._data_filtered = []
        self._infl_filtered = []
        self._data_real_filtered = []
        self._branches_filtered = []
        self._new_data = []
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
            self._data_real = _get_real_data(self._data, self._infl)
        finally:
            engine.dispose()

    def set_filter(self, branches, year_from, year_to):
        self._branches_filtered = branches
        self._data_filtered = _filter_data(self._data, branches, year_from, year_to)
        self._data_real_filtered = _filter_data(self._data_real, branches, year_from, year_to)
        self._infl_filtered = self._infl[(self._infl.index <= year_to) & (self._infl.index >= year_from)]

    def get_branches(self):
        return self._data['Отрасль'].array
    
    def get_data(self):
        return self._data_filtered
    
    def get_data_real(self):
        return self._data_real_filtered
    
    def get_infl(self):
        return self._infl_filtered
    
    def get_salary_plot(self, show_infl):
        data = self._data_filtered
        data_real = self._data_real_filtered
        fig = go.Figure()
        for name in self._branches_filtered:
            dt = _get_line(data, name)
            if show_infl:
                dt_real = _get_line(data_real, name)
                fig.add_trace(go.Scatter(x=dt_real.index, y=dt_real.array, name=name + ' с учетом инфл.'))
                fig.add_trace(go.Scatter(x=dt.index, y=dt.array, name=name, line=dict(dash='dot')))
            else:
                fig.add_trace(go.Scatter(x=dt.index, y=dt.array, name=name))
        fig.update_layout(xaxis_title='год', yaxis_title='з/п, руб.',
                          margin=dict(l=20, r=10, t=40, b=10))
        return fig
    
    def get_salary_discount_plot(self, year_from, year_to):
        data_end = self._data_filtered.copy()
        data_start = self._data_filtered.copy()

        for year in range(year_from, year_to + 1):
            data_end[str(year)] = self._compound(year, year_to, data_end[str(year)])
            data_start[str(year)] = self._discount(year, year_from, data_start[str(year)])

        def plot(data, fig, year, col):
            for name in self._branches_filtered:
                dt = _get_line(data, name)
                fig.add_trace(go.Scatter(x=dt.index, y=dt.array, name=name, legendgroup = str(col)), col=col, row=1)
                
        titles = [
            f'Среднемесячная реальная начисленная<br>заработная плата в ценах {year_from} г.',
            f'Среднемесячная реальная начисленная<br>заработная плата в ценах {year_to} г.',
        ]

        fig = make_subplots(rows=1, cols=2, subplot_titles=titles)
        plot(data_start, fig, year_from, 1)
        plot(data_end, fig, year_to, 2)
        fig.update_layout(legend_tracegroupgap = 50,
                          margin=dict(l=20, r=10, t=40, b=10))

        return fig
    
    def get_salary_change_plots(self):
        dt = self._data_real_filtered.transpose()
        dt = dt.set_axis(dt.iloc[0], axis='columns')
        dt = dt.iloc[1:]
        dt.index.name = 'Год'
        dt.index = dt.index.map(int)
        dt = dt.pct_change() * 100.0
        dt = dt.iloc[1:]
        dt.join(self._infl_filtered)[self._branches_filtered + ['Инфляция']].transpose()

        n = 0
        fig = make_subplots(rows=math.ceil(len(self._branches_filtered) / 2.0), cols=2, subplot_titles=self._branches_filtered)
        for line in self._branches_filtered:
            bar = dt[line] - self._infl_filtered
            row = n // 2 + 1
            col = n % 2 + 1
            fig.add_trace(go.Bar(x=bar.index, y=bar.array, name=line, marker_color='blue'), col=col, row=row)
            n += 1
        fig.update_layout(showlegend=False, margin=dict(l=20, r=10, t=40, b=10))
        
        return fig
    
    def get_min_max_salary_plot(self):
        minmax = self._new_data[['Отрасль', '2023']]
        minmax = minmax.set_index('Отрасль')
        minmax = minmax['2023'].sort_values()

        fig = go.Figure()
        fig.add_trace(go.Bar(x=minmax.index, y=minmax.array))
        fig.update_layout(xaxis_visible=False, margin=dict(l=20,r=20,b=10,t=40))
        
        return fig

import dash
from dash import html, dcc
import pandas as pd
import plotly.express as px
import plotly.graph_objects as go
import numpy as np

df = pd.read_csv('./Slot Utilization.csv')
df = df[df['CAPACITY'].notna()]
df = df[~df['BRNCH_CD'].isin(['X1', 'X6', 'X7'])]
df = df[~df['FULL_MARKET_NAME'].str.contains('STOCK YARDS')]
df_area_agg = df.groupby(['FULL_MARKET_NAME', 'DATE_EXTRACT']).agg(np.sum).reset_index()
df_area = df.groupby(['FULL_MARKET_NAME', 'DATE_EXTRACT', 'AREA']).agg(np.sum).reset_index()
df_area = df_area.merge(df_area_agg, on=['FULL_MARKET_NAME', 'DATE_EXTRACT'])
df_area['CAPACITY'] = df_area['SUM(PALLET_USED)_x'] / df_area['SUM(PALLET_USED)_y'] 
df = df.groupby(['FULL_MARKET_NAME', 'BRNCH_CD', 'DATE_EXTRACT', 'AREA']).agg(np.mean).reset_index()
df['CAPACITY'] = df['SUM(PALLET_USED)'] / df['SUM(PALLET_POSITIONS)']
cases = pd.read_csv('./cases_sold.csv')
cases['FISC_YR_WK'] = pd.to_datetime(cases['FISC_YR_WK'].astype(str) + '0', format="%Y%W%w")
cases = cases.groupby(['BRNCH_CD', 'FISC_YR_WK']).agg(np.sum).reset_index()
inv = pd.read_csv('./inventory.csv')
inv['FISC_YR_WK'] = pd.to_datetime(inv['FISC_YR_WK'].astype(str) + '0', format="%Y%W%w")
inv = inv.groupby(['BRNCH_CD', 'FISC_YR_WK']).agg(np.sum).reset_index()
forecast = pd.read_csv("forecasted_capacity.csv")
forecast = forecast.groupby(['BRNCH_CD', 'DATE_EXTRACT', 'AREA', 'MODEL']).agg(np.mean).reset_index()

app = dash.Dash(__name__)

app.layout = html.Div([
    dcc.Dropdown(
        id='branch-dropdown',
        options=[{'label': i, 'value': i} for i in df['FULL_MARKET_NAME'].unique()],
        value=['CHICAGO (3Y, 2099)'],
        multi=True
    ),
    dcc.DatePickerRange(
        id='date-picker-range',
        min_date_allowed=df['DATE_EXTRACT'].min(),
        max_date_allowed=forecast['DATE_EXTRACT'].max(),
        initial_visible_month=df['DATE_EXTRACT'].min(),
        start_date=df['DATE_EXTRACT'].min(),
        end_date=forecast['DATE_EXTRACT'].max()
    ),
    dcc.Graph(id='line-chart'),
    html.Br(),
    dcc.Graph(id='line-chart2'),
    html.Br(),
    dcc.Graph(id='line-chart3'),
    html.Br(),
    dcc.Dropdown(
        id='branch-dropdown-2',
        options=[{'label': i, 'value': i} for i in df['FULL_MARKET_NAME'].unique()],
        value='CHICAGO (3Y, 2099)'
    ),
    dcc.Graph(id='stacked-area-chart')
])

@app.callback(
    dash.dependencies.Output('line-chart', 'figure'),
    [dash.dependencies.Input('branch-dropdown', 'value'),
     dash.dependencies.Input('date-picker-range', 'start_date'),
     dash.dependencies.Input('date-picker-range', 'end_date')])
def update_line_chart(selected_branches, start_date, end_date):
    if isinstance(selected_branches, str):
        selected_branches = [selected_branches]
    filtered_df = df[(df['FULL_MARKET_NAME'].isin(selected_branches)) & (df['DATE_EXTRACT'] >= start_date) & (df['DATE_EXTRACT'] <= end_date)]
    filtered_df['MODEL'] = 'Observed'
    selected_branches2 = [np.unique(df[df['FULL_MARKET_NAME'] == name]['BRNCH_CD'])[0] for name in selected_branches]
    filtered_forecast = forecast[(forecast['BRNCH_CD'].isin(selected_branches2)) & (forecast['DATE_EXTRACT'] >= start_date) & (forecast['DATE_EXTRACT'] <= end_date)]
    filtered_forecast = filtered_forecast.merge(df.loc[:,['BRNCH_CD', 'FULL_MARKET_NAME']].drop_duplicates(), how='left')
    full = pd.concat([filtered_df, filtered_forecast])
    fig = px.line(full, x='DATE_EXTRACT', y='CAPACITY', color='FULL_MARKET_NAME', facet_row='AREA', line_dash='MODEL',
                  labels={'DATE_EXTRACT':'Date', 'CAPACITY':'Capacity', 'FULL_MARKET_NAME':'Branch', 'AREA':'Area', 'MODEL':'Model'},
                  title='Daily Capacity for Selected Warehouse(s)', height=1000, facet_row_spacing=0.03)   
    return fig

@app.callback(
    dash.dependencies.Output('line-chart2', 'figure'),
    [dash.dependencies.Input('branch-dropdown', 'value'),
     dash.dependencies.Input('date-picker-range', 'start_date'),
     dash.dependencies.Input('date-picker-range', 'end_date')])
def update_line_chart2(selected_branches, start_date, end_date):
    if isinstance(selected_branches, str):
        selected_branches = [selected_branches]
    selected_branches.sort()
    selected_branches2 = [np.unique(df[df['FULL_MARKET_NAME'] == name]['BRNCH_CD'])[0] for name in selected_branches]
    filtered_df = cases[(cases['BRNCH_CD'].isin(selected_branches2)) & (cases['FISC_YR_WK'] >= start_date) & (cases['FISC_YR_WK'] <= end_date)]
    fig = px.line(filtered_df, x='FISC_YR_WK', y='CASES_SOLD', color='BRNCH_CD',
                  labels={'FISC_YR_WK':'Fiscal Week', 'CASES_SOLD':'Cases Sold', 'BRNCH_CD':'Branch'},
                  title='Weekly Cases Sold for Selected Warehouse(s)')
    for i, b in enumerate(selected_branches2):
        filtered_forecast = forecast[(forecast['BRNCH_CD'] == b) & (forecast['DATE_EXTRACT'] >= start_date) & (forecast['DATE_EXTRACT'] <= end_date) & (forecast['DATE_EXTRACT'] > max(df['DATE_EXTRACT']))]
        fig.add_trace(go.Scatter(x=filtered_forecast['DATE_EXTRACT'], y=filtered_forecast['CASES_SOLD'], name=selected_branches2[i]+' FORECAST',
                                 line={'dash':'dot'}, marker={'color':fig.data[i].line.color}))
    return fig

@app.callback(
    dash.dependencies.Output('line-chart3', 'figure'),
    [dash.dependencies.Input('branch-dropdown', 'value'),
     dash.dependencies.Input('date-picker-range', 'start_date'),
     dash.dependencies.Input('date-picker-range', 'end_date')])
def update_line_chart3(selected_branches, start_date, end_date):
    if isinstance(selected_branches, str):
        selected_branches = [selected_branches]
    selected_branches = [np.unique(df[df['FULL_MARKET_NAME'] == name]['BRNCH_CD'])[0] for name in selected_branches]
    filtered_df = inv[(inv['BRNCH_CD'].isin(selected_branches)) & (inv['FISC_YR_WK'] >= start_date) & (inv['FISC_YR_WK'] <= end_date)]
    fig = px.line(filtered_df, x='FISC_YR_WK', y='MAX_WKLY_INVENTORY', color='BRNCH_CD',
                  labels={'FISC_YR_WK':'Fiscal Week', 'MAX_WKLY_INVENTORY':'Max Weekly Inventory', 'BRNCH_CD':'Branch Code'},
                  title='Max Weekly Inventory for Selected Warehouse(s)')
    return fig

@app.callback(
    dash.dependencies.Output('stacked-area-chart', 'figure'),
    [dash.dependencies.Input('branch-dropdown-2', 'value')])
def update_stacked_area_chart(selected_branch):
    filtered_df = df_area[(df_area['FULL_MARKET_NAME'] == selected_branch)]
    fig = px.area(filtered_df, x='DATE_EXTRACT', y='CAPACITY', color='AREA',
                  labels={'DATE_EXTRACT':'Date', 'CAPACITY':'Capacity', 'AREA':'Area'},
                  title='Daily Percentage of Total Pallet Positions Used by Area for Selected Warehouse')
    
    return fig

if __name__ == '__main__':
    app.run_server(debug=True)

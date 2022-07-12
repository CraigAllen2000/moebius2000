import plotly.graph_objects as go # or plotly.express as px
import dash
from dash import dcc
from dash import html
from dash import Input, Output
import pandas as pd
import numpy as np
import requests
import json
import datetime
from plotly.subplots import make_subplots
from stock_tools import *


#fig.add_trace(go.Scatter(x=[datetime.datetime(2021,5,1),datetime.datetime(2021,4,1),datetime.datetime(2021,6,1)], y=[140, 150, 145],mode="markers",marker_symbol="x",marker_color="green"))

app = dash.Dash()
app.layout = html.Div([
    dcc.Input(
            id="tick-input",
            type="text",
            value='DVA',
            placeholder="input type {}".format("text"),
        ),
    dcc.Input(
            id="date-input-start",
            type="text",
            value="01-01-21",
            placeholder="input type {}".format("text"),
        ),
    dcc.Input(
            id="date-input-end",
            type="text",
            value="01-01-22",
            placeholder="input type {}".format("text"),
        ),
    html.Div(
        [dcc.Checklist(
            options=['SMA'],
            id='sma-input'
        ),
        dcc.Checklist(
            options=['EMA'],
            id='ema-input'
        ),
        dcc.Checklist(
            options=['Bollinger Bands'],
            id='bands-input'
        )]
    ),
    html.Div([dcc.Dropdown(['MACD','RSI','EMA'], id='rules'),html.Button('Run Simulation', id='run-sim', n_clicks=0)]),
    html.Div(id='profit-output'),
    html.Div(dcc.Graph(id='graph-output1',figure={})),
    html.Div(dcc.Graph(id='graph-output2',figure={},config={
        'displayModeBar': False
    }))
])

global tick_saver
tick_saver = 'DVA'

@app.callback(
    Output(component_id='graph-output1', component_property='figure'),
    Output(component_id='graph-output2', component_property='figure'),
    Output(component_id='run-sim',component_property='n_clicks'),
    Output(component_id='profit-output',component_property='children'),
    Input(component_id='tick-input', component_property='value'),
    Input(component_id='date-input-start', component_property='value'),
    Input(component_id='date-input-end', component_property='value'),
    Input(component_id='sma-input', component_property='value'),
    Input(component_id='ema-input', component_property='value'),
    Input(component_id='bands-input', component_property='value'),
    Input(component_id='run-sim',component_property='n_clicks'),
    Input(component_id='rules',component_property='value')
)
def update_output_div(tick_input,date_input_start,date_input_end,sma_input,ema_input,band_input,n_clicks,rule_input):
    global tick_saver
    if tick_saver != tick_input:
        tick_saver = tick_input
        new_clicks = 0
        n_clicks = 0
    else: 
        new_clicks = n_clicks
    tick = tick_input
    start_date = datetime.datetime.strptime(date_input_start, '%m-%d-%y')
    end_date = datetime.datetime.strptime(date_input_end, '%m-%d-%y')
    dates = [start_date,end_date]
    data, df = getPriceHistory(tick,dates,"daily")
    sma_data = sma(df['close'],20)
    ema_data = emma(df['close'],20)
    lower_band,upper_band = get_Bands(df['close'],20,2)
    profit = 0
    if rule_input == 'MACD':
        rule = MACD_rule
    if rule_input == 'RSI':
        rule = RSI_rule
    if rule_input == 'EMA':
        rule = EMMA_rule
    fig1 = go.Figure(go.Candlestick(
        x=convert_time(df['datetime']),
        open=df['open'],
        high=df['high'],
        low=df['low'],
        close=df['close'],
        name = tick+ ' candlesticks'
    ))
    try:
        if sma_input[0] == 'SMA':
            print('sma')
            fig1.add_trace(go.Scatter(x=convert_time(df['datetime']), y=sma_data,mode="lines",line_color="#0000ff",name='SMA'))
    except:
        pass
    try:
        if ema_input[0] == 'EMA':
            print('ema')
            fig1.add_trace(go.Scatter(x=convert_time(df['datetime']), y=ema_data,mode="lines",line_color="#ff0000",name='EMA')) 
    except:
        pass
    try:
        if band_input[0] == 'Bollinger Bands':
            print('bands')
            fig1.add_trace(go.Scatter(x=convert_time(df['datetime']), y=upper_band,mode="lines",line_color="#f0f000",name='Upper Band')) 
            fig1.add_trace(go.Scatter(x=convert_time(df['datetime']), y=lower_band,mode="lines",line_color="#f0f000",name='Lower Band')) 
    except:
        pass
    if n_clicks > 0:
        wait_time = 10
        capital = 100000
        bp = 1.99 #when to buy back in after selling
        sp =  .95#what loss to take
        trade_log, balance = runSimulation(df,rule,wait_time,capital,bp,sp,False)
        profit = 100*(balance[0]+balance[2]-capital)/(balance[0]+balance[2])
        buys = []
        buys_time = []
        sells = []
        sells_time = []
        for i in range(len(trade_log)):
            if trade_log[i] == 1:
                buys.append(df['close'][i])
                buys_time.append(df['datetime'][i])
            if trade_log[i] == 2:
                sells.append(df['close'][i])
                sells_time.append(df['datetime'][i])
        fig1.add_trace(go.Scatter(x=convert_time(buys_time), y=buys,mode="markers",marker_color='green',marker_symbol='300',marker_size=15,name='Buys')) 
        fig1.add_trace(go.Scatter(x=convert_time(sells_time), y=sells,mode="markers",marker_color='red',marker_symbol='300',marker_size=15,name='Sells')) 
    fig2 = go.Figure([go.Bar(x=convert_time(df['datetime']), y=df['volume'],)])
    fig2.update_layout(autosize=False,height=300)
    return fig1,fig2,new_clicks,str(profit)+r"% Profit/Loss"

app.run_server(debug=True, use_reloader=False)  # Turn off reloader if inside Jupyter
import pandas as pd
import sqlite3
from datetime import date
import configparser
import ast

import dash
import dash_table
import dash_auth
import dash_html_components as html
import dash_core_components as dcc
from dash.dependencies import Input, Output

import json
import requests

import DB
import business
from DB import *
from business import *

config = configparser.ConfigParser()
config.read('config.txt')
VALID_USERNAME_PASSWORD_PAIRS = ast.literal_eval(config.get('authentication', 'username_password_pairs'))

df_claim_types = get_distinct_claim_types()
df_claim_status = get_distinct_claim_status()
df_claims = get_claim_empty_rec()
df_claim_details = get_claim_details_empty_rec()

lv_claims_filter = ""
lv_claim_types  = []
lv_claim_status = []

app = dash.Dash(__name__)

auth = dash_auth.BasicAuth(
    app,
    VALID_USERNAME_PASSWORD_PAIRS
)

tabs_styles = {
    'height': '44px'
}
tab_style = {
    'borderBottom': '1px solid #d6d6d6',
    'padding': '6px',
    'fontWeight': 'bold'
}

tab_selected_style = {
    'borderTop': '1px solid #d6d6d6',
    'borderBottom': '1px solid #d6d6d6',
    'backgroundColor': '#119DFF',
    'color': 'white',
    'padding': '6px'
}

app.layout = html.Div([
    dcc.Tabs(id="tabs_claims", value='tab_claims',children = [
        dcc.Tab(label='Claims', value='tab_claims', id = "tab_claims", style=tab_style, selected_style=tab_selected_style, children=[
            html.Div([dcc.Dropdown(id='dropdown_claim_type',
                        options=[{'label':i, 'value':i} for i in df_claim_types['claim_type']],
                        multi=True,
                        placeholder="Select a claim type",
                        value = lv_claim_types
            )]),
            html.Div([dcc.Dropdown(id='dropdown_claim_status',
                        options=[{'label':i, 'value':i} for i in df_claim_status['claim_status']],
                        multi=True,
                        placeholder="Select a claim status",
                        value = lv_claim_status
            )]),
            html.Div([dcc.Input(id="input_claim_number", type="text",
                     debounce=False, placeholder="Type a claim number",
            ), dcc.DatePickerRange(
                id = 'date_picker_range',
                min_date_allowed=date(1995, 1, 1),
                max_date_allowed=date(2021, 4, 20),
                display_format='MMM Do, YY',
                start_date_placeholder_text='Start date',
                end_date_placeholder_text='End date'
            )]),
            html.Br(),
            html.Div([dash_table.DataTable(
                id='table_claims',
                columns=([{'id': p, 'name': p.upper()} for p in df_claims.columns]),
                data=df_claims.to_dict('records'),
                editable=False,
                row_selectable="single",
                page_current= 0,
                page_size= 3,
                ),
        ]) ]),
        dcc.Tab(label='Claim Details', value='tab_claim_details', id = "tab_claim_details", style=tab_style, selected_style=tab_selected_style, children = [
            dash_table.DataTable(
                id='table_claim_details',
                columns=([{'id': p, 'name': p} for p in df_claim_details.columns]),
                data=df_claim_details.to_dict('records'),
                editable=False,
                ),
        ])
    ]
    )
    ,html.Div(id='claims_tab_content')
    ,html.Div(id='claim_details_tab_content'),
    html.Div(id='claim_numbers', style={'display': 'none'}),
])

@app.callback([Output('table_claims', 'data'),
               Output('claim_numbers','children')],
              [Input('dropdown_claim_type', 'value'),
               Input('dropdown_claim_status', 'value'),
               Input('input_claim_number', 'value'),
               Input('date_picker_range', 'start_date'),
               Input('date_picker_range', 'end_date')])
def change_dropdown_claim_type(claim_types,claim_status,claim_number,start_date,end_date):
    lv_claim_types = claim_types
    lv_claim_status = claim_status
    lv_claim_number = claim_number
    lv_start_date = start_date
    lv_end_date = end_date
    print('Selected types: ',lv_claim_types)
    print('Selected status: ',lv_claim_status)
    print('Selected number: ',lv_claim_number)
    print('Selected start date: ',lv_start_date)
    print('Selected end date: ',lv_end_date)
    where_conds = []
    if lv_claim_types:
        where_conds.append(get_filter_claim_types(lv_claim_types))
    if lv_claim_status:
        where_conds.append(get_filter_claim_status(lv_claim_status))    
    if lv_claim_number:
        where_conds.append(get_filter_claim_number(lv_claim_number))
    if lv_start_date and lv_end_date:
        where_conds.append(get_filter_claim_dates(lv_start_date,lv_end_date))
    
    if len(where_conds)>0:
        df = get_multiple_filter(where_conds)
    else:
        df = get_claims_top10()
        
    df = calculate(df)
        
    data=df.to_dict('records')
    print("Table data: ",data)
    claim_numbers_string = ','.join(df['claim_no'].astype(str).tolist())
    print("Claim_numbers_string: ",claim_numbers_string)
    return data, claim_numbers_string

#callback for selected claim in Claims table
@app.callback(Output('table_claim_details', 'data'),
             [Input('claim_numbers','children'),
              Input('table_claims','selected_rows')])
def table_claim_select_row(claim_numbers_string, selected_rows):
    data = []
#    print('Existingng data:',a_data)
    print('Selected row:',selected_rows)
    print("Claim_numbers_string fn2: ",claim_numbers_string)
    if selected_rows and (selected_rows[0] >= 0) and (selected_rows[0] <= len(claim_numbers_string)/2):
        claim_numbers_list = claim_numbers_string.split(',') 
        claim_no = claim_numbers_list[selected_rows[0]]
        print("Claim no:",claim_no)
        parameters = {"claim_no":claim_no}
        response = requests.post("http://127.0.0.1:5000/", json=parameters )
        ret_status = response.status_code
        print("API Call return status code: ", ret_status)
        if ret_status == 200:
            #print("Received from API call:",response.json())
            x = response.json()
            print("response text:",x)
            for k,v in x.items():
                data.append({'COLUMN_NAME':k,'COLUMN_VALUE':v})
            
    print("Data to return:",data)
    return data

if __name__ == '__main__':
    app.run_server(debug=False)


import logging
logging.basicConfig(filename='app.log', level=logging.DEBUG)

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
from dash.dependencies import Input, Output, State

import json
import requests

from business import calculate

# Read DB type and import corresponding class
config = configparser.ConfigParser()
try:
    config.read('config.txt')
    active_type = config.get('db_types', 'active_type')
    logging.debug("Active DB type = {}".format(active_type))
except Exception as e:
    logging.error('Config file missing or active DB type not defined: ' + str(e))
print("Database type: ",active_type)

if active_type == 'sqlite':
    try:
        from DB import SQLite
        name = config.get('db_names','db_name_o')
        path = config.get('sqlite_paths', 'db_path_o')
        db = SQLite(name,path)
        logging.debug("SQLite DB name = {}, path = {}".format(name,path))
    except Exception as e:
        logging.error('Could not create SQLite class instance: ' + str(e))
        
elif active_type == 'postgres':
    try:
        from DB import Postgres
        name = config.get('db_names','db_name_o').split('.')[0]
        user = config.get('postgres_users', 'user')
        password = config.get('postgres_passwords', 'password')
        db = Postgres(name, user, password)
        logging.debug("Postgres DB name = {}, user = {}, password = {}".format(name,user,password))
    except Exception as e:
        logging.error('Could not create Postgres class instance: ' + str(e))

# Get authentication info and static DataFrames
try:
    VALID_USERNAME_PASSWORD_PAIRS = ast.literal_eval(config.get('authentication', 'username_password_pairs'))
    logging.debug('Authentication username_password pairs retrieved from config file')
except Exception as e:
    logging.error('Authentication username_password pairs could not be retrieved from config file: ' + str(e))

df_claim_types = db.get_distinct_claim_types()
df_claim_status = db.get_distinct_claim_status()
df_claims = db.get_claim_empty_rec()
df_claim_details = db.get_claim_details_empty_rec()

lv_claims_filter = ""
lv_claim_types  = []
lv_claim_status = []

app = dash.Dash(__name__)

# Dash authentication
try:
    auth = dash_auth.BasicAuth(
        app,
        VALID_USERNAME_PASSWORD_PAIRS
    )
    logging.debug('Created authentication')
except Exception as e:
    logging.error('Could not create authentication: ' + str(e))

# Dash display settings
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

# App layout
app.layout = html.Div([
    dcc.Tabs(id="tabs_claims", value='tab_claims',children = [
        dcc.Tab(label='Claims', value='tab_claims', id = "tab_claims", style=tab_style, selected_style=tab_selected_style, children=[
            html.H5(id='title1',children='Claim type',style={'text-align':'center'}),
            html.Div([dcc.Dropdown(id='dropdown_claim_type',
                        options=[{'label':i, 'value':i} for i in df_claim_types['claim_type']],
                        multi=True,
                        placeholder="Select a claim type",
                        value = lv_claim_types
            )]),
            html.H5(id='title2',children='Claim status',style={'text-align':'center'}),
            html.Div([dcc.Dropdown(id='dropdown_claim_status',
                        options=[{'label':i, 'value':i} for i in df_claim_status['claim_status']],
                        multi=True,
                        placeholder="Select a claim status",
                        value = lv_claim_status
            )]),
            html.H5(id='title3',children='Claim number',style={'text-align':'center'}),
            html.Div([dcc.Input(id="input_claim_number", type="text",
                     debounce=False, placeholder="Type a claim number",
            )]),
            html.H5(id='title4',children='Claim date',style={'text-align':'center'}),
            html.Div([dcc.DatePickerRange(
                id = 'date_picker_range',
                min_date_allowed=date(2020, 1, 1),
                max_date_allowed=date(2021, 4, 20),
                display_format='MMM Do, YY',
                start_date_placeholder_text='Start date',
                end_date_placeholder_text='End date',
                style = {'align':'center'}
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
        ]),
    ]
    ),
    html.Div(id='claim_numbers', style={'display': 'none'}),
])
logging.debug('Created dropdown claim type'),
logging.debug('Created dropdown claim status'),
logging.debug('Created input edit box claim number'),
logging.debug('Created date range input'),
logging.debug('Created tab 1 table'),
logging.debug('Created tab 2 table')
logging.debug('Created hidden list of claim numbers'),
logging.debug('Completed layout section')

# Callbacks
# Tab 1 callback for selected filtering options 
@app.callback([Output('table_claims', 'data'),
               Output('claim_numbers','children'),
               Output('table_claims', 'selected_rows')],
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
    logging.debug("Callback change_dropdown_claim_type received inputs {}".format(claim_types,claim_status,claim_number,start_date,end_date))
    logging.info("Callback change_dropdown_claim_type selected types: ".format(lv_claim_types))
    logging.info("Callback change_dropdown_claim_type selected status: ".format(lv_claim_status))
    logging.info("Callback change_dropdown_claim_type selected number: ".format(lv_claim_number))
    logging.info("Callback change_dropdown_claim_type selected start date: ".format(lv_start_date))
    logging.info("Callback change_dropdown_claim_type selected end date: ".format(lv_end_date))
    where_conds = []
    if lv_claim_types:
        where_conds.append(db.get_filter_claim_types(lv_claim_types))
    if lv_claim_status:
        where_conds.append(db.get_filter_claim_status(lv_claim_status))    
    if lv_claim_number:
        where_conds.append(db.get_filter_claim_number(lv_claim_number))
    if lv_start_date and lv_end_date:
        where_conds.append(db.get_filter_claim_dates(lv_start_date,lv_end_date))
    
    if len(where_conds)>0:
        logging.debug("Callback change_dropdown_claim_type list of non-null inputs: {}".format(where_conds))
        df = db.get_multiple_filter(where_conds)
    else:
        logging.debug("Callback change_dropdown_claim_type: all inputs are None.")
        df = db.get_claims_top10()
        
    df = calculate(df)
    
    data=df.to_dict('records')
    logging.debug('Created data dictionary')
    logging.info("Tab 1 table data: ".format(data))
    claim_numbers_string = ','.join(df['claim_no'].astype(str).tolist())
    logging.debug('Created string of claim numbers present in tab 1 table')
    logging.info("Claim_numbers_string: ".format(claim_numbers_string))

    return data, claim_numbers_string, []

# Tab 2 callback for selected claim in Claims table
@app.callback(Output('table_claim_details', 'data'),
             [Input('claim_numbers','children'),
              Input('table_claims','selected_rows')])
def table_claim_select_row(claim_numbers_string, selected_rows):
    data = []
    logging.debug("Callback table_claim_select_row received inputs {}".format(claim_numbers_string,selected_rows))
    logging.info("Callback table_claim_select_row string of claim numbers present in tab 1: {}".format(claim_numbers_string))
    logging.info("Callback table_claim_select_row selected row: {}".format(selected_rows))
    
    ctx = dash.callback_context
    trigger_id = ctx.triggered[0]['prop_id'].split('.')[0]
    logging.debug("Callback table_claim_select_row input trigger id: {}".format(trigger_id))
    
    if selected_rows and (active_type == 'sqlite') and (selected_rows[0] >= 0) and (selected_rows[0] <= len(claim_numbers_string)/2):
        claim_numbers_list = claim_numbers_string.split(',') 
        claim_no = claim_numbers_list[selected_rows[0]]
        logging.debug("Obtained claim number of selected row: ".format(claim_no))
        logging.info("Claim number of selected row: ".format(claim_no))
        
        parameters = {"claim_no":claim_no,"full_path":path+name}
        response = requests.post("http://127.0.0.1:5000/", json=parameters, timeout=10)
        logging.debug("Sent API request for tab 2 table data")
        ret_status = response.status_code
        logging.debug("API request for tab 2 table data returned status code: ".format(ret_status))
        logging.info("API Call return status code: ".format(ret_status))
        
        if ret_status == 200:
            x = response.json()
            logging.debug("Retrieved dictionary from API call")
            logging.info("Received from API call: ".format(x))
            for k,v in x.items():
                data.append({'COLUMN_NAME':k,'COLUMN_VALUE':v})
            logging.debug("Created list of dictionaries with keys COLUMN_NAME and COLUMN_VALUE")
    logging.info("Data to return:".format(data))
    return data

if __name__ == '__main__':
    app.run_server(debug=False)




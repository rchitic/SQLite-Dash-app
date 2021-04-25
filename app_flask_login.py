#import dependencies
#manage database and users
import logging
logging.basicConfig(filename='app.log', level=logging.DEBUG)

import sqlite3
from sqlalchemy import Table, create_engine
from sqlalchemy.sql import select
from flask import session
from flask_sqlalchemy import SQLAlchemy
from flask_login import login_user, logout_user, current_user, LoginManager, UserMixin
#manage password hashing
from werkzeug.security import generate_password_hash, check_password_hash
#use to config server
import warnings
import configparser
import os
#dash dependencies
import dash_core_components as dcc
import dash_html_components as html
import dash
import dash_auth
import dash_table
from dash.dependencies import Input, Output, State
#other
import pandas as pd
import datetime
from datetime import date
import ast
import json
import requests
#own business modules
from business import calculate

# Read DB type and import corresponding class
config = configparser.ConfigParser()
config.read('config.txt')
active_type = config.get('db_types', 'active_type')
logging.info("Database type: {}".format(active_type))

if active_type == 'sqlite':
    from DB import SQLite
    name = config.get('db_names','db_name_o')
    path = config.get('sqlite_paths', 'db_path_o')
    db = SQLite(name,path)
    engine = create_engine('sqlite:///'+path+name)
    sqlalchemy_database_uri ='sqlite:///'+path+name
elif active_type == 'postgres':
    from DB import Postgres
    name = config.get('db_names','db_name_o').split('.')[0]
    user = config.get('postgres_users', 'user')
    password = config.get('postgres_passwords', 'password')
    db = Postgres(name, user, password)
    engine = create_engine('postgresql+psycopg2://' + user + ':' + password + '@localhost/' + name)
    sqlalchemy_database_uri = 'postgresql+psycopg2://' + user + ':' + password + '@localhost/' + name

# Get static DataFrames
df_claim_types = db.get_distinct_claim_types()
df_claim_status = db.get_distinct_claim_status()
df_claims = db.get_claim_empty_rec()
df_claim_details = db.get_claim_details_empty_rec()

lv_claims_filter = ""
lv_claim_types  = []
lv_claim_status = []
lv_user_id = None

from flask import Flask
warnings.filterwarnings("ignore")
#connect to SQLite database
db_alch = SQLAlchemy()
config = configparser.ConfigParser()
#create users class for interacting with users table
class Users(db_alch.Model):
    id = db_alch.Column(db_alch.Integer, primary_key=True)
    username = db_alch.Column(db_alch.String(15), unique=True, nullable = False)
    email = db_alch.Column(db_alch.String(50), unique=True)
    password = db_alch.Column(db_alch.String(80))
Users_tbl = Table('users', Users.metadata)
#instantiate dash apps
server = Flask(__name__)
#server = app1.server
app = dash.Dash(__name__, server=server)
app.config.suppress_callback_exceptions = True
#config the server to interact with the database
#Secret Key is used for user sessions
server.config.update(
    SECRET_KEY=os.urandom(12),
    SQLALCHEMY_DATABASE_URI=sqlalchemy_database_uri,
    SQLALCHEMY_TRACK_MODIFICATIONS=False
)
db_alch.init_app(server)

# Setup the LoginManager for the server
login_manager = LoginManager()
login_manager.init_app(server)
login_manager.login_view = '/login'

#User as base
# Create User class with UserMixin
class Users(UserMixin, Users):
    pass

#Dash display settings
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

#------------------------------------------------------------------------------------------------------------------------------
#Layout
#------------------------------------------------------------------------------------------------------------------------------

create = html.Div([ html.H1('Create User Account')
        , dcc.Location(id='create_user', refresh=True)
        , dcc.Input(id="username"
            , type="text"
            , placeholder="user name"
            , maxLength =15)
        , dcc.Input(id="password"
            , type="password"
            , placeholder="password")
        , dcc.Input(id="email"
            , type="email"
            , placeholder="email"
            , maxLength = 50)
        , html.Button('Create User', id='submit-val', n_clicks=0)
        , html.Div(id='container-button-basic')
    ])#end div

login =  html.Div([dcc.Location(id='url_login', refresh=True)
            , html.H2('''Please log in to continue:''', id='h1')
            , dcc.Input(placeholder='Enter your username',
                    type='text',
                    id='uname-box')
            , dcc.Input(placeholder='Enter your password',
                    type='password',
                    id='pwd-box')
            , html.Button(children='Login',
                    n_clicks=0,
                    type='submit',
                    id='login-button')
            , html.Div(children='', id='output-state'),
        ]) #end div

main_dash =  html.Div([
                dcc.Link('Go to Analytics', href='/analytics/'),
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
                            end_date_placeholder_text='End date'
                        )]),
                        html.Br(),
                        html.Button('Go', id='go-val', n_clicks=0, style={'justify':'center'}),
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
                ),
                html.Div(id='claim_numbers', style={'display': 'none'}),
            ])

analytics = html.Div([ dcc.Location(id='analytics', refresh=True)
                , html.Div([dcc.Link('Go to main page', href='/main/'),
                        html.H1('Analytics', style={'text-align':'center'}),
                        dcc.Graph(
                            id='graph_count_actions',
                            figure={
                                'data': [
                                    {'x': db.get_count_actions()["object"].tolist(), 'y': db.get_count_actions()["COUNT(*)"].tolist(), 'type': 'bar', 'name': 'SF'},
                                ],
                                'layout': {
                                    'title': 'Count actions'
                                }
                            }
                        ),
                        dcc.Graph(
                            id='graph_count_claim_types',
                            figure={
                                'data': [
                                    {'x': db.get_count_claim_types()["value"].tolist(), 'y': db.get_count_claim_types()["COUNT(*)"].tolist(), 'type': 'bar', 'name': 'SF'},
                                ],
                                'layout': {
                                    'title': 'Count claim types'
                                }
                            }
                        ),
                        dcc.Graph(
                            id='graph_count_claim_status',
                            figure={
                                'data': [
                                    {'x': db.get_count_claim_status()["value"].tolist(), 'y': db.get_count_claim_status()["COUNT(*)"].tolist(), 'type': 'bar', 'name': 'SF'},
                                ],
                                'layout': {
                                    'title': 'Count claim status'
                                }
                            }
                        )
                       #dcc.Dropdown(id='dropdown_user_id',
                       #             options=[{'label':i, 'value':i} for i in db.get_count_actions()],
                       #             placeholder="Select a user id",
                       #             value = lv_user_id
                       # ),
                       #html.Div(id='display_selected_user_id'),
              ])
          ])

failed = html.Div([ dcc.Location(id='url_login_df', refresh=True)
            , html.Div([html.H2('Log in Failed. Please try again.')
                    , html.Br()
                    , html.Div([login])
                    , html.Br()
                    , html.Button(id='back-button', children='Go back', n_clicks=0)
                ]) #end div
        ]) #end div

logout = html.Div([dcc.Location(id='logout', refresh=True)
        , html.Br()
        , html.Div(html.H2('You have been logged out - Please login'))
        , html.Br()
        , html.Div([login])
        , html.Button(id='back-button', children='Go back', n_clicks=0)
    ])#end div

app.layout= html.Div([
            html.Div(id='page-content', className='content')
            ,  dcc.Location(id='url', refresh=False),
        ])
#------------------------------------------------------------------------------------------------------------------------------
# Login callbacks
#------------------------------------------------------------------------------------------------------------------------------

# callback to reload the user object
@login_manager.user_loader
def load_user(user_id):
    return Users.query.get(int(user_id))

@server.route('/')
def render_login():
    return app.index()

@app.callback(
    Output('page-content', 'children')
    , [Input('url', 'pathname')])
def display_page(pathname):
    print("PATHNAME ",pathname)
    if pathname == '/':
        return login
    elif pathname == '/main/':
        if current_user.is_authenticated:
            return main_dash
        else:
            return failed
    elif pathname == '/analytics/':
        if current_user.is_authenticated:
            return analytics
        else:
            return failed
    elif pathname == '/logout':
        if current_user.is_authenticated:
            logout_user()
            return logout
        else:
            return logout
    else:
        return '404'
    
#set the callback for the dropdown interactivity
@app.callback(
    [Output('graph', 'figure')]
    , [Input('dropdown', 'value')])
def update_graph(dropdown_value):
    if dropdown_value == 'Day 1':
        return [{'layout': {'title': 'Graph of Day 1'}
                , 'data': [{'x': [1, 2, 3, 4]
                    , 'y': [4, 1, 2, 1]}]}]
    else:
        return [{'layout': {'title': 'Graph of Day 2'}
                ,'data': [{'x': [1, 2, 3, 4]
                    , 'y': [2, 3, 2, 4]}]}]
@app.callback(
   [Output('container-button-basic', "children")]
    , [Input('submit-val', 'n_clicks')]
    , [State('username', 'value'), State('password', 'value'), State('email', 'value')])
def insert_users(n_clicks, un, pw, em):
    hashed_password = generate_password_hash(pw, method='sha256')
    if un is not None and pw is not None and em is not None:
        ins = Users_tbl.insert().values(username=un,  password=hashed_password, email=em,)
        conn = engine.connect()
        conn.execute(ins)
        conn.close()
        return [login]
    else:
        return [html.Div([html.H2('Already have a user account?'), dcc.Link('Click here to Log In', href='/login')])] 
    
@app.callback(
    Output('url_login', 'pathname')
    , [Input('login-button', 'n_clicks')]
    , [State('uname-box', 'value'), State('pwd-box', 'value')])
def successful(n_clicks, input1, input2):
    user = Users.query.filter_by(username=input1).first()
    if user:
        if check_password_hash(user.password, input2):
            user_id = user.id
            login_user(user)
            db.insert_user_action([str(user_id),"'login'","'successful'","'{}'".format(str(datetime.datetime.now()))])
            return '/main'
        else:
            pass
    else:
        pass
    
@app.callback(
    Output('output-state', 'children')
    , [Input('login-button', 'n_clicks')]
    , [State('uname-box', 'value'), State('pwd-box', 'value')])
def update_output(n_clicks, input1, input2):
    if n_clicks > 0:
        user = Users.query.filter_by(username=input1).first()
        if user:
            if check_password_hash(user.password, input2):
                return ''
            else:
                return 'Incorrect username or password'
        else:
            return 'Incorrect username or password'
    else:
        return ''
@app.callback(
    Output('url_login_success', 'pathname')
    , [Input('back-button', 'n_clicks')])
def logout_dashboard(n_clicks):
    if n_clicks > 0:
        return '/'
@app.callback(
    Output('url_login_df', 'pathname')
    , [Input('back-button', 'n_clicks')])
def logout_dashboard(n_clicks):
    if n_clicks > 0:
        return '/'
# Create callbacks
@app.callback(
    Output('url_logout', 'pathname')
    , [Input('back-button', 'n_clicks')])
def logout_dashboard(n_clicks):
    if n_clicks > 0:
        return '/'
    
#------------------------------------------------------------------------------------------------------------------------------
#Content callbacks
#------------------------------------------------------------------------------------------------------------------------------

# Tab 1 callback
@app.callback([Output('table_claims', 'data'),
               Output('claim_numbers','children'),
               Output('table_claims', 'selected_rows')],
              [Input('go-val', 'n_clicks'),
               State('dropdown_claim_type', 'value'),
               State('dropdown_claim_status', 'value'),
               State('input_claim_number', 'value'),
               State('date_picker_range', 'start_date'),
               State('date_picker_range', 'end_date')])
               
def change_dropdown_claim_type(n_clicks,claim_types,claim_status,claim_number,start_date,end_date):
    ctx = dash.callback_context
    trigger_id = ctx.triggered[0]['prop_id'].split('.')[0]
    if trigger_id == 'go-val': #if 'go' button was clicked
        lv_claim_types = claim_types
        lv_claim_status = claim_status
        lv_claim_number = claim_number
        lv_start_date = start_date
        lv_end_date = end_date
        logging.info("Selected types: {}".format(lv_claim_types))
        logging.info("Selected status: {}".format(lv_claim_status))
        logging.info("Selected number: {}".format(lv_claim_number))
        logging.info("Selected start date: {}".format(lv_start_date))
        logging.info("Selected end date: {}".format(lv_end_date))

        user_id = current_user.get_id()
        where_conds = []
        if lv_claim_types:
            where_conds.append(db.get_filter_claim_types(lv_claim_types))
            db.insert_user_action([str(user_id),"'dropdown claim types'","'{}'".format(",".join(lv_claim_types)),"'{}'".format(str(datetime.datetime.now()))])
        if lv_claim_status:
            where_conds.append(db.get_filter_claim_status(lv_claim_status))  
            db.insert_user_action([str(user_id),"'dropdown claim status'","'{}'".format(",".join(lv_claim_status)),"'{}'".format(str(datetime.datetime.now()))])
        if lv_claim_number:
            where_conds.append(db.get_filter_claim_number(lv_claim_number))
            db.insert_user_action([str(user_id),"'edit box claim number'","'{}'".format(",".join(lv_claim_number)),"'{}'".format(str(datetime.datetime.now()))])
        if lv_start_date and lv_end_date:
            where_conds.append(db.get_filter_claim_dates(lv_start_date,lv_end_date))
            db.insert_user_action([str(user_id),"'date range'","'{}'".format(",".join([lv_start_date,lv_end_date])),"'{}'".format(str(datetime.datetime.now()))])

        if len(where_conds)>0:
            df = db.get_multiple_filter(where_conds)
        else:
            df = db.get_claims_top10()

        df = calculate(df)
        data=df.to_dict('records')
        claim_numbers_string = ','.join(df['claim_no'].astype(str).tolist())
    
    elif n_clicks == 0:
        df = db.get_claims_top10()
        df = calculate(df)
        data=df.to_dict('records')
        
    claim_numbers_string = ','.join(df['claim_no'].astype(str).tolist())
    logging.info("Table data: {}".format(data))
    logging.info("Claim_numbers_string: ".format(claim_numbers_string))
    return data, claim_numbers_string, []

# Tab 2 callback for selected claim in Claims table
@app.callback(Output('table_claim_details', 'data'),
             [Input('claim_numbers','children'),
              Input('table_claims','selected_rows')])
def table_claim_select_row(claim_numbers_string, selected_rows):
    data = []
    
    ctx = dash.callback_context
    trigger_id = ctx.triggered[0]['prop_id'].split('.')[0]
    logging.info("trigger id: {}".format(trigger_id))
    logging.info("Claim_numbers_string fn2: {}".format(claim_numbers_string))
    logging.info("Selected row: {}".format(selected_rows))
    
    if selected_rows and (active_type == 'sqlite') and (selected_rows[0] >= 0) and (selected_rows[0] <= len(claim_numbers_string)/2):
        selected_row_ids = selected_rows
        claim_numbers_list = claim_numbers_string.split(',') 
        claim_no = claim_numbers_list[selected_rows[0]]
        logging.info("Claim no: {}".format(claim_no))
        parameters = {"claim_no":claim_no, "full_path":path+name}
        response = requests.post("http://127.0.0.1:5000/", json=parameters, timeout=10)
        ret_status = response.status_code
        logging.info("API Call return status code: ".format(ret_status))
        if ret_status == 200:
            x = response.json()
            logging.info("response text: ".format(x))
            for k,v in x.items():
                data.append({'COLUMN_NAME':k,'COLUMN_VALUE':v})
            
    logging.info("Data to return: ".format(data))
    return data

# Analytics callbacks
# Dropdown user id
# TODO

#------------------------------------------------------------------------------------------------------------------------------
if __name__ == '__main__':
    #app.run_server(debug=False)
    server.run(port=5001,threaded=True)




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

config = configparser.ConfigParser()
config.read('config.txt')
VALID_USERNAME_PASSWORD_PAIRS = ast.literal_eval(config.get('authentication', 'username_password_pairs'))
lv_db_path = config.get('paths', 'db_path_o')
lv_db_name = config.get('db_names','db_name_a')
lv_db_full_path = lv_db_path + lv_db_name
#lv_db_conn = sqlite3.connect(lv_db_full_path)

def get_distinct_claim_types():
    with sqlite3.connect(lv_db_full_path) as conn:
        q_claims_types = "SELECT DISTINCT claim_type FROM CLAIMS;"
        df_claims_types = pd.read_sql_query(q_claims_types,conn)
    return df_claims_types

def get_distinct_claim_status():
    with sqlite3.connect(lv_db_full_path) as conn:
        q_claims_status = "SELECT DISTINCT claim_status FROM CLAIMS;"
        df_claims_status = pd.read_sql_query(q_claims_status,conn)
    return df_claims_status

def get_claim_empty_rec():
    with sqlite3.connect(lv_db_full_path) as conn:
        q_claims_empty_rec  = "SELECT c.*, '' AS CALCULATED_FIELD FROM CLAIMS c WHERE 1=2;"
        df_claims   = pd.read_sql_query(q_claims_empty_rec,conn)#,index_col=['claim_no'])
    #df_claims   = df_claims.set_index("claim_no", drop = False)
    return df_claims

def get_claim_details_empty_rec():
    with sqlite3.connect(lv_db_full_path) as conn:
        q_claims_details = "SELECT '' AS COLUMN_NAME,'' AS 'COLUMN_VALUE'"
        df_claims_details = pd.read_sql_query(q_claims_details,conn)
    return df_claims_details

def get_claims_top10():
    with sqlite3.connect(lv_db_full_path) as conn:
        q_claims_top10 = "SELECT * FROM CLAIMS LIMIT 10"
        df_claims_top10 = pd.read_sql_query(q_claims_top10,conn)
    return df_claims_top10    

def get_filter_claim_types(claim_types):
    '''
    with sqlite3.connect(lv_db_full_path) as conn:
        lv_filter = "'" + "','".join(claim_types) + "'"
        q_filter_claim_types = "SELECT * FROM CLAIMS WHERE claim_type IN (" + lv_filter + ") LIMIT 10"
        df_filter_claim_types = pd.read_sql_query(q_filter_claim_types,conn) 
    '''
    lv_filter = "'" + "','".join(claim_types) + "'"
    q_filter_claim_types = "claim_type IN (" + lv_filter + ")"
    return q_filter_claim_types
    
def get_filter_claim_status(claim_status):
    '''
    with sqlite3.connect(lv_db_full_path) as conn:
        lv_filter = "'" + "','".join(claim_status) + "'"
        q_filter_claim_status = "SELECT * FROM CLAIMS WHERE claim_status IN (" + lv_filter + ") LIMIT 10"
        df_filter_claim_status = pd.read_sql_query(q_filter_claim_status,conn)  
    '''
    lv_filter = "'" + "','".join(claim_status) + "'"
    q_filter_claim_status = "claim_status IN (" + lv_filter + ")"
    return q_filter_claim_status
    
def get_filter_claim_number(claim_number):
    '''
    with sqlite3.connect(lv_db_full_path) as conn:
        q_filter_claim_number = "SELECT * FROM CLAIMS WHERE claim_no LIKE " + claim_number + "%"
        df_filter_claim_number = pd.read_sql_query(q_filter_claim_number,conn) 
    '''
    q_filter_claim_number = "claim_no LIKE '" + claim_number + "%'"
    return q_filter_claim_number
    
def get_filter_claim_dates(claim_start_date,claim_end_date):
    '''
    with sqlite3.connect(lv_db_full_path) as conn:
        lv_filter = "'" + "','".join(lv_claim_number) + "'"
        q_filter_claim_dates = "SELECT * FROM CLAIMS WHERE claim_date BETWEEN " + lv_filter + "%"
        df_filter_claim_dates = pd.read_sql_query(q_filter_claim_dates,conn)
    '''
    q_filter_claim_dates = "claim_date BETWEEN '" + claim_start_date + "' AND '" + claim_end_date + "' LIMIT 10"
    return q_filter_claim_dates

def get_multiple_filter(where_conds):
    with sqlite3.connect(lv_db_full_path) as conn:
        query = "SELECT * FROM CLAIMS WHERE " + " AND ".join(where_conds)
        print("Multiple filter query: ",query)
        df = pd.read_sql_query(query,conn)
    return df
import pandas as pd
import sqlite3
import psycopg2
from datetime import date
import configparser
import ast
import logging

import dash
import dash_table
import dash_auth
import dash_html_components as html
import dash_core_components as dcc
from dash.dependencies import Input, Output

import json
import requests

'''
config = configparser.ConfigParser()
config.read('config.txt')
VALID_USERNAME_PASSWORD_PAIRS = ast.literal_eval(config.get('authentication', 'username_password_pairs'))
lv_db_path = config.get('paths', 'db_path_o')
lv_db_name = config.get('db_names','db_name_o')
lv_db_full_path = lv_db_path + lv_db_name
'''

class DB(object):
    def __init__(self, conn):
        self.conn = conn
        
    def get_distinct_claim_types(self):
        #with sqlite3.connect(self.path) as conn:
        try:
            q_claims_types = "SELECT DISTINCT claim_type FROM CLAIMS;"
            df_claims_types = pd.read_sql_query(q_claims_types,self.conn)
            logging.debug('Obtained DataFrame of distinct types from CLAIMS table')
            return df_claims_types
        except Exception as e:
            logging.error('Could not obtain distinct claim types from CLAIMS table' + str(e))

    def get_distinct_claim_status(self):
        #with sqlite3.connect(self.path) as conn:
        try:
            q_claims_status = "SELECT DISTINCT claim_status FROM CLAIMS;"
            df_claims_status = pd.read_sql_query(q_claims_status,self.conn)
            logging.debug('Obtained DataFrame of distinct status from CLAIMS table')
            return df_claims_status
        except Exception as e:
            logging.error('Could not obtain distinct status from CLAIMS table' + str(e))        

    def get_claim_empty_rec(self):
        try:
            q_claims_empty_rec  = "SELECT c.*, '' AS CALCULATED_FIELD FROM CLAIMS c WHERE 1=2;"
            df_claims   = pd.read_sql_query(q_claims_empty_rec,self.conn)
            logging.debug('Obtained DataFrame of empty records from CLAIMS table')
            return df_claims
        except Exception as e:
            logging.error('Could not obtain DataFrame of empty records from CLAIMS table' + str(e)) 

    def get_claim_details_empty_rec(self):
        try:
            q_claims_details = "SELECT '' AS COLUMN_NAME,'' AS 'COLUMN_VALUE'"
            df_claims_details = pd.read_sql_query(q_claims_details,self.conn)
            logging.debug('Obtained DataFrame of empty records from CLAIMS_DETAILS table')
            return df_claims_details
        except Exception as e:
            logging.error('Could not obtain DataFrame of empty records from CLAIMS_DETAILS table' + str(e))         

    def get_claims_top10(self):
        try:
            q_claims_top10 = "SELECT * FROM CLAIMS LIMIT 10"
            df_claims_top10 = pd.read_sql_query(q_claims_top10,self.conn)
            logging.debug('Obtained DataFrame of top 10 records from CLAIMS table')
            return df_claims_top10
        except Exception as e:
            logging.error('Could not obtain DataFrame of top 10 records from CLAIMS table' + str(e))   
            
    def get_filter_claim_types(self,claim_types):
        try:
            lv_filter = "'" + "','".join(claim_types) + "'"
            q_filter_claim_types = "claim_type IN (" + lv_filter + ")"
            logging.debug('Created query to filter claim types from CLAIMS table')
            return q_filter_claim_types
        except Exception as e:
            logging.error('Could not create query to filter claim types from CLAIMS table' + str(e))

    def get_filter_claim_status(self,claim_status):
        try:
            lv_filter = "'" + "','".join(claim_status) + "'"
            q_filter_claim_status = "claim_status IN (" + lv_filter + ")"
            logging.debug('Created query to filter claim status from CLAIMS table')
            return q_filter_claim_status
        except Exception as e:
            logging.error('Could not create query to filter claim status from CLAIMS table' + str(e))        

    def get_filter_claim_number(self,claim_number):
        try:
            q_filter_claim_number = "claim_no LIKE '" + claim_number + "%'"
            logging.debug('Created query to filter claim number from CLAIMS table')
            return q_filter_claim_number
        except Exception as e:
            logging.error('Could not create query to filter claim number from CLAIMS table' + str(e))
            
    def get_filter_claim_dates(self,claim_start_date,claim_end_date):
        try:
            q_filter_claim_dates = "claim_date BETWEEN '" + claim_start_date + "' AND '" + claim_end_date + "' LIMIT 10"
            logging.debug('Created query to filter claim dates from CLAIMS table')
            return q_filter_claim_dates
        except Exception as e:
            logging.error('Could not create query to filter claim dates from CLAIMS table' + str(e))
            
    def get_multiple_filter(self,where_conds):
        try:
            query = "SELECT * FROM CLAIMS WHERE " + " AND ".join(where_conds)
            df = pd.read_sql_query(query,self.conn)
            logging.debug('Obtained DataFrame filtered on multiple conditions from CLAIMS table')
            logging.info("Created the following query for filtering CLAIMS: {}".format(query))
            return df
        except Exception as e:
            logging.error('Could not obtain DataFrame filtered on multiple conditions from CLAIMS table' + str(e))
            
    def get_user_id(self):
        try:
            q_user_id = "SELECT user_id FROM USER_ACTIONS ORDER BY rowid DESC LIMIT 1;"
            df_user_id = pd.read_sql_query(q_user_id,self.conn)
            logging.debug("Obtained user id from USER_ACTIONS table: {}".format(df_user_id["user_id"][0]))
            return df_user_id["user_id"][0]
        except Exception as e:
            logging.error('Could not obtain user id from Users table: ' + str(e))
            
    def insert_user_action(self,action):
        try:
            cursor = self.conn.cursor()
            q_insert_action = "INSERT INTO USER_ACTIONS(user_id,object,value,timestamp) VALUES(" + ",".join(action) + ")"
            count = cursor.execute(q_insert_action)
            self.conn.commit()
            cursor.close()
            logging.debug("Inserted action in USERS_ACTION table: {}".format(action))
        except Exception as e:
            logging.error('Could not insert action in USERS_ACTION table: ' + str(e))    
            
    def get_count_actions(self):
        try:
            q_count = "SELECT object, COUNT(*) FROM USER_ACTIONS GROUP BY object"
            df_count = pd.read_sql_query(q_count,self.conn)
            logging.debug("Obtained count of actions from USERS_ACTION table")
            return df_count
        except Exception as e:
            logging.error("Could not obtain count of actions from USERS_ACTION table: " + str(e)) 
            
    def get_count_claim_types(self):
        try:
            q_count = "SELECT value, COUNT(*) FROM USER_ACTIONS WHERE object = "+"'dropdown claim types'"+" GROUP BY value"
            df_count = pd.read_sql_query(q_count,self.conn)
            logging.debug("Obtained count of claim types from USERS_ACTION table")
            return df_count
        except Exception as e:
            logging.error("Could not obtain count of claim types from USERS_ACTION table: " + str(e))  

    def get_count_claim_status(self):
        try:
            q_count = "SELECT value, COUNT(*) FROM USER_ACTIONS WHERE object = "+"'dropdown claim status'"+" GROUP BY value"
            df_count = pd.read_sql_query(q_count,self.conn)
            logging.debug("Obtained count of claim status from USERS_ACTION table")
            return df_count
        except Exception as e:
            logging.error("Could not obtain count of claim status from USERS_ACTION table: " + str(e))              
            
class SQLite(DB):
    def __init__(self, name, path):
        full_path = path + name
        conn = sqlite3.connect(full_path,check_same_thread=False)
        super().__init__(conn)
        
class Postgres(DB):
    def __init__(self, name, user, password):
        conn = psycopg2.connect("dbname=" + name + " user=" + user + " password=" + password)
        super(Postgres,self).__init__(conn)
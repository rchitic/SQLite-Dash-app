import pandas as pd
import sqlite3
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

def calculate(df):
    df["CALCULATED_FIELD"] = df["claim_amount"]*2
    logging.debug('Performed calculation for CALCULATED_FIELD of CLAIMS table')
    return df
    
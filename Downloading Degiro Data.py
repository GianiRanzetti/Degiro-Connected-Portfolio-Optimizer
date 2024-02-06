# IMPORTATIONS
import json
import pandas as pd
import logging
import datetime as dt
import plotly
import plotly.graph_objects as go
from plotly.subplots import make_subplots
import plotly.express as px
import plotly.figure_factory as ff
import numpy as np
from tqdm import tqdm

import degiro_connector.core.helpers.pb_handler as pb_handler
from IPython.display import display
from degiro_connector.trading.api import API as TradingAPI
from degiro_connector.trading.models.trading_pb2 import Credentials, Update, ProductsInfo

import eikon as ek
import refinitiv.dataplatform as rdp

# SETUP LOGGING LEVEL
logging.basicConfig(level=logging.DEBUG)

# SETUP CONFIG DICTIONARY
with open("config.json") as config_file:
    config_dict = json.load(config_file)

# SETUP CREDENTIALS
user_token = config_dict.get("user_token")
int_account = int(config_dict.get("int_account"))
username = config_dict.get("username")
password = config_dict.get("password")

credentials = Credentials(
    int_account= int_account,
    username=username,
    password=password,
)

# SETUP TRADING API
trading_api = TradingAPI(credentials=credentials)

# CONNECT
trading_api.connect()


# SETUP REQUEST
request_list = Update.RequestList()
request_list.values.extend(
    [
        Update.Request(option=Update.Option.ORDERS, last_updated=0),
        Update.Request(option=Update.Option.PORTFOLIO, last_updated=0),
        Update.Request(option=Update.Option.TOTALPORTFOLIO, last_updated=0),
    ]
)

# FETCH DATA
update = trading_api.get_update(request_list=request_list, raw=False)
update_dict = pb_handler.message_to_dict(message=update)

# DISPLAY DATA
if "orders" in update_dict:
    orders_df = pd.DataFrame(update_dict["orders"]["values"])
    print("orders")
    display(orders_df)

if "portfolio" in update_dict:
    portfolio_df = pd.DataFrame(update_dict["portfolio"]["values"])
    portfolio_df = portfolio_df[portfolio_df["value"] != 0]
    portfolio_df = portfolio_df.sort_values(by="value", ascending=False)
    portfolio_df.reset_index(drop=True, inplace=True)
    print("portfolio")
    display(portfolio_df)

if "total_portfolio" in update_dict:
    total_portfolio_df = pd.DataFrame(update_dict["total_portfolio"]["values"])
    print("total_portfolio")
    display(total_portfolio_df)

portfolio_df['value'] = pd.to_numeric(portfolio_df['value'], errors='coerce')
portfolio_df['weights'] = portfolio_df['value'] / total_portfolio_df.loc['EUR', 'reportNetliq']
print("portfolio")
display(portfolio_df)

# SETUP REQUEST
request = ProductsInfo.Request()
request.products.extend(pd.to_numeric(portfolio_df["id"][:-1])) # EUR not included!!

# FETCH DATA
products_info = trading_api.get_products_info(
    request=request,
    raw=True,
)

# DISPLAY PRODUCTS_INFO
print(products_info)

# Initialize empty lists to collect data
index_list = []
name_list = []
type_list = []
isin_list = []
ticker_list = []

# Extract data from the dictionary
for key, value in products_info['data'].items():
    index_list.append(key)
    type_list.append(value['productType'])
    name_list.append(value['name'])
    isin_list.append(value['isin'])
    ticker_list.append(value['symbol'])

# Create a DataFrame
summary_df = pd.DataFrame({'id': index_list, 'Name': name_list, 'ISIN': isin_list, "Ticker": ticker_list, "Asset Type": type_list})
cash = {'id': 'EUR', 'Name': 'Cash Account', 'ISIN': None, "Ticker": None, "Asset Type":"CASH"}
summary_df = summary_df.append(cash, ignore_index=True)
summary_df= summary_df.merge(portfolio_df[['id','weights']], on='id', how='left')

# Display the DataFrame
pd.set_option('display.max_columns', None)
print(summary_df)

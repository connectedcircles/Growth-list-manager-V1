import streamlit as st
import pandas as pd
from google.oauth2 import service_account
import pygsheets
import pyodbc
import json







##### LOCAL AUTHENTICATION ####################################################
# Authenticate Google Sheets API
#creds = service_account.Credentials.from_service_account_file(
#    'C:/Users/HP/Downloads/credentials.json',
#    scopes=['https://spreadsheets.google.com/feeds']
#)
### Define connection credentials to SQL database
#conn_str = "Driver={ODBC Driver 17 for SQL Server};Server=circulus-data.database.windows.net;Database=circulus-database;UID=circulus_admin;PWD=ZKv25YQq8k9Kv86f;"
###############################################################################


##### CLOUD AUTHENTICATION ####################################################
# Authenticate Google Sheets API
raw_creds = st.secrets["raw_creds"]
json_creds = json.loads(raw_creds)

creds = service_account.Credentials.from_service_account_info(
    json_creds,
    scopes=['https://spreadsheets.google.com/feeds']
)



conn_str = st.secrets["conn_str"] 
###############################################################################


###############################################################################

def get_all_connections():
    conn = pyodbc.connect(conn_str)
    query = "SELECT * FROM ProfilesX"
    df = pd.read_sql(query, conn)
    conn.close()
    return df

def get_invited_profiles():
    gc = pygsheets.authorize(custom_credentials=creds)
    spreadsheet = gc.open_by_url("https://docs.google.com/spreadsheets/d/1QWhVtOPoOoYVdxoUtM5RKAhwJKVW-6-q6T5ACZJVkdU/edit#gid=1820302186")
    worksheet = spreadsheet.worksheet_by_title("Invited")
    records = worksheet.get_all_records()
    df = pd.DataFrame(records)
    return df

def get_engagers_group():
    gc = pygsheets.authorize(custom_credentials=creds)
    spreadsheet = gc.open_by_url("https://docs.google.com/spreadsheets/d/19cgiKVQM1ShW9R8JzdWuPVAcXqbPnDbavyeLQyixQxo/edit?gid=0#gid=0")
    worksheet = spreadsheet.worksheet_by_title("Engagers")
    records = worksheet.get_all_records()
    df = pd.DataFrame(records)
    return df


def make_clickable_link(val):
    """Return a clickable URL with the text 'URL'"""
    return f'<a target="_blank" href="{val}">URL</a>'


def main():
    st.title("Recent Connections Engagement Assistant")
    st.write("""Engage with most recent connections that were invited by CC by clicking the Posts' URL. Connections
             are sorted from most recent to least recent. MAINTENANCE: In case of "pyodbc.ProgrammingError:" contact Data Team. 
             Data Team: Manage App (lower right hand corner of the app) -> Copy the IP adress -> add firewall rule in Azure Portal.
             https://portal.azure.com/#@connectedcircles.net/resource/subscriptions/61171ae4-c392-4dca-9ad4-880921a42770/resourceGroups/circulus-api/providers/Microsoft.Sql/servers/circulus-data/networking""")
             
   
            
    # Obtain data
    df_connections = get_all_connections()
    
    df_engagers = get_engagers_group()
    #df_invited['Posts_URL'] = df_invited['Profile URL'] + '/recent-activity/all/'

    # Get unique clients for the dropdown menu
    unique_clients = df_connections['Client'].unique()

    # Dropdown menu for Client
    Client_Name = st.selectbox("Select Client", unique_clients)

    st.title("Create a group")
    st.write("Search for the people from the list")
    
    
    #get the full list of connections 
    connections = get_all_connections()
    #get connections for the selected client
    get_connections = connections[connections["Client"]==Client_Name]["Name"]
    
    engagers_list = st.multiselect("select names to include in the engage group", get_connections)







if __name__ == '__main__':
    main()

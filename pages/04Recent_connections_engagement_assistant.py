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

def make_clickable_link(val):
    """Return a clickable URL with the text 'URL'"""
    return f'<a target="_blank" href="{val}">URL</a>'


def main():
    st.title("Recent Connections Engagement Assistant")
    st.write("""Engage with most recent connections that were invited by CC by clicking the Posts' URL. Connections
             are sorted from most recent to least recent.""")

    # Obtain data
    df_connections = get_all_connections()
    df_invited = get_invited_profiles()
    df_invited.rename(columns={'Full name': 'Name'}, inplace=True)
    df_invited['Posts_URL'] = df_invited['Profile URL'] + '/recent-activity/all/'

    # Get unique clients for the dropdown menu
    unique_clients = df_connections['Client'].unique()

    # Dropdown menu
    Client_Name = st.selectbox("Select Client", unique_clients)

    df_invited_client_specific = df_invited[df_invited['Client Name'] == Client_Name]
    df_connections_client_specific = df_connections[df_connections['Client'] == Client_Name]
    
    df_accepted = pd.merge(df_invited_client_specific, df_connections_client_specific[['Name','ProfileDate']], on='Name', how='inner')
    df_accepted_display = df_accepted[["Name", "Title", "Profile URL", "Posts_URL", "Followers", "Category", "Date collected", "ProfileDate"]]
    df_accepted_display.rename(columns={'Posts_URL': 'Posts URL', "Date collected": 'Invited on', 'ProfileDate': 'Connected on (approximate)'}, inplace=True)
    df_accepted_display = df_accepted_display.sort_values(by='Connected on (approximate)', ascending=False)

    # Convert URLs to clickable icons
    df_accepted_display['Profile URL'] = df_accepted_display['Profile URL'].apply(make_clickable_link)
    df_accepted_display['Posts URL'] = df_accepted_display['Posts URL'].apply(make_clickable_link)

    # Display data with clickable links
    st.write(df_accepted_display.to_html(escape=False), unsafe_allow_html=True)

if __name__ == '__main__':
    main()

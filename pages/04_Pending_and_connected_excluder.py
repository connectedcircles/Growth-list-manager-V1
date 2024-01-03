import streamlit as st
import pandas as pd
from google.oauth2 import service_account
import pygsheets
import pyodbc
import base64
import json




##### LOCAL AUTHENTICATION ####################################################

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


#######################################################################



# Define a function to get the connections of all clients from the SQL database of connections
def get_all_connections():
    conn = pyodbc.connect(conn_str)
    query = "SELECT * FROM ProfilesX"
    df = pd.read_sql(query, conn)
    conn.close()
    return df

# Define a function to get the profiles that were invited by CC for all clients from the google sheet 
def get_invited_profiles():
    gc = pygsheets.authorize(custom_credentials=creds)
    spreadsheet = gc.open_by_url("https://docs.google.com/spreadsheets/d/1QWhVtOPoOoYVdxoUtM5RKAhwJKVW-6-q6T5ACZJVkdU/edit#gid=1820302186")
    worksheet = spreadsheet.worksheet_by_title("Invited")
    records = worksheet.get_all_records()
    df = pd.DataFrame(records)
    return df








def app():
    
    # Set title and subtitle
    st.title("Connection and Pending Invite Filter For Growth Lists")
    st.subheader("Property of Connected Circles")
    
    # Apply the functions to get the connected and invited profiles
    df_connections = get_all_connections()
    df_invited = get_invited_profiles()
    
    # Select client from unique values in df_invited
    client_name = st.selectbox('Select Client', df_connections['Client'].unique())

    # File uploader
    uploaded_file = st.file_uploader("Choose a CSV file to filter", type="csv")

    if uploaded_file is not None:
        growth_list = pd.read_csv(uploaded_file)

        # filter the Connection and Invited dataframes to only those relating to the client
        df_connections_client_specific = df_connections[df_connections['Client'] == client_name]
        df_invited_client_specific = df_invited[df_invited['Client Name'] == client_name]
        
        ##### Filtering growth list

        # Copy the growth list
        growth_list_filtered = growth_list.copy()

        ### Filtering out already invited profiles
        invited_names = df_invited_client_specific['Full name'].tolist()
        growth_list_filtered = growth_list_filtered[~growth_list_filtered['Full name'].isin(invited_names)]



        ### Filtering out existing connections
        connection_names = df_connections_client_specific['Name'].tolist()
        growth_list_filtered = growth_list_filtered[~growth_list_filtered['Full name'].isin(connection_names)]
        
        

        # Download link for filtered data
        csv_filtered = growth_list_filtered.to_csv(index=False)
        b64_filtered = base64.b64encode(csv_filtered.encode('utf-8')).decode()
        href_filtered = f'<a href="data:file/csv;base64,{b64_filtered}" download="filtered_data.csv">Download Filtered CSV File</a>'
        

        # Download link for filtered data URLs only, no header
        url_col = growth_list_filtered["Profile url"].dropna().astype(str)
        csv_url = url_col.to_csv(index=False, header=False)
        b64_url = base64.b64encode(csv_url.encode('utf-8')).decode()
        href_url = f'<a href="data:file/csv;base64,{b64_url}" download="profile_urls.csv">Download Profile URLs CSV File</a>'


##### DISPLAY OF RESULTS #####
        
        ### Display Metrics (list lengths and overlaps)
        st.write(f"Rows in Connections DataFrame: {len(df_connections_client_specific)}")
        st.write(f"Rows in Invited DataFrame: {len(df_invited_client_specific)}")
        # Count how many names in the growth list are in the invited names list
        overlap_count_invited = growth_list[growth_list['Full name'].isin(invited_names)].shape[0]
        st.write(f"Overlapping pending invites: {overlap_count_invited}")
        # Count how many names in the growth list are in the connections names list
        overlap_count_connections = growth_list[growth_list['Full name'].isin(connection_names)].shape[0]
        st.write(f"Overlapping connections: {overlap_count_connections}")
        st.write(f"Rows in filtered growth list: {len(growth_list_filtered)}")


            
        # Display the link to download the filtered data, whole and as URLs only
        st.markdown(href_url, unsafe_allow_html=True)
        st.markdown(href_filtered, unsafe_allow_html=True)


if __name__ == "__main__":
    app()
    
    

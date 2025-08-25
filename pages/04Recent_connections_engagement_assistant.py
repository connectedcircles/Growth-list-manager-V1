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
             are sorted from most recent to least recent. MAINTENANCE: In case of "pyodbc.ProgrammingError:" contact Data Team. 
             Data Team: Manage App (lower right hand corner of the app) -> Copy the IP adress -> add firewall rule in Azure Portal.
             https://portal.azure.com/#@connectedcircles.net/resource/subscriptions/61171ae4-c392-4dca-9ad4-880921a42770/resourceGroups/circulus-api/providers/Microsoft.Sql/servers/circulus-data/networking""")

    # Obtain data
    df_connections = get_all_connections()
    df_invited = get_invited_profiles()
    
    # Debug info 1: Initial data loading
    print(f"DEBUG 1: Total invited profiles: {len(df_invited)}")
    print(f"DEBUG 1: Total connections: {len(df_connections)}")
    st.sidebar.write(f"DEBUG 1: Total invited profiles: {len(df_invited)}")
    st.sidebar.write(f"DEBUG 1: Total connections: {len(df_connections)}")

    # Debug info 2: Sample data structure
    if len(df_invited) > 0:
        print("DEBUG 2: First row of invited profiles:")
        print(df_invited.iloc[0])
    
    if len(df_connections) > 0:
        print("DEBUG 2: First row of connections:")
        print(df_connections.iloc[0])
    
    # Column names in invited profiles
    print("DEBUG 2: Columns in invited profiles:", df_invited.columns.tolist())
    # Column names in connections
    print("DEBUG 2: Columns in connections:", df_connections.columns.tolist())

    df_invited.rename(columns={'Full name': 'Name'}, inplace=True)
    df_invited['Posts_URL'] = df_invited['Profile URL'] + '/recent-activity/all/'
    df_invited['Client Name'] = df_invited[' ']

    # Add after setting Client Name to check values
    print("Sample Client Names from the first column:")
    print(df_invited[' '].head(5).tolist())  # Show first 5 values
    print("Sample Client Names after setting:")
    print(df_invited['Client Name'].head(5).tolist())  # Should match the above
    
    # Get unique clients for the dropdown menu
    unique_clients = df_connections['Client'].unique()
    print(f"DEBUG 3: Unique clients: {unique_clients}")
    st.sidebar.write(f"DEBUG 3: Number of unique clients: {len(unique_clients)}")
    
    # Dropdown menu for Client
    Client_Name = st.selectbox("Select Client", unique_clients)
    print(f"DEBUG 4: Selected client: {Client_Name}")
    st.sidebar.write(f"DEBUG 4: Selected client: {Client_Name}")

    # Debug info: Check if any invited profiles match the selected client
    client_matches = df_invited[df_invited['Client Name'] == Client_Name]
    print(f"DEBUG 5: Invited profiles matching client {Client_Name}: {len(client_matches)}")
    st.sidebar.write(f"DEBUG 5: Invited profiles matching client {Client_Name}: {len(client_matches)}")

    # Dropdown menu for Category with "All Categories" at the top
    try:
        if 'Client Name' in df_invited.columns:
            unique_categories = ["All Categories"] + list(df_invited[df_invited['Client Name'] == Client_Name]['Category'].unique())
            print(f"DEBUG 6: Found {len(unique_categories)} categories for {Client_Name}: {unique_categories}")
            st.sidebar.write(f"DEBUG 6: Found {len(unique_categories)} categories for {Client_Name}")
        else:
            print("DEBUG 6: Client Name column is missing in the data source.")
            st.sidebar.write("DEBUG 6: Client Name column is missing in the data source.")
            unique_categories = ["All Categories"]  # Provide a default value
    except Exception as e:
        print(f"DEBUG 6: Error occurred: {str(e)}")
        st.sidebar.write(f"DEBUG 6: Error occurred: {str(e)}")
        unique_categories = ["All Categories"]  # Fallback in case of any error

    selected_categories = st.multiselect("Select Category", unique_categories, default=["All Categories"])
    print(f"DEBUG 7: Selected categories: {selected_categories}")
    st.sidebar.write(f"DEBUG 7: Selected categories: {selected_categories}")

    df_invited_client_specific = df_invited[df_invited['Client Name'] == Client_Name]
    df_connections_client_specific = df_connections[df_connections['Client'] == Client_Name]
    
    # Debug info: Check filtered dataframes
    print(f"DEBUG 8: Invited profiles for client {Client_Name}: {len(df_invited_client_specific)}")
    print(f"DEBUG 8: Connections for client {Client_Name}: {len(df_connections_client_specific)}")
    st.sidebar.write(f"DEBUG 8: Invited profiles for client {Client_Name}: {len(df_invited_client_specific)}")
    st.sidebar.write(f"DEBUG 8: Connections for client {Client_Name}: {len(df_connections_client_specific)}")
    
    # Show sample of connection names to check for matches
    if len(df_connections_client_specific) > 0:
        conn_names = df_connections_client_specific['Name'].tolist()
        print(f"DEBUG 9: Some connection names: {conn_names[:5]}")
        st.sidebar.write(f"DEBUG 9: First few connection names: {', '.join(conn_names[:5] if len(conn_names) >= 5 else conn_names)}")
    
    if len(df_invited_client_specific) > 0:
        invited_names = df_invited_client_specific['Name'].tolist()
        print(f"DEBUG 9: Some invited names: {invited_names[:5]}")
        st.sidebar.write(f"DEBUG 9: First few invited names: {', '.join(invited_names[:5] if len(invited_names) >= 5 else invited_names)}")
        
        # Check for common names (potential matches)
        if len(df_connections_client_specific) > 0:
            conn_names_set = set(df_connections_client_specific['Name'])
            invited_names_set = set(df_invited_client_specific['Name'])
            common_names = invited_names_set.intersection(conn_names_set)
            print(f"DEBUG 10: Common names (potential matches): {common_names}")
            st.sidebar.write(f"DEBUG 10: Number of common names (potential matches): {len(common_names)}")
            if len(common_names) > 0:
                st.sidebar.write(f"Some common names: {', '.join(list(common_names)[:5] if len(common_names) >= 5 else list(common_names))}")

    df_accepted = pd.merge(df_invited_client_specific, df_connections_client_specific[['Name', 'ProfileDate']], on='Name', how='inner')
    print(f"DEBUG 11: Matched records after merge: {len(df_accepted)}")
    st.sidebar.write(f"DEBUG 11: Matched records after merge: {len(df_accepted)}")
    
    if len(df_accepted) > 0:
        df_accepted_display = df_accepted[["Name", "Title", "Organization 1", "Profile URL", "Posts_URL", "Followers", "Category", "Date collected", "ProfileDate"]]
        df_accepted_display.rename(columns={"Organization 1": "Organization", 'Posts_URL': 'Posts URL', "Date collected": 'Invited on', 'ProfileDate': 'Connected on (approximate)'}, inplace=True)
        
        # If "All Categories" is not the only category selected, filter by selected categories
        if "All Categories" not in selected_categories or len(selected_categories) > 1:
            before_filter = len(df_accepted_display)
            df_accepted_display = df_accepted_display[df_accepted_display['Category'].isin(selected_categories)]
            after_filter = len(df_accepted_display)
            print(f"DEBUG 12: Records before category filtering: {before_filter}, after: {after_filter}")
            st.sidebar.write(f"DEBUG 12: Records before category filtering: {before_filter}, after: {after_filter}")
        
        # Option to display as dataframe using a toggle
        display_as_dataframe = st.checkbox("Display as dataframe", value=False)
        
        # Sort the dataframe
        df_accepted_display = df_accepted_display.sort_values(by='Connected on (approximate)', ascending=False)
        
        print(f"DEBUG 13: Final dataframe size: {len(df_accepted_display)}")
        st.sidebar.write(f"DEBUG 13: Final dataframe size: {len(df_accepted_display)}")
        
        if len(df_accepted_display) > 0:
            print("DEBUG 14: First row of final data:")
            print(df_accepted_display.iloc[0])
        
        if display_as_dataframe:
            # Display as raw dataframe
            st.dataframe(df_accepted_display)
        else:
            # Convert URLs to clickable icons
            df_accepted_display['Profile URL'] = df_accepted_display['Profile URL'].apply(make_clickable_link)
            df_accepted_display['Posts URL'] = df_accepted_display['Posts URL'].apply(make_clickable_link)
            
            # Display data with clickable links without the index
            st.write(df_accepted_display.to_html(index=False, escape=False), unsafe_allow_html=True)
    else:
        st.warning("No matching records found between invited profiles and connections for the selected client.")
        print("DEBUG 11: No matching records found in merge.")

    # Provide debug expander with more details
    with st.sidebar.expander("Raw Data Sample"):
        st.write("Sample of invited data:")
        if len(df_invited) > 0:
            st.dataframe(df_invited.head(3))
        st.write("Sample of connections data:")
        if len(df_connections) > 0:
            st.dataframe(df_connections.head(3))

if __name__ == '__main__':
    main()
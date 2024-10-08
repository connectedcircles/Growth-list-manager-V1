import streamlit as st
import pandas as pd
from google.oauth2 import service_account
import pygsheets
import pyodbc
import json


##### CLOUD AUTHENTICATION ####################################################
# Authenticate Google Sheets API
raw_creds = st.secrets["raw_creds"]
json_creds = json.loads(raw_creds)

creds = service_account.Credentials.from_service_account_info(
    json_creds,
    scopes=['https://www.googleapis.com/auth/spreadsheets',
            'https://www.googleapis.com/auth/drive']
)

conn_str = st.secrets["conn_str"] 
###############################################################################

def get_all_connections():
    conn = pyodbc.connect(conn_str)
    query = "SELECT * FROM ProfilesX"
    df = pd.read_sql(query, conn)
    conn.close()
    return df

def get_engagers_group():
    gc = pygsheets.authorize(custom_credentials=creds)
    spreadsheet = gc.open_by_url("https://docs.google.com/spreadsheets/d/19cgiKVQM1ShW9R8JzdWuPVAcXqbPnDbavyeLQyixQxo/edit#gid=0")
    worksheet = spreadsheet.worksheet_by_title("Engagers")
    records = worksheet.get_all_records()
    df = pd.DataFrame(records)
    return df

def make_clickable_link(val):
    """Return a clickable URL with the text 'URL'"""
    return f'<a target="_blank" href="{val}">URL</a>'

def display_group(client_name):
    st.subheader("Select a Group")
    
    # Retrieve data from Google Sheet
    try:
        df = get_engagers_group()
    except Exception as e:
        st.error(f"An error occurred while reading the Google Sheet: {e}")
        return

    if 'Category' in df.columns:
        unique_categories = df[df["Client"] == client_name]['Category'].unique()
        category = st.selectbox('Select a Category', unique_categories)
        
        # Filter the DataFrame based on the selected category
        filtered_df = df[(df['Category'] == category) & (df['Client'] == client_name)]
        
        # Option to display as dataframe using a toggle
        display_as_dataframe = st.checkbox("Display as dataframe", value=False)
        
        if display_as_dataframe:
            # Display as raw dataframe
            st.dataframe(filtered_df)
        else:
            # Convert URLs to clickable icons
            filtered_df['ProfilePermaLink'] = filtered_df['ProfilePermaLink'].apply(make_clickable_link)
            filtered_df['Posts_URL'] = filtered_df['Posts_URL'].apply(make_clickable_link)
    
            # Display data with clickable links without the index
            st.text(f"Selected Engagers Group: {category}")
            st.write(filtered_df[["Name", "ProfilePermaLink", "Posts_URL", "Organization", "Title", "Location", "Followers"]].to_html(index=False, escape=False), unsafe_allow_html=True)
    else:
        st.error('No "Category" column found in the Google Sheet. Please ensure the sheet has a "Category" column.')

def save_to_google_sheet(sheet_name, filtered_connections, creds, sheet_url):
    try:
        # Authorize with pygsheets using the credentials
        gc = pygsheets.authorize(custom_credentials=creds)

        # Open the Google Sheet by URL
        spreadsheet = gc.open_by_url(sheet_url)

        try:
            # Check if the specified sheet already exists
            worksheet = spreadsheet.worksheet_by_title(sheet_name)

            # Get existing records and convert to DataFrame
            existing_data = pd.DataFrame(worksheet.get_all_records())

            # Combine the new data with the existing data
            combined_data = pd.concat([filtered_connections, existing_data], ignore_index=True)
            
            # Clear the existing worksheet to prepare for new data
            worksheet.clear()
        except pygsheets.WorksheetNotFound:
            # If the sheet doesn't exist, create a new one and start with the new data
            worksheet = spreadsheet.add_worksheet(title=sheet_name, rows=1000, cols=50)
            combined_data = filtered_connections

        # Set the combined data to the worksheet
        worksheet.set_dataframe(combined_data, (1, 1))  # (1, 1) means starting from the first cell

        # Success message after saving
        st.success("Data saved successfully to Google Sheet!")

    except Exception as e:
        st.error(f"Error saving data to Google Sheet: {e}")

def main():
    # Set the title and description of the Streamlit app
    st.title("Create and Monitor Activity of Specific Groups")
    st.write("""Engage with selected groups from all connections by clicking the Posts' URL. You can create a new group by choosing a client, naming a group, and selecting names from the client network.
You can edit exisiting list here: https://docs.google.com/spreadsheets/d/19cgiKVQM1ShW9R8JzdWuPVAcXqbPnDbavyeLQyixQxo/edit?gid=0#gid=0 """)
    
    # Obtain data for connections
    df_connections = get_all_connections()

    # Extract unique clients for the dropdown menu
    unique_clients = df_connections['Client'].unique()

    # Create a dropdown menu to select a client
    client_name = st.selectbox("Select Client", unique_clients)

    # Section for creating a group
    st.subheader("Create a Group")
    st.write("Search and select people from the list")

    # Retrieve all connections for the selected client
    connections = df_connections[df_connections["Client"] == client_name]

    # Get a list of names for the selected client to use in multiselect
    client_connections_names = connections["Name"].tolist()

    # Input for naming the group
    group_name = st.text_input("Name the Group")

    # Multiselect widget to select specific names for the group
    engagers_list = st.multiselect("Select Names", client_connections_names)

    # Filter connections based on the selected client and names
    filtered_connections = connections[connections['Name'].isin(engagers_list)]

    # Add new columns to the filtered DataFrame
    filtered_connections["Category"] = group_name
    filtered_connections['Posts_URL'] = filtered_connections['ProfilePermaLink'] + '/recent-activity/all/'

    # Apply the `make_clickable_link` function to create a new 'Feed' column for clickable URLs
    filtered_connections["Feed"] = filtered_connections["ProfilePermaLink"].apply(make_clickable_link)

    # Reorganize the columns to a desired order
    filtered_connections = filtered_connections[[
        "Client", "Name", "ProfilePermaLink", "Posts_URL", "Organization", 
        "Title", "Location", "Followers", "Category"
    ]]

    # Display the filtered DataFrame in a table format
    st.table(filtered_connections)

    # Define the Google Sheet URL and credentials
    sheet_url = 'https://docs.google.com/spreadsheets/d/19cgiKVQM1ShW9R8JzdWuPVAcXqbPnDbavyeLQyixQxo/edit#gid=0'

    # Add a button to save the DataFrame to the Google Sheet
    if st.button("Save to Google Sheet"):
        save_to_google_sheet(sheet_name='Engagers',
                             filtered_connections=filtered_connections,
                             creds=creds,
                             sheet_url=sheet_url)
        
    display_group(client_name)

if __name__ == '__main__':
    main()

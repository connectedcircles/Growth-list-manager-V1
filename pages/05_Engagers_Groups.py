import streamlit as st
import pandas as pd
from google.oauth2 import service_account
import pygsheets
import pyodbc
import json
from openpyxl import load_workbook


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
file_path = 'Engagers_groups.xlsx'


def get_all_connections():
    conn = pyodbc.connect(conn_str)
    query = "SELECT * FROM ProfilesX"
    df = pd.read_sql(query, conn)
    conn.close()
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


def display_group(file_path):
    st.subheader("Select a Group")
    
    # Read Excel file directly from the specified path
    try:
        df = pd.read_excel(file_path)
    except FileNotFoundError:
        st.error("The specified file was not found in the provided path.")
        return
    except Exception as e:
        st.error(f"An error occurred while reading the file: {e}")
        return

    if 'Category' in df.columns:
        unique_categories = df['Category'].unique()
        category = st.selectbox('Select a Category', unique_categories)
        
        # Filter the DataFrame based on the selected category
        filtered_df = df[df['Category'] == category]
        # Option to display as dataframe using a toggle
        display_as_dataframe = st.checkbox("Display as dataframe", value=False)
        
        # Display the filtered DataFrame
        #st.write("Displaying rows with selected category:")
        
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
    
            #st.dataframe(filtered_df)
    else:
        st.error('No "Category" column found in the Excel file. Please ensure the file has a "Category" column.')
        


def save_to_excel(file_path, sheet_name, filtered_connections):
    try:
        # Load the existing workbook to check for the sheet
        workbook = load_workbook(file_path)

        # Check if the specified sheet already exists
        if sheet_name in workbook.sheetnames:
            # Read the existing sheet into a DataFrame, skipping the headers (to preserve them)
            existing_df = pd.read_excel(file_path, sheet_name=sheet_name, header=0)
            
            # Append new data on top by combining filtered_connections above existing data
            combined_df = pd.concat([filtered_connections, existing_df], ignore_index=True)
        else:
            # If the sheet doesn't exist, start with the new data as the combined DataFrame
            combined_df = filtered_connections

        # Write the combined DataFrame back to the Excel file, preserving the original headers
        with pd.ExcelWriter(file_path, engine='openpyxl', mode='a', if_sheet_exists='replace') as writer:
            # Set `startrow=1` to write data below the existing header row
            combined_df.to_excel(writer, sheet_name=sheet_name, index=False, startrow=0)

        # Success message after saving
        st.success("Data saved successfully to Excel file!")

    except Exception as e:
        # Display an error message if something goes wrong
        st.error(f"Error saving data to Excel: {e}")


def main():
    #df = get_invited_profiles()
    #st.table(df)
    # Set the title and description of the Streamlit app
    st.title("Create and Monitor Activity of Specific Groups")
    st.write("""Engage with selected groups from all connections by clicking the Posts' URL. You can create a new group by choosing a client, naming a group and selecting names from the client network. 
             If you want to manually update the Excel file with groups (remove/add new names from existing groups), you can click on this link:
                https://docs.google.com/spreadsheets/d/19cgiKVQM1ShW9R8JzdWuPVAcXqbPnDbavyeLQyixQxo/edit?gid=0#gid=0 """)

    # Obtain data for connections
    df_connections = get_all_connections()

    # Extract unique clients for the dropdown menu
    unique_clients = df_connections['Client'].unique()

    # Create a dropdown menu to select a client
    Client_Name = st.selectbox("Select Client", unique_clients)

    # Section for creating a group
    st.subheader("Create a Group")
    st.write("Search and select people from the list")

    # Retrieve all connections for the selected client
    connections = df_connections[df_connections["Client"] == Client_Name]

    # Get a list of names for the selected client to use in multiselect
    client_connections_names = connections["Name"].tolist()

    # Input for naming the group
    group_name = st.text_input("Name the Group")

    # Multiselect widget to select specific names for the group
    engagers_list = st.multiselect("Select Names", client_connections_names)

    # Display selected names and group name
    #st.write("Selected Names:", engagers_list)
    #st.write("Group Name:", group_name)

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

    # Define the path to the existing Excel file
    sheet_name = 'Filtered_Connections'

    # Add a button to save the DataFrame to the existing Excel file
    if st.button("Save to Excel"):
        save_to_excel(file_path,sheet_name,filtered_connections)
        
    display_group(file_path)
        

        







if __name__ == '__main__':
    main()

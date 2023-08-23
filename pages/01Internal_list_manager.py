import streamlit as st
import pandas as pd
from google.oauth2 import service_account
from getfilelistpy import getfilelist
import pygsheets
import json

### Google Drive API authentication ########################################################################
# Authenticate Google Drive API
# Authenticate Google Sheets API
json_creds = json.loads(raw_creds)

creds = service_account.Credentials.from_service_account_info(
    json_creds,
    scopes=['https://spreadsheets.google.com/feeds', 'https://www.googleapis.com/auth/drive']
)
#############################################################################################################

##### Define function to retrieve all info about the files in a folder and the folders within it #####
def get_files_in_nested_folders(folder_url):
    resource = {
        "service_account":creds,
        "id": folder_url.split('/')[-1],
        "fields": "files(name,id,webViewLink)",
    }
    res = getfilelist.GetFileList(resource)
    return res
#######################################################################################################

# Streamlit app
def main():
    st.title("Google Drive Files Viewer")
    
    folder_url = 'https://drive.google.com/drive/folders/13pKJYkrbDgEqva5eHJx0Nta66gLZwzz7'  # Enter your default folder URL here
    res = get_files_in_nested_folders(folder_url)

    # Retrieving relevant info from the res (results) object #############################################
    # create an intermediate object to store the records
    file_records = []

    # retrieve each file's name, link, id and the last foldertree (id of the folder that it is in)
    for file_list_item in res['fileList']:
        file_data = file_list_item.get('files', [])
        folder_tree = file_list_item.get('folderTree', [])  # Retrieve the folderTree data

        for file_item in file_data:
            name = file_item.get('name', None)
            id = file_item.get('id', None)
            webViewLink = file_item.get('webViewLink', None)

            # Include folderTree in each item
            file_records.append({
                'name': name,
                'id': id,
                'webViewLink': webViewLink,
                'folderTree': folder_tree  # Add folderTree data to each item
            })

    # Preserve only the second foldertree value (the name of the client folder id)
    for record in file_records:
        folder_tree = record['folderTree']
        if len(folder_tree) > 1:
            record['folderTree'] = folder_tree[1]
        else:
            record['folderTree'] = None

    ### Create a dataframe to store the info about each file
    files = pd.DataFrame(file_records, columns=["name", "id", "webViewLink", "folderTree"])

    ########################################################################################################

    # get the names of folders corresponding to their foldertree codes
    folder_tree_names = pd.DataFrame(res['folderTree'])
    # rename for merging
    folder_tree_names = folder_tree_names.rename(columns={"folders": "folderTree"})

    # merge them to the records
    files = files.merge(folder_tree_names, on='folderTree', how='left')

    files = files.dropna(subset=['names'])

    # Authenticate with Google Sheets API
    gc = pygsheets.authorize(service_file='C:/Users/HP/Downloads/credentials.json')


    # Calculate lengths and add the "length" column
    lengths = []
    for idx, row in files.iterrows():
        sheet_id = row['webViewLink'].split('/')[-2]
        sheet = gc.open_by_key(sheet_id)
        worksheet = sheet[0]
        column_values = worksheet.get_col(1)
        non_empty_count = sum(1 for value in column_values if value)
        lengths.append(non_empty_count)
    files['length'] = lengths

    # Display files grouped by names with hyperlinks and length
    grouped = files.groupby('names')
    for name, group in grouped:
        st.subheader(name)
        for idx, row in group.iterrows():
            st.markdown(f"**[{row['name']}]({row['webViewLink']})** - Length: {row['length']}")

if __name__ == "__main__":
    main()

import streamlit as st
import pandas as pd
from google.oauth2 import service_account
from getfilelistpy import getfilelist
import pygsheets
import json
import numpy as np

### Google Drive API authentication ########################################################################
# Authenticate Google Drive API
# Authenticate Google Sheets API
raw_creds = st.secrets["raw_creds"]
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
    st.title("Growth List Manager - Internal")
    st.write("""This app allows you to view growth lists and filter them based on approval status. Please follow the correct procedure when 
    creating growth lists - 1.Use the correct template. 2. Indicate which names have been invited alreay using the "Sent" column in the template. 3.
    Store the folder in the appropriate folder in the "Growth list manager" drive. 3. Use the prefix "Approved" and "Done" in the filename to indicate 
    the approval/competion status.""")
    

    
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
        if len(folder_tree) > 0:
            record['folderTree'] = folder_tree[-1]
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

    # drop files wich are not nested in a folder with the name of a client
    files = files.dropna(subset = ['names'])
    
    # detect which files are DONE or declined and remove them
    files['done_or_declined'] = files['name'].apply(lambda x: 'yes' if 'done' in x.lower() or 'declined' in x.lower() else 'no')
    
    files = files.drop(files[files['done_or_declined'] == "yes"].index)

    files = files.merge(folder_tree_names['names'], on='names', how='right')

### Count the number of rows in the sheets #############################################################

    # Authenticate with Google Sheets API
    gc = pygsheets.authorize(custom_credentials=creds)


    total_lengths = []
    depleted_lengths = []
    
    for url in files['webViewLink']:
        # Check if the 'url' is not NaN
        if pd.notna(url):
            try:
                # Print the URL for debugging
                print(f"Processing URL: {url}")
                
                # Extract the Google Sheets ID from the URL
                sheet_id = url.split('/')[-2]
                
                # Print the extracted Sheet ID for debugging
                print(f"Extracted Sheet ID: {sheet_id}")
    
                # Open the Google Sheet using its ID
                sheet = gc.open_by_key(sheet_id)
    
                # Select the first sheet
                worksheet = sheet[0]
    
                # Get all values in the sheet
                all_values = worksheet.get_all_values()
    
                # Find the header row
                header_row = all_values[0]
    
                # Find the index of the "Sent" column
                if "Sent" not in header_row:
                    raise ValueError("The 'Sent' column is missing!")
                
                sent_column_index = header_row.index("Sent")
    
                # Count non-empty cells in the first column
                total_count = sum(1 for row in all_values if row[0])
    
                # Count rows where the "Sent" column has the value "Depleted"
                depleted_count = sum(1 for row in all_values if sent_column_index is not None and row[sent_column_index] == "Depleted")
    
                total_lengths.append(total_count)
                depleted_lengths.append(depleted_count)
                
            except Exception as e:
                print(f"Failed processing {url} due to: {e}")
                # Append 0 for this URL since it failed
                total_lengths.append(0)
                depleted_lengths.append(0)
    
        else:
            # Handle NaN case here
            total_lengths.append(0)
            depleted_lengths.append(0)
            
### Now we make operations on the dataframe
# Add the lengths and depleted lengths column in the original DataFrame
    files['length'] = total_lengths
    files['depleted'] = depleted_lengths
    # calculate the number of available rows
    files['available'] = files['length'] - files['depleted']
    # label growth lists based on whether they include the strings approved or done
    files['approved'] = files['name'].apply(lambda x: 
                                            'yes' if 'approved' in str(x).lower() 
                                            else ('no' if isinstance(x, str) 
                                                  else np.nan))


    # Display files grouped by names with hyperlinks and length
    grouped = files.groupby('names')

    for name, group in grouped:
        st.subheader(name)
        for idx, row in group.iterrows():
            st.markdown(f"**[{row['name']}]({row['webViewLink']})** - Length: {row['length']} - Available: {row['available']}")


if __name__ == "__main__":
    main()

import streamlit as st
import gspread
import pandas as pd
from google.oauth2 import service_account
from getfilelistpy import getfilelist
import json

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

# Authorize Google Sheets API
client = gspread.authorize(creds)

# Load the table of client login credentials
sheet = client.open('Growth list manager login credentials').sheet1

# Define a function to load the client credentials and URLs of the folder with their lists
def login(name, password):
    data = sheet.get_all_records()
    for row in data:
        if row['Name'] == name and row['Password'] == password:
            return row['Folder_URL']
    return None

# Define a function to get files in a folder using getfilelist
def get_files_in_folder(folder_url):
    resource = {
        "service_account": creds,
        "id": folder_url.split('/')[-1],
        "fields": "files(name,id,webViewLink)",
    }
    res = getfilelist.GetFileList(resource)
    files = pd.DataFrame(res['fileList'][0]['files'], columns=["name", "id", "webViewLink"])
    return files

# Define the app
def main():
    st.title('Login')
    name = st.text_input('Name')
    password = st.text_input('Password', type='password')
    if st.button('Login'):
        folder_url = login(name, password)
        if folder_url:
            st.success('Login Successful!')
            # Display clickable URLs to files in the folder
            files = get_files_in_folder(folder_url)
            if not files.empty:
                st.markdown("### Available lists:")
                for _, file in files.iterrows():
                    st.markdown(f"[{file['name']}]({file['webViewLink']})")
            else:
                st.markdown("No files found in the folder.")
        else:
            st.error('Invalid credentials')

# Run the app
if __name__ == '__main__':
    main()

### Import libraries
import streamlit as st
import gspread
from google.oauth2 import service_account
import json
import os


### Parse credentials stored in Streamlit Share secret
# Load JSON credentials as a dictionary
credentials_dict = json.loads(os.getenv('google_credentials'))

# Create ServiceAccountCredentials object
creds = ServiceAccountCredentials.from_json_keyfile_dict(credentials_dict)

# Authenticate
client = gspread.authorize(creds)


### Load the table of client login credentials
sheet = client.open('Growth list manager login credentials').sheet1




### Create a function to load the client credentials and URLs of the folder with their lists
def login(name, password):
    data = sheet.get_all_records()
    for row in data:
        if row['Name'] == name and row['Password'] == password:
            return row['folder URL']
    return None


### Define the app
def main():
    st.title('Login')
    name = st.text_input('Name')
    password = st.text_input('Password', type='password')
    if st.button('Login'):
        folder_url = login(name, password)
        if folder_url:
            st.success('Login Successful!')
            # Display clickable URLs to files in the folder
            # You can use the Google Drive API or any other method to retrieve the files.
            # Display them using Streamlit components like st.markdown or st.write.
        else:
            st.error('Invalid credentials')


### Run the app
if __name__ == '__main__':
    main()





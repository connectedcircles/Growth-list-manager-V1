import pandas as pd
import streamlit as st
import base64
import datetime
from google.oauth2 import service_account
import pygsheets
import json



### Google Drive API authentication (Streamlit share version) ###############################################
# Authenticate Google Drive API
# Authenticate Google Sheets API
raw_creds = st.secrets["raw_creds"]
json_creds = json.loads(raw_creds)

creds = service_account.Credentials.from_service_account_info(
    json_creds,
    scopes=['https://spreadsheets.google.com/feeds', 'https://www.googleapis.com/auth/drive']
)
############################################################################################################

#### Google Drive API authentication (Offline, local version)#################################################
## Authenticate Google Drive API
## Authenticate Google Sheets API
#creds = service_account.Credentials.from_service_account_file(
#    'C:/Users/HP/Downloads/credentials.json',
#    scopes=['https://spreadsheets.google.com/feeds', 'https://www.googleapis.com/auth/drive']
#)
#############################################################################################################


#use it to authorize pygsheets
gc = pygsheets.authorize(custom_credentials=creds)

# Define function to append data to Google Sheet
def append_to_sheet(df):
    try:
        # Open the Google Sheet by title
        spreadsheet = gc.open_by_key('1UsI_uXcDeVQ61saUwok9wBygLbaEdR15zMCu52D5WU8')
        
        # Select the worksheet by title
        worksheet = spreadsheet.sheet1
        
        # Calculate the starting row for appending data
        start_row = len(worksheet.get_all_values()) + 1
        
        # Append the data to the worksheet, starting from the next empty row
        worksheet.append_table(values=df.values.tolist(), start=f'A{start_row}', end=None, dimension='ROWS', overwrite=False)
        
        st.success("Data appended successfully!")
    except Exception as e:
        st.error(f"An error occurred: {str(e)}")

def app():
    # Set title and subtitle, additional text
    st.title("Growth Invite Logger V1")
    st.subheader("Property of Connected Circles")
    st.write("""Log invites with this app. Please mind your spelling.""")
    
    # Set client name, invite date and category
    ClientName = st.text_input("Enter client name")
    DateInvited = st.date_input("Select a date", datetime.date.today())
    Category = st.text_input("Enter category")
    
    # Convert date to string format
    DateInvited_str = DateInvited.strftime('%Y-%m-%d')

    # File uploader
    uploaded_file = st.file_uploader("Choose a CSV file to upload", type="csv")
    
    # Process data
    if uploaded_file is not None:
        df = pd.read_csv(uploaded_file)
    
        # Create a column for the name of the client
        df.insert(0, "Client Name", ClientName)
        # Rewrite the date and category columns
        df["Date collected"] = DateInvited_str
        df["Category"] = Category

        # Replace missing values with "NA"
        df.fillna("NA", inplace=True)

        # DISPLAY OF RESULTS
        
        # Display both filtered and unfiltered data in two windows with links to download each below
        st.write(df)

        # Button to append data to Google Sheet
        if st.button("Append data to Google Sheet"):
            append_to_sheet(df.dropna(how="all", axis=1))

if __name__ == "__main__":
    app()

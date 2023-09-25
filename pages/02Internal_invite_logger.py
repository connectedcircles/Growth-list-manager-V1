import pandas as pd
import streamlit as st
import base64
import datetime
from google.oauth2 import service_account
import pygsheets
import json
from slack_sdk import WebClient

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

### Google Drive API authentication (Offline, local version) #################################################
# Authenticate Google Drive API
# Authenticate Google Sheets API
#creds = service_account.Credentials.from_service_account_file(
#    'C:/Users/HP/Downloads/credentials.json',
#    scopes=['https://spreadsheets.google.com/feeds', 'https://www.googleapis.com/auth/drive']
#)
############################################################################################################



### Slack authorization (Offline, local version) ####################################################################

############################################################################################

### Slack authorization (Streamlit share version) ####################################################################
# set Slack access token
slack_token = st.secrets["slack_token"]
# set slack channel
target_channel_id = st.secrets["target_channel_id"]
############################################################################################



# Initialize the Slack WebClient
slack_client = WebClient(token=slack_token)

# Use Google credentials to authorize pygsheets
gc = pygsheets.authorize(custom_credentials=creds)



# Define function to append data to Google Sheet and send a Slack message
def append_to_sheet(df, ClientName, Category, DateInvited_str, growth_list_url):
    try:
        # Open the Google Sheet by title
        spreadsheet = gc.open_by_key('1QWhVtOPoOoYVdxoUtM5RKAhwJKVW-6-q6T5ACZJVkdU')
        
        # Select the worksheet by title
        worksheet = spreadsheet.sheet1
        
        # Calculate the starting row for appending data
        start_row = sum(1 for row in worksheet.get_all_values() if row[0]) + 1
        
        # Append the data to the worksheet, starting from the next empty row
        worksheet.append_table(values=df.values.tolist(), start=f'A{start_row}', end=None, dimension='ROWS', overwrite=False)
        
        st.success("Data appended successfully!")

        # Send the message to Slack
        send_slack_message(message)

    except Exception as e:
        st.error(f"An error occurred: {str(e)}")



def send_slack_message(message):
    try:
        # Send the message to Slack
        response = slack_client.chat_postMessage(
            channel= target_channel_id,
            text=message
        )

        if response["ok"]:
            st.success("Slack message sent successfully!")
        else:
            st.error(f"Failed to send Slack message. Error: {response['error']}")
    except Exception as e:
        st.error(f"An error occurred while sending the Slack message: {str(e)}")




# Streamlit app function
def app():
    # Set title and subtitle, additional text
    st.title("Growth Invite Logger V1")
    st.subheader("Property of Connected Circles")
    st.write("""Log invites with this app. Please mind your spelling. Data location: https://docs.google.com/spreadsheets/d/1QWhVtOPoOoYVdxoUtM5RKAhwJKVW-6-q6T5ACZJVkdU/edit#gid=1820302186. For emergency use, fill manually.""")
    
    # Set client name, invite date, category, and growth list URL
    ClientName = st.text_input("Enter client name")
    DateInvited = st.date_input("Select a date", datetime.date.today())
    Category = st.text_input("Enter category")
    growth_list_url = st.text_input("Growth list URL")  # Added input for growth list URL
    
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

        # Display both filtered and unfiltered data in two windows with links to download each below
        st.write(df)

        # Button to append data to Google Sheet and send Slack message
        if st.button("Append data to Google Sheet and Send Slack Message"):
            appended = append_to_sheet(df.dropna(how="all", axis=1), ClientName, Category, DateInvited_str, growth_list_url)
            message = f"{ClientName}, {len(df)} profiles, \"{Category}\", {DateInvited_str}, {growth_list_url}"
            send_slack_message(message)



if __name__ == "__main__":
    app()

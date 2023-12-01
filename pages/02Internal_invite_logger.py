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

# Define a function to retrieve the Invited profiles from the Google Sheet
def get_invited_profiles():
    gc = pygsheets.authorize(custom_credentials=creds)
    spreadsheet = gc.open_by_url("https://docs.google.com/spreadsheets/d/1QWhVtOPoOoYVdxoUtM5RKAhwJKVW-6-q6T5ACZJVkdU/edit#gid=1820302186")
    worksheet = spreadsheet.worksheet_by_title("Invited")
    records = worksheet.get_all_records()
    df = pd.DataFrame(records)
    return df


# Streamlit app function
def app():
    st.title("Growth Invite Logger V1")
    st.subheader("Property of Connected Circles")
    st.write("Log invites with this app. Please mind your spelling. Data location: https://docs.google.com/spreadsheets/d/1QWhVtOPoOoYVdxoUtM5RKAhwJKVW-6-q6T5ACZJVkdU/edit#gid=1820302186. For emergency use, fill manually.")

    # Get invited profiles
    invited_profiles = get_invited_profiles()

    # Client name selection with custom option
    client_names = list(invited_profiles['Client Name'].unique())
    client_names.append("Enter Custom Name")  # Add custom option
    selected_client_name = st.selectbox("Select client name", client_names)

    # Allow custom client name input
    if selected_client_name == "Enter Custom Name":
        selected_client_name = st.text_input("Enter Custom Client Name")

    # Filter dataframe based on selected client name
    filtered_df = invited_profiles[invited_profiles['Client Name'] == selected_client_name]

    # Category selection with custom option
    categories = list(filtered_df['Category'].unique())
    categories.append("Enter Custom Category")  # Add custom option
    selected_category = st.selectbox("Select category", categories)

    # Allow custom category input
    if selected_category == "Enter Custom Category":
        selected_category = st.text_input("Enter Custom Category")

    DateInvited = st.date_input("Select a date", datetime.date.today())
    growth_list_url = st.text_input("Growth list URL")

    DateInvited_str = DateInvited.strftime('%Y-%m-%d')

    uploaded_file = st.file_uploader("Choose a CSV file to upload", type="csv")

    if uploaded_file is not None:
        df = pd.read_csv(uploaded_file)
        df.insert(0, "Client Name", selected_client_name)
        df["Date collected"] = DateInvited_str
        df["Category"] = selected_category
        df.fillna("NA", inplace=True)
        st.write(df)

        if st.button("Append data to Google Sheet and Send Slack Message"):
            appended = append_to_sheet(df.dropna(how="all", axis=1), selected_client_name, selected_category, DateInvited_str, growth_list_url)
            message = f"{selected_client_name}, {len(df)} profiles, \"{selected_category}\", {DateInvited_str}, {growth_list_url}"
            send_slack_message(message)

if __name__ == "__main__":
    app()

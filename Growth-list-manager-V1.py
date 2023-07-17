### Import libraries
import streamlit as st
import gspread
from google.oauth2 import service_account
import json


### Parse credentials stored in Streamlit Share secret
# Load JSON credentials as a dictionary
credentials_dict = json.loads(google_credentials)

# Create ServiceAccountCredentials object
creds = ServiceAccountCredentials.from_json_keyfile_dict(credentials_dict)

# Authenticate
client = gspread.authorize(creds)

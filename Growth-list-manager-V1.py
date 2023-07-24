### Import libraries
import streamlit as st
import gspread
from google.oauth2 import service_account
import json
import os


### Parse credentials stored in Streamlit Share secret
# Load JSON credentials from a Streamlit Share secret
google_credentials_text = st.secrets["google_credentials_text"]

# Convert to a dictionary
google_credentials = json.loads(google_credentials_text)





### Define the app
def main():
    st.write(print(google_credentials["private_key"]))



### Run the app
if __name__ == '__main__':
    main()





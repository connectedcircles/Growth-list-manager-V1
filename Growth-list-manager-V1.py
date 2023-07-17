### Import libraries
import streamlit as st
import gspread
from google.oauth2 import service_account
import json
import os


### Parse credentials stored in Streamlit Share secret
# Load JSON credentials from a Streamlit Share secret
google_credentials_text = os.getenv('google_credentials_text')



### Define the app
def main():
    st.title('google_credentials_text')



### Run the app
if __name__ == '__main__':
    main()





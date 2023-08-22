import streamlit as st

def app():
    st.title("Connected Circles Profile Multirole Filter V2")
    st.subheader("Property of Connected Circles")
    st.write("""This app allows you to filter LinkedIn profiles by various categories including seniority, gender or location - filters 
    which are either missing, or inaccurate in SalesNav and cannot be easily filtered in Excel or Sheets. You can download the data 
    either labeled, filtered or filtered profile URLs only, all as a .csv.""")
if __name__ == "__main__":
    app()

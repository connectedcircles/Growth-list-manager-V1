# =============================================================================
# FILE: 03Internal_list_manager_LOCAL_TEST.py
# PURPOSE: List Manager - Google Drive files + Database analytics (Hybrid Version)
# =============================================================================

import streamlit as st
import pandas as pd
from google.oauth2 import service_account
from getfilelistpy import getfilelist
import pygsheets
import json
import numpy as np
import pymssql

### STREAMLIT SECRETS CONFIGURATION ###################################
# This app is configured to use Streamlit secrets.
# For local development, create a .streamlit/secrets.toml file.
# For cloud deployment, add the secrets to your Streamlit Cloud app settings.
import re
import json

try:
    # Database connection
    conn_str = st.secrets["conn_str"]
    server_match = re.search(r'Server=([^;]+)', conn_str)
    database_match = re.search(r'Database=([^;]+)', conn_str)
    uid_match = re.search(r'UID=([^;]+)', conn_str)
    pwd_match = re.search(r'PWD=([^;]+)', conn_str)
    
    server = server_match.group(1) if server_match else None
    database = database_match.group(1) if database_match else None
    username = uid_match.group(1) if uid_match else None
    password = pwd_match.group(1) if pwd_match else None
    
    # Google credentials
    # The value of 'raw_creds' in secrets.toml should be the full JSON content as a multi-line string.
    raw_creds_str = st.secrets["raw_creds"]
    json_creds = json.loads(raw_creds_str)
    
    st.info("🔒 Using Streamlit secrets for configuration.")

    # Validate that all secrets are present
    if not all([server, database, username, password, json_creds]):
        st.error("❌ Missing one or more secrets. Please check your Streamlit secrets configuration.")
        st.stop()

except KeyError as e:
    st.error(f"❌ Missing secret: {e}. Please check your Streamlit secrets configuration.")
    st.stop()

# Setup Google credentials with correct scopes
creds = service_account.Credentials.from_service_account_info(
    json_creds,
    scopes=[
        'https://www.googleapis.com/auth/spreadsheets.readonly',
        'https://www.googleapis.com/auth/drive.readonly',
        'https://spreadsheets.google.com/feeds',
        'https://www.googleapis.com/auth/drive'
    ]
)
################################################################

def get_db_connection():
    """Create database connection using pymssql"""
    try:
        conn = pymssql.connect(
            server=server,
            user=username,
            password=password,
            database=database,
            timeout=30,
            login_timeout=60
        )
        return conn
    except Exception as e:
        raise Exception(f"Database connection failed: {str(e)}")

def get_list_usage_stats():
    """Get growth list usage statistics from database"""
    try:
        conn = get_db_connection()
        query = """
        SELECT 
            ClientName,
            COUNT(*) as TotalInvites,
            COUNT(DISTINCT Category) as Categories,
            MIN(DateCollected) as FirstInvite,
            MAX(DateCollected) as LastInvite
        FROM InvitedProfiles 
        GROUP BY ClientName
        ORDER BY MAX(DateCollected) DESC
        """
        df = pd.read_sql(query, conn)
        conn.close()
        return df
    except Exception as e:
        st.error(f"Error loading database stats: {str(e)}")
        return pd.DataFrame()

def test_connections():
    """Test both database and Google Drive connections"""
    results = {"database": False, "google_drive": False}
    
    # Test database
    try:
        conn = get_db_connection()
        cursor = conn.cursor()
        cursor.execute("SELECT COUNT(*) FROM InvitedProfiles")
        count = cursor.fetchone()[0]
        conn.close()
        st.success(f"✅ Database connected! {count:,} invite records")
        results["database"] = True
    except Exception as e:
        st.error(f"❌ Database connection failed: {str(e)}")
    
    # Test Google Drive
    try:
        folder_url = 'https://drive.google.com/drive/folders/13pKJYkrbDgEqva5eHJx0Nta66gLZwzz7'
        resource = {
            "service_account": creds,
            "id": folder_url.split('/')[-1],
            "fields": "files(name,id)",
        }
        res = getfilelist.GetFileList(resource)
        file_count = sum(len(item.get('files', [])) for item in res['fileList'])
        st.success(f"✅ Google Drive connected! {file_count} files found")
        results["google_drive"] = True
    except Exception as e:
        st.error(f"❌ Google Drive connection failed: {str(e)}")
    
    return results

def get_files_in_nested_folders(folder_url):
    """Get files in Google Drive folders - READ ONLY"""
    resource = {
        "service_account": creds,
        "id": folder_url.split('/')[-1],
        "fields": "files(name,id,webViewLink)",
    }
    res = getfilelist.GetFileList(resource)
    return res

def main():
    st.title("📂 Growth List Manager V2")
    st.subheader("Database + Google Drive Edition (Mac)")
    
    # Simple usage explanation
    with st.expander("📖 How to Use This Page"):
        st.write("**Used for**: Checking how many people are left in your growth lists")
        st.write("**Steps**:")
        st.write("1. View all your Google Drive growth lists")
        st.write("2. See which lists are running low on people")
        st.write("3. Check which lists have been approved")
        st.write("4. Plan which lists need refilling")
        st.write("5. Track overall campaign performance")
    
    st.write("""
    This app manages growth lists stored in Google Drive and tracks their usage.
    """)
    
    # Show configuration
    with st.expander("Current Configuration"):
        st.text(f"Database: {database} on {server} (for usage tracking)")
        st.text(f"Google Drive: Connected for file management")
        st.text(f"Hybrid: Drive files + Database analytics")
    
    # Test connections
    st.subheader("Connection Tests")
    connections = test_connections()
    
    if not connections["google_drive"]:
        st.error("Google Drive connection required for file management.")
        return
    
    # Show database usage stats if available
    if connections["database"]:
        st.subheader("Database Usage Analytics")
        usage_stats = get_list_usage_stats()
        if not usage_stats.empty:
            st.dataframe(usage_stats, use_container_width=True)
        else:
            st.info("No usage statistics available yet.")
    
    # Google Drive file management (original functionality)
    st.subheader("📁 Google Drive Growth Lists (READ-ONLY)")
    st.info("🔒 This app only reads files - no modifications or deletions possible")
    
    folder_url = 'https://drive.google.com/drive/folders/13pKJYkrbDgEqva5eHJx0Nta66gLZwzz7'
    
    with st.spinner("Loading files from Google Drive..."):
        res = get_files_in_nested_folders(folder_url)
    
    # Process file records (same logic as original)
    file_records = []
    for file_list_item in res['fileList']:
        file_data = file_list_item.get('files', [])
        folder_tree = file_list_item.get('folderTree', [])
        
        for file_item in file_data:
            name = file_item.get('name', None)
            id = file_item.get('id', None)
            webViewLink = file_item.get('webViewLink', None)
            
            file_records.append({
                'name': name,
                'id': id,
                'webViewLink': webViewLink,
                'folderTree': folder_tree
            })
    
    # Process folder structure
    for record in file_records:
        folder_tree = record['folderTree']
        if len(folder_tree) > 0:
            record['folderTree'] = folder_tree[-1]
        else:
            record['folderTree'] = None
    
    files = pd.DataFrame(file_records, columns=["name", "id", "webViewLink", "folderTree"])
    
    if files.empty:
        st.warning("No files found in Google Drive folder.")
        return
    
    folder_tree_names = pd.DataFrame(res['folderTree'])
    folder_tree_names = folder_tree_names.rename(columns={"folders": "folderTree"})
    
    files = files.merge(folder_tree_names, on='folderTree', how='left')
    files = files.dropna(subset=['names'])

    # Filter files based on specified prefixes for performance, per user request
    prefixes_to_include = ['TBA_', 'DONE_', 'APPROVED_']
    files = files[files['name'].astype(str).str.startswith(tuple(prefixes_to_include), na=False)]

    files = files.merge(folder_tree_names['names'], on='names', how='right')

    # Filter for active profiles
    files['profile_folder'] = files['names'].apply(
        lambda x: 'yes' if 'active' in x.lower() else 'no'
    )
    files = files.drop(files[files['profile_folder'] == "no"].index)
    files['names'] = files['names'].str.replace('active', '', case=False)
    
    if files.empty:
        st.info("No active growth lists found.")
        return
    
    # Count rows in sheets using pygsheets (READ ONLY - no modifications)
    gc = pygsheets.authorize(custom_credentials=creds)
    
    total_lengths = []
    depleted_lengths = []
    rejected_lengths = []
    
    progress_bar = st.progress(0)
    status_text = st.empty()
    
    valid_files = files.dropna(subset=['webViewLink'])
    successful_processed = 0
    failed_files = []
    
    for i, (idx, row) in enumerate(valid_files.iterrows()):
        progress_bar.progress((i + 1) / len(valid_files))
        status_text.text(f"Processing file {i + 1} of {len(valid_files)}: {row['name'][:50]}...")
        
        try:
            sheet_id = row['webViewLink'].split('/')[-2]
            
            # Alternative approach: Try pygsheets first, fallback to direct API if needed
            try:
                # Method 1: pygsheets (usually works)
                sheet = gc.open_by_key(sheet_id)
                worksheet = sheet[0]
                all_values = worksheet.get_all_values()
            except Exception as pygsheets_error:
                # Method 2: Direct API call with proper authentication
                import gspread
                gc_gspread = gspread.authorize(creds)
                sheet_gspread = gc_gspread.open_by_key(sheet_id)
                worksheet_gspread = sheet_gspread.sheet1
                all_values = worksheet_gspread.get_all_values()
            
            if not all_values:
                total_lengths.append(0)
                depleted_lengths.append(0)
                rejected_lengths.append(0)
                continue
            
            header_row = all_values[0]
            
            if "Sent" not in header_row:
                # No "Sent" column, just count total rows
                total_count = len([row for row in all_values if any(row)])
                total_lengths.append(total_count)
                depleted_lengths.append(0)
                rejected_lengths.append(0)
                successful_processed += 1
                continue
            
            sent_column_index = header_row.index("Sent")
            total_count = sum(1 for row in all_values if any(row))
            depleted_count = sum(1 for row in all_values 
                               if len(row) > sent_column_index and row[sent_column_index] == "Depleted")
            rejected_count = sum(1 for row in all_values 
                               if len(row) > sent_column_index and row[sent_column_index] == "Rejected")
            
            total_lengths.append(total_count)
            depleted_lengths.append(depleted_count)
            rejected_lengths.append(rejected_count)
            successful_processed += 1
            
        except Exception as e:
            error_msg = f"{row['name']}: {str(e)}"
            failed_files.append(error_msg)
            total_lengths.append(0)
            depleted_lengths.append(0)
            rejected_lengths.append(0)
    
    progress_bar.empty()
    status_text.empty()
    
    # Show processing summary
    if failed_files:
        st.warning(f"⚠️ Processed {successful_processed}/{len(valid_files)} files. {len(failed_files)} files had issues:")
        with st.expander("🔍 View Failed Files (READ-ONLY ERRORS)"):
            for error in failed_files:
                st.text(f"• {error}")
            st.info("Note: These are read-only errors. No files were modified or deleted.")
    else:
        st.success(f"✅ Successfully processed all {successful_processed} files (READ-ONLY)")
    
    # Add metrics to dataframe
    files.loc[valid_files.index, 'length'] = total_lengths
    files.loc[valid_files.index, 'depleted'] = depleted_lengths
    files.loc[valid_files.index, 'rejected'] = rejected_lengths
    files['length'] = files['length'].fillna(0)
    files['depleted'] = files['depleted'].fillna(0)
    files['rejected'] = files['rejected'].fillna(0)
    files['available'] = files['length'] - (files['depleted'] + files['rejected'])
    files['approved'] = files['name'].apply(
        lambda x: 'yes' if 'approved' in str(x).lower() 
        else ('no' if isinstance(x, str) else np.nan)
    )
    
    # Display results grouped by client
    st.subheader("📊 Growth List Status by Client")
    
    # Summary metrics
    col1, col2, col3, col4 = st.columns(4)
    with col1:
        st.metric("📁 Total Lists", len(files))
    with col2:
        st.metric("👥 Total Names", int(files['length'].sum()))
    with col3:
        st.metric("✅ Available", int(files['available'].sum()))
    with col4:
        approved_count = (files['approved'] == 'yes').sum()
        st.metric("✅ Approved", approved_count)
    
    grouped = files.groupby('names')
    
    for name, group in grouped:
        with st.expander(f"👤 {name} ({len(group)} lists)", expanded=True):
            # Summary for this client
            client_total = group['length'].sum()
            client_available = group['available'].sum()
            client_approved = (group['approved'] == 'yes').sum()
            
            col1, col2, col3 = st.columns(3)
            with col1:
                st.metric("Total Names", int(client_total))
            with col2:
                st.metric("Available", int(client_available))
            with col3:
                st.metric("Approved Lists", client_approved)
            
            # Individual files
            for idx, row in group.iterrows():
                col1, col2, col3, col4 = st.columns([3, 1, 1, 1])
                
                with col1:
                    if pd.notna(row['webViewLink']):
                        st.markdown(f"**[{row['name']}]({row['webViewLink']})**")
                    else:
                        st.markdown(f"**{row['name']}** (No link)")
                with col2:
                    st.metric("Total", int(row['length']))
                with col3:
                    st.metric("Available", int(row['available']))
                with col4:
                    status = "✅ Approved" if row['approved'] == 'yes' else "⏳ Pending"
                    st.write(status)
    
    # Show database correlation if available
    if connections["database"] and not usage_stats.empty:
        st.subheader("📈 Database vs Drive Correlation")
        st.write("Compare Google Drive lists with actual invite activity from database:")
        
        # Merge drive data with database stats
        drive_summary = files.groupby('names').agg({
            'length': 'sum',
            'available': 'sum',
            'approved': lambda x: (x == 'yes').sum()
        }).reset_index()
        drive_summary = drive_summary.rename(columns={'names': 'ClientName'})
        
        correlation = pd.merge(drive_summary, usage_stats, on='ClientName', how='outer')
        correlation = correlation.fillna(0)
        
        st.dataframe(correlation, use_container_width=True)

if __name__ == "__main__":
    main()

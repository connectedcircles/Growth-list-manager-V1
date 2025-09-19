# =============================================================================
# FILE: 04_Pending_and_connected_excluder_FIXED.py
# PURPOSE: Filter Tool - Remove duplicates using LinkedIn profile IDs (Database Version)
# FIXED: Now uses LinkedIn profile URLs as unique identifiers + Excel support
# =============================================================================

import streamlit as st
import pandas as pd
import pymssql
import base64
import re

### STREAMLIT SECRETS CONFIGURATION ###################################
try:
    # Parse connection string from secrets
    conn_str = st.secrets["conn_str"]
    server_match = re.search(r'Server=([^;]+)', conn_str)
    database_match = re.search(r'Database=([^;]+)', conn_str)
    uid_match = re.search(r'UID=([^;]+)', conn_str)
    pwd_match = re.search(r'PWD=([^;]+)', conn_str)

    server = server_match.group(1) if server_match else None
    database = database_match.group(1) if database_match else None
    username = uid_match.group(1) if uid_match else None
    password = pwd_match.group(1) if pwd_match else None

    # Validate that all secrets are present
    if not all([server, database, username, password]):
        st.error("❌ Missing database connection details in secrets. Please check your Streamlit secrets configuration.")
        st.stop()

    st.info("🔐 Using Streamlit secrets for configuration.")

except KeyError as e:
    st.error(f"❌ Missing secret: {e}. Please check your Streamlit secrets configuration.")
    st.stop()
################################################################

def extract_linkedin_id(url):
    """Extract LinkedIn username/ID from profile URL"""
    if pd.isna(url) or not url:
        return None
    
    # Convert to string and clean
    url = str(url).strip()
    
    # Extract username from URLs like:
    # https://www.linkedin.com/in/wilbertstaring/
    # https://linkedin.com/in/wilbertstaring
    # www.linkedin.com/in/wilbertstaring
    match = re.search(r'linkedin\.com/in/([^/?#]+)', url)
    if match:
        linkedin_id = match.group(1).strip().lower()  # Normalize to lowercase
        return linkedin_id
    return None

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

def get_all_connections():
    """Get all connections from ProfilesX table with LinkedIn IDs"""
    try:
        conn = get_db_connection()
        query = "SELECT * FROM ProfilesX"
        df = pd.read_sql(query, conn)
        conn.close()
        
        # Extract LinkedIn IDs from ProfilePermaLink
        df['linkedin_id'] = df['ProfilePermaLink'].apply(extract_linkedin_id)
        
        # Show how many IDs were extracted
        valid_ids = df['linkedin_id'].notna().sum()
        st.sidebar.metric("Valid Connection IDs", f"{valid_ids:,}/{len(df):,}")
        
        return df
    except Exception as e:
        st.error(f"❌ Error loading connections: {str(e)}")
        return pd.DataFrame()

def get_invited_profiles():
    """Get all invited profiles from InvitedProfiles table with LinkedIn IDs"""
    try:
        conn = get_db_connection()
        query = "SELECT * FROM InvitedProfiles"
        df = pd.read_sql(query, conn)
        conn.close()
        
        # Extract LinkedIn IDs if ProfileURL column exists
        if 'ProfileURL' in df.columns:
            df['linkedin_id'] = df['ProfileURL'].apply(extract_linkedin_id)
        elif 'ProfileUrl' in df.columns:
            df['linkedin_id'] = df['ProfileUrl'].apply(extract_linkedin_id)
        else:
            # Fallback: Try to find any column with URLs
            url_columns = [col for col in df.columns if 'url' in col.lower() or 'link' in col.lower()]
            if url_columns:
                df['linkedin_id'] = df[url_columns[0]].apply(extract_linkedin_id)
            else:
                st.warning("⚠️ No profile URL column found in InvitedProfiles table")
                df['linkedin_id'] = None
        
        # Show how many IDs were extracted
        valid_ids = df['linkedin_id'].notna().sum()
        st.sidebar.metric("Valid Invited IDs", f"{valid_ids:,}/{len(df):,}")
        
        return df
    except Exception as e:
        st.error(f"❌ Error loading invited profiles: {str(e)}")
        return pd.DataFrame()

def read_uploaded_file(uploaded_file):
    """Read CSV or Excel file and return DataFrame"""
    try:
        # Check file extension
        file_name = uploaded_file.name.lower()
        
        if file_name.endswith('.csv'):
            # Read CSV
            df = pd.read_csv(uploaded_file, encoding='utf-8')
        elif file_name.endswith(('.xlsx', '.xls')):
            # Read Excel
            df = pd.read_excel(uploaded_file, engine='openpyxl')
        else:
            st.error("❌ Unsupported file format. Please upload CSV or Excel file.")
            return None
        
        return df
    except Exception as e:
        st.error(f"❌ Error reading file: {str(e)}")
        return None

def create_download_link(df, filename, link_text):
    """Create download link for dataframe"""
    try:
        csv = df.to_csv(index=False)
        b64 = base64.b64encode(csv.encode('utf-8')).decode()
        href = f'<a href="data:file/csv;base64,{b64}" download="{filename}">{link_text}</a>'
        return href
    except Exception as e:
        st.error(f"Error creating download link: {str(e)}")
        return f"Error: {link_text}"

def test_database_connection():
    """Test database connection"""
    try:
        conn = get_db_connection()
        cursor = conn.cursor()
        
        # Test both tables
        cursor.execute("SELECT COUNT(*) FROM ProfilesX")
        connections_count = cursor.fetchone()[0]
        
        cursor.execute("SELECT COUNT(*) FROM InvitedProfiles")
        invited_count = cursor.fetchone()[0]
        
        conn.close()
        
        st.success(f"✅ Database connected! ProfilesX: {connections_count:,}, InvitedProfiles: {invited_count:,}")
        return True
    except Exception as e:
        st.error(f"❌ Database connection failed: {str(e)}")
        return False

def app():
    st.title("🔍 Connection and Pending Invite Filter V3")
    st.subheader("Property of Connected Circles - **Fixed with LinkedIn ID Matching**")
    
    # Simple usage explanation
    with st.expander("🔖 How to Use This Page (UPDATED)"):
        st.write("**What's New:**")
        st.write("✅ Now uses LinkedIn profile URLs as unique identifiers (names can change!)")
        st.write("✅ Supports Excel (.xlsx) files in addition to CSV")
        st.write("")
        st.write("**Steps:**")
        st.write("1. Select your client name")
        st.write("2. Upload your growth list (CSV or Excel)")
        st.write("3. System removes people by matching LinkedIn profile IDs")
        st.write("4. Download the clean list")
        st.write("5. Use clean list for your campaign")
    
    # Sidebar for debugging info
    st.sidebar.title("🔧 Debug Info")
    
    # Show configuration
    with st.expander("🔧 Current Configuration"):
        st.text(f"Database: {database} on {server}")
        st.text(f"Tables: ProfilesX (connections) + InvitedProfiles (invites)")
        st.text(f"Matching Method: LinkedIn Profile IDs (from URLs)")
    
    # Test database connection
    st.subheader("🔐 Database Connection Test")
    if not test_database_connection():
        st.error("Cannot proceed without database connection.")
        return
    
    # Load data from database
    with st.spinner("Loading data from database..."):
        df_connections = get_all_connections()
        df_invited = get_invited_profiles()
    
    if df_connections.empty or df_invited.empty:
        st.error("Unable to load data from database. Please check connection.")
        return
    
    # Show data summary
    st.subheader("📊 Database Summary")
    col1, col2, col3 = st.columns(3)
    with col1:
        st.metric("Total Connections", len(df_connections))
    with col2:
        st.metric("Total Invited", len(df_invited))
    with col3:
        st.metric("Unique Clients", df_connections['Client'].nunique())
    
    # Client selection
    unique_clients = sorted(df_connections['Client'].unique())
    client_name = st.selectbox('🏢 Select Client', unique_clients)
    
    # Show client-specific stats
    client_connections = df_connections[df_connections['Client'] == client_name]
    client_invited = df_invited[df_invited['ClientName'] == client_name]
    
    col1, col2 = st.columns(2)
    with col1:
        st.info(f"{client_name} - Connections: {len(client_connections):,}")
    with col2:
        st.info(f"{client_name} - Invited: {len(client_invited):,}")
    
    # File uploader - NOW SUPPORTS EXCEL
    st.subheader("📂 Upload Growth List to Filter")
    uploaded_file = st.file_uploader(
        "Choose CSV or Excel file to filter", 
        type=["csv", "xlsx", "xls"],
        help="Must contain 'Full name' and 'Profile url' columns"
    )
    
    if uploaded_file is not None:
        # Read the file (CSV or Excel)
        growth_list = read_uploaded_file(uploaded_file)
        
        if growth_list is None:
            return
        
        # Validate required columns
        if 'Profile url' not in growth_list.columns:
            st.error("❌ File must contain 'Profile url' column for LinkedIn ID matching")
            st.info("Available columns in your file:")
            st.code(", ".join(growth_list.columns.tolist()))
            return
        
        st.success(f"✅ Growth list loaded: {len(growth_list):,} rows")
        
        # Extract LinkedIn IDs from growth list
        growth_list['linkedin_id'] = growth_list['Profile url'].apply(extract_linkedin_id)
        
        # Show LinkedIn ID extraction stats
        valid_ids = growth_list['linkedin_id'].notna().sum()
        st.info(f"📊 Extracted {valid_ids:,} valid LinkedIn IDs from growth list")
        
        if valid_ids == 0:
            st.error("❌ No valid LinkedIn profile URLs found in the uploaded file!")
            st.write("Sample URLs from file:")
            st.dataframe(growth_list[['Profile url']].head(5))
            return
        
        # Filter data for selected client
        df_connections_client = df_connections[df_connections['Client'] == client_name]
        df_invited_client = df_invited[df_invited['ClientName'] == client_name]
        
        # Get LinkedIn IDs to exclude
        connection_ids = set(df_connections_client['linkedin_id'].dropna())
        invited_ids = set(df_invited_client['linkedin_id'].dropna())
        
        st.sidebar.write(f"**{client_name} Stats:**")
        st.sidebar.write(f"Connection IDs: {len(connection_ids)}")
        st.sidebar.write(f"Invited IDs: {len(invited_ids)}")
        
        # Create filtered growth list
        growth_list_filtered = growth_list.copy()
        
        st.subheader("🔄 Filtering Process (Using LinkedIn IDs)")
        
        # Filter out already invited profiles
        initial_count = len(growth_list_filtered)
        growth_list_filtered = growth_list_filtered[
            ~growth_list_filtered['linkedin_id'].isin(invited_ids)
        ]
        invited_removed = initial_count - len(growth_list_filtered)
        
        # Filter out existing connections
        before_connections = len(growth_list_filtered)
        growth_list_filtered = growth_list_filtered[
            ~growth_list_filtered['linkedin_id'].isin(connection_ids)
        ]
        connections_removed = before_connections - len(growth_list_filtered)
        
        # Also do fallback name matching for any entries without LinkedIn IDs
        if 'Full name' in growth_list.columns:
            # Get names for fallback matching
            invited_names = set(df_invited_client['FullName'].dropna())
            connection_names = set(df_connections_client['Name'].dropna())
            
            # Filter entries without LinkedIn IDs by name
            no_id_mask = growth_list_filtered['linkedin_id'].isna()
            if no_id_mask.any():
                before_name_filter = len(growth_list_filtered)
                growth_list_filtered = growth_list_filtered[
                    ~((no_id_mask) & 
                      (growth_list_filtered['Full name'].isin(invited_names | connection_names)))
                ]
                name_removed = before_name_filter - len(growth_list_filtered)
                st.sidebar.write(f"Name fallback removed: {name_removed}")
        
        # Display results
        st.success("✅ Filtering Complete!")
        
        col1, col2, col3, col4 = st.columns(4)
        with col1:
            st.metric("📊 Original List", initial_count)
        with col2:
            st.metric("❌ Pending Invites", invited_removed, delta=f"-{invited_removed}")
        with col3:
            st.metric("👥 Existing Connections", connections_removed, delta=f"-{connections_removed}")
        with col4:
            st.metric("✅ Clean List", len(growth_list_filtered), delta=f"{len(growth_list_filtered) - initial_count}")
        
        # Show filtering efficiency
        if initial_count > 0:
            efficiency = (len(growth_list_filtered) / initial_count) * 100
            st.info(f"🎯 Filtering Efficiency: {efficiency:.1f}% of original list remains")
        
        # Show sample of filtered data
        if not growth_list_filtered.empty:
            st.subheader("Filtered Results Preview")
            
            # Drop the linkedin_id column before showing to user
            display_df = growth_list_filtered.drop(columns=['linkedin_id'], errors='ignore')
            st.dataframe(display_df.head(10), use_container_width=True)
            
            # Show removed samples for verification with LinkedIn IDs
            with st.expander("🔍 View Removed Entries (Sample with LinkedIn IDs)"):
                # Find removed entries
                removed_mask = growth_list['linkedin_id'].isin(invited_ids | connection_ids)
                removed_entries = growth_list[removed_mask].head(5)
                
                if not removed_entries.empty:
                    st.write("**Removed entries (showing LinkedIn ID matches):**")
                    display_cols = ['Full name', 'linkedin_id'] if 'Full name' in removed_entries.columns else ['linkedin_id']
                    if 'Profile url' in removed_entries.columns:
                        display_cols.append('Profile url')
                    st.dataframe(removed_entries[display_cols], use_container_width=True)
                    
                    # Show which database they matched with
                    for idx, row in removed_entries.iterrows():
                        lid = row['linkedin_id']
                        if lid in invited_ids:
                            st.write(f"• **{lid}** → Found in InvitedProfiles")
                        if lid in connection_ids:
                            st.write(f"• **{lid}** → Found in ProfilesX (Connections)")
            
            # Download links
            st.subheader("📥 Download Filtered Data")
            
            # Remove linkedin_id column from downloads
            download_df = growth_list_filtered.drop(columns=['linkedin_id'], errors='ignore')
            
            col1, col2 = st.columns(2)
            with col1:
                # Full filtered dataset
                full_link = create_download_link(
                    download_df, 
                    f"{client_name}_filtered_growth_list.csv",
                    "📄 Download Complete Filtered List"
                )
                st.markdown(full_link, unsafe_allow_html=True)
                st.text(f"Contains: {len(download_df)} records with all columns")
            
            with col2:
                # URLs only for browser extensions
                if 'Profile url' in download_df.columns:
                    urls_only = download_df[['Profile url']].dropna()
                    urls_link = create_download_link(
                        urls_only,
                        f"{client_name}_profile_urls.csv", 
                        "🔗 Download URLs Only"
                    )
                    st.markdown(urls_link, unsafe_allow_html=True)
                    st.text(f"Contains: {len(urls_only)} URLs for browser extensions")
            
            # Performance metrics
            st.subheader("⚡ Performance Metrics")
            col1, col2, col3 = st.columns(3)
            with col1:
                st.metric("🔍 Profiles Checked", initial_count)
            with col2:
                duplicates_found = invited_removed + connections_removed
                st.metric("🔄 Duplicates Found", duplicates_found)
            with col3:
                if initial_count > 0:
                    duplicate_rate = (duplicates_found / initial_count) * 100
                    st.metric("📊 Duplicate Rate", f"{duplicate_rate:.1f}%")
            
        else:
            st.warning("⚠️ No profiles remaining after filtering!")
            st.info("This means everyone in your growth list has either been invited or is already connected.")
            
            # Show debugging info
            st.subheader("🔍 Debug Information")
            st.write("Sample LinkedIn IDs from growth list:")
            st.code(growth_list['linkedin_id'].dropna().head(5).tolist())
            st.write("Sample LinkedIn IDs from connections:")
            st.code(list(connection_ids)[:5])
            st.write("Sample LinkedIn IDs from invited:")
            st.code(list(invited_ids)[:5])

if __name__ == "__main__":
    app()

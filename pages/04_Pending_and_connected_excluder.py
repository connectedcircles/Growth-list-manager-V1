# =============================================================================
# FILE: 04_Pending_and_connected_excluder_LOCAL_TEST.py
# PURPOSE: Filter Tool - Remove duplicates before campaigns (Database Version)
# =============================================================================

import streamlit as st
import pandas as pd
import pymssql
import base64

### STREAMLIT SECRETS CONFIGURATION ###################################
# This app is configured to use Streamlit secrets.
# For local development, create a .streamlit/secrets.toml file.
# For cloud deployment, add the secrets to your Streamlit Cloud app settings.
import re

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

    st.info("🔒 Using Streamlit secrets for configuration.")

except KeyError as e:
    st.error(f"❌ Missing secret: {e}. Please check your Streamlit secrets configuration.")
    st.stop()
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

def get_all_connections():
    """Get all connections from ProfilesX table"""
    try:
        conn = get_db_connection()
        query = "SELECT * FROM ProfilesX"
        df = pd.read_sql(query, conn)
        conn.close()
        return df
    except Exception as e:
        st.error(f"❌ Error loading connections: {str(e)}")
        return pd.DataFrame()

def get_invited_profiles():
    """Get all invited profiles from InvitedProfiles table (was Google Sheets)"""
    try:
        conn = get_db_connection()
        query = "SELECT * FROM InvitedProfiles"
        df = pd.read_sql(query, conn)
        conn.close()
        return df
    except Exception as e:
        st.error(f"❌ Error loading invited profiles: {str(e)}")
        return pd.DataFrame()

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
    st.title("🔍 Connection and Pending Invite Filter V2")
    st.subheader("Property of Connected Circles")
    
    # Simple usage explanation
    with st.expander("📖 How to Use This Page"):
        st.write("**Used for**: Cleaning growth lists before sending invites")
        st.write("**Steps**:")
        st.write("1. Select your client name")
        st.write("2. Upload your growth list CSV")
        st.write("3. System removes people you already invited or connected with")
        st.write("4. Download the clean list")
        st.write("5. Use clean list for your campaign")
    
    
    # Show configuration
    with st.expander("🔧 Current Configuration"):
        st.text(f"Database: {database} on {server}")
        st.text(f"Tables: ProfilesX (connections) + InvitedProfiles (invites)")
    
    # Test database connection
    st.subheader("🔍 Database Connection Test")
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
    
    # File uploader
    st.subheader("📂 Upload Growth List to Filter")
    uploaded_file = st.file_uploader(
        "Choose CSV file to filter", 
        type="csv",
        help="Must contain 'Full name' and 'Profile url' columns"
    )
    
    if uploaded_file is not None:
        try:
            growth_list = pd.read_csv(uploaded_file, encoding='utf-8')
            
            # Validate required columns
            if 'Full name' not in growth_list.columns:
                st.error("❌ CSV must contain 'Full name' column")
                st.info("Available columns in your file:")
                st.code(", ".join(growth_list.columns.tolist()))
                return
            
            st.success(f"✅ Growth list loaded: {len(growth_list):,} rows")
            
            # Filter data for selected client
            df_connections_client = df_connections[df_connections['Client'] == client_name]
            df_invited_client = df_invited[df_invited['ClientName'] == client_name]
            
            # Create filtered growth list
            growth_list_filtered = growth_list.copy()
            
            # Get lists of names to exclude
            invited_names = df_invited_client['FullName'].dropna().tolist()
            connection_names = df_connections_client['Name'].dropna().tolist()
            
            st.subheader("🔄 Filtering Process")
            
            # Filter out already invited profiles
            initial_count = len(growth_list_filtered)
            growth_list_filtered = growth_list_filtered[
                ~growth_list_filtered['Full name'].isin(invited_names)
            ]
            invited_removed = initial_count - len(growth_list_filtered)
            
            # Filter out existing connections
            before_connections = len(growth_list_filtered)
            growth_list_filtered = growth_list_filtered[
                ~growth_list_filtered['Full name'].isin(connection_names)
            ]
            connections_removed = before_connections - len(growth_list_filtered)
            
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
                st.dataframe(growth_list_filtered.head(10), use_container_width=True)
                
                # Show removed samples for verification
                with st.expander("🔍 View Removed Entries (Sample)"):
                    removed_invited = growth_list[growth_list['Full name'].isin(invited_names)].head(5)
                    removed_connections = growth_list[growth_list['Full name'].isin(connection_names)].head(5)
                    
                    if not removed_invited.empty:
                        st.write("**Removed - Already Invited:**")
                        st.dataframe(removed_invited[['Full name']], use_container_width=True)
                    
                    if not removed_connections.empty:
                        st.write("**Removed - Already Connected:**")
                        st.dataframe(removed_connections[['Full name']], use_container_width=True)
                
                # Download links
                st.subheader("📥 Download Filtered Data")
                
                col1, col2 = st.columns(2)
                with col1:
                    # Full filtered dataset
                    full_link = create_download_link(
                        growth_list_filtered, 
                        f"{client_name}_filtered_growth_list.csv",
                        "📄 Download Complete Filtered List"
                    )
                    st.markdown(full_link, unsafe_allow_html=True)
                    st.text(f"Contains: {len(growth_list_filtered)} records with all columns")
                
                with col2:
                    # URLs only for browser extensions
                    if 'Profile url' in growth_list_filtered.columns:
                        urls_only = growth_list_filtered[['Profile url']].dropna()
                        urls_link = create_download_link(
                            urls_only,
                            f"{client_name}_profile_urls.csv", 
                            "🔗 Download URLs Only"
                        )
                        st.markdown(urls_link, unsafe_allow_html=True)
                        st.text(f"Contains: {len(urls_only)} URLs for browser extensions")
                    else:
                        st.warning("No 'Profile url' column found for URL extraction")
                
                # Performance metrics
                st.subheader("⚡ Performance Metrics")
                col1, col2, col3 = st.columns(3)
                with col1:
                    st.metric("🔍 Names Checked", initial_count)
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
                
                # Show what was filtered out
                st.subheader("📊 Filtering Breakdown")
                col1, col2 = st.columns(2)
                with col1:
                    st.metric("Already Invited", invited_removed)
                    if invited_removed > 0:
                        invited_sample = growth_list[growth_list['Full name'].isin(invited_names)].head(3)
                        st.write("Sample already invited:")
                        st.dataframe(invited_sample[['Full name']], use_container_width=True)
                
                with col2:
                    st.metric("Already Connected", connections_removed)
                    if connections_removed > 0:
                        connected_sample = growth_list[growth_list['Full name'].isin(connection_names)].head(3)
                        st.write("Sample already connected:")
                        st.dataframe(connected_sample[['Full name']], use_container_width=True)
                
        except Exception as e:
            st.error(f"❌ File processing error: {str(e)}")
            st.info("Make sure your file is a valid CSV with UTF-8 encoding.")
            
            with st.expander("🔍 Detailed Error"):
                st.text(f"Error type: {type(e).__name__}")
                st.text(f"Error message: {str(e)}")

if __name__ == "__main__":
    app()

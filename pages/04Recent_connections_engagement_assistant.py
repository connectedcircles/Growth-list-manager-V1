# =============================================================================
# FILE: 04Recent_connections_engagement_assistant_LOCAL_TEST.py
# PURPOSE: Engagement Assistant - Recent connections for follow-up (Database Version)
# =============================================================================

import streamlit as st
import pandas as pd
import pymssql
import datetime
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

def make_clickable_link(val):
    """Create clickable URL link"""
    if pd.isna(val) or val == '':
        return ''
    return f'<a target="_blank" href="{val}">🔗 Open</a>'

# --- Saved Searches Database Functions ---
def get_saved_searches(conn):
    """Fetches all saved searches from the database."""
    query = "SELECT SearchID, SearchName, ClientName, Categories, TitleIncludeKeywords, TitleExcludeKeywords, OrganizationFilter, MinFollowers, MaxFollowers, ConnectedStartDate, ConnectedEndDate, InvitedStartDate, InvitedEndDate FROM SavedSearches ORDER BY SearchName"
    df = pd.read_sql(query, conn)
    return df

def save_search(conn, search_name, client_name, categories, title_include, title_exclude, org_filter, min_f, max_f, conn_start, conn_end, inv_start, inv_end):
    """Saves the current filter settings as a new search."""
    cursor = conn.cursor()
    insert_sql = """
    INSERT INTO SavedSearches (SearchName, ClientName, Categories, TitleIncludeKeywords, TitleExcludeKeywords, OrganizationFilter, MinFollowers, MaxFollowers, ConnectedStartDate, ConnectedEndDate, InvitedStartDate, InvitedEndDate)
    VALUES (%s, %s, %s, %s, %s, %s, %s, %s, %s, %s, %s, %s)
    """
    try:
        cursor.execute(insert_sql, (
            search_name,
            client_name,
            ",".join(categories) if categories else None,
            title_include,
            title_exclude,
            org_filter,
            min_f,
            max_f,
            conn_start,
            conn_end,
            inv_start,
            inv_end
        ))
        conn.commit()
        st.success(f"Search '{search_name}' saved successfully!")
    except pymssql.Error as e:
        st.error(f"Error saving search: {e}")
        conn.rollback()

def delete_search(conn, search_id):
    """Deletes a saved search by its ID."""
    cursor = conn.cursor()
    delete_sql = "DELETE FROM SavedSearches WHERE SearchID = %s"
    try:
        cursor.execute(delete_sql, (search_id,))
        conn.commit()
        st.success("Search deleted successfully!")
    except pymssql.Error as e:
        st.error(f"Error deleting search: {e}")
        conn.rollback()

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

def main():
    st.title("🤝 Recent Connections Engagement Assistant V2 - BETA")
    st.subheader("Recent Connections Engagement Assistant")
    
    # Simple usage explanation
    with st.expander("📖 How to Use This Page"):
        st.write("**Used for**: Following up with people who accepted your invites")
        st.write("**Steps**:")
        st.write("1. Select your client name")
        st.write("2. See list of people who accepted your invites")
        st.write("3. Click 'Posts URL' to see their recent LinkedIn activity")
        st.write("4. Like/comment on their posts")
        st.write("5. Build relationships before pitching")
    
   
    
    # Show configuration
    with st.expander("Current Configuration"):
        st.text(f"Database: {database} on {server}")
        st.text(f"Data: ProfilesX + InvitedProfiles [DB]")
    
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
    
    # Prepare invited profiles data (column mapping from Google Sheets to Database)
    df_invited_clean = df_invited.copy()
    df_invited_clean.rename(columns={'FullName': 'Name'}, inplace=True)
    
    # Create Posts URL for LinkedIn activity
    df_invited_clean['Posts_URL'] = df_invited_clean['ProfileURL'].apply(
        lambda x: f"{x}/recent-activity/all/" if pd.notna(x) and x != '' else ''
    )
    
    # Client selection
    unique_clients = sorted(df_connections['Client'].unique())
    client_name = st.selectbox("🏢 Select Client", unique_clients)
    
    # Show client summary
    client_connections = df_connections[df_connections['Client'] == client_name]
    client_invited = df_invited_clean[df_invited_clean['ClientName'] == client_name]
    
    # Define unique_categories here, after client_invited is available
    if not client_invited.empty:
        unique_categories = ["🌟 All Categories"] + sorted(
            client_invited['Category'].dropna().unique()
        )
    else:
        unique_categories = ["🌟 All Categories"] # Default if no invited profiles for client
    
    col1, col2, col3 = st.columns(3)
    with col1:
        st.metric("👥 Total Connections", len(client_connections))
    with col2:
        st.metric("📧 Total Invited", len(client_invited))
    with col3:
        # Calculate accepted (people who were invited AND are now connected)
        accepted = pd.merge(client_invited, client_connections[['Name']], on='Name', how='inner')
        st.metric("✅ Accepted", len(accepted))
    
    

    # Merge to find accepted connections (people invited who are now connected)
    df_accepted = pd.merge(
        client_invited, 
        client_connections[['Name', 'ProfileDate']], 
        on='Name', 
        how='inner'
    )
    
    if df_accepted.empty:
        st.info("No accepted connections found for this client.")
        st.info("This means none of the people you invited have accepted yet, or there's a data mismatch.")
        
        # Show debugging info
        with st.expander("🔍 Debugging Information"):
            st.write("**Sample Invited Names:**")
            st.dataframe(client_invited[['Name']].head(), use_container_width=True)
            st.write("**Sample Connection Names:**")
            st.dataframe(client_connections[['Name']].head(), use_container_width=True)
        
        return
    
    # Prepare display data (column mapping)
    df_display = df_accepted[[
        "Name", "Title", "Organization1", "ProfileURL", "Posts_URL", 
        "Followers", "Category", "DateCollected", "ProfileDate"
    ]].copy()
    
    # Rename columns for better display
    df_display.rename(columns={
        "Organization1": "Organization",
        "Posts_URL": "Posts URL",
        "DateCollected": "Invited On",
        "ProfileDate": "Connected On (Approx)",
        "ProfileURL": "Profile URL"
    }, inplace=True)

    # --- Saved Searches ---
    st.subheader("Saved Searches")
    db_conn = get_db_connection() # Get a fresh connection for saved searches
    saved_searches_df = get_saved_searches(db_conn)
    db_conn.close() # Close connection immediately

    search_names = ["-- Select a saved search --"] + saved_searches_df['SearchName'].tolist()
    selected_saved_search_name = st.selectbox("Load Saved Search", search_names)

    if selected_saved_search_name != "-- Select a saved search --":
        selected_search_data = saved_searches_df[saved_searches_df['SearchName'] == selected_saved_search_name].iloc[0]
        
        # Populate session state with loaded values
        st.session_state['selected_categories'] = selected_search_data['Categories'].split(',') if selected_search_data['Categories'] else ["🌟 All Categories"]
        st.session_state['title_include_keywords'] = selected_search_data['TitleIncludeKeywords'] if pd.notna(selected_search_data['TitleIncludeKeywords']) else ""
        st.session_state['title_exclude_keywords'] = selected_search_data['TitleExcludeKeywords'] if pd.notna(selected_search_data['TitleExcludeKeywords']) else ""
        st.session_state['org_filter'] = selected_search_data['OrganizationFilter'] if pd.notna(selected_search_data['OrganizationFilter']) else ""
        st.session_state['min_followers'] = int(selected_search_data['MinFollowers']) if pd.notna(selected_search_data['MinFollowers']) else 0
        st.session_state['max_followers'] = int(selected_search_data['MaxFollowers']) if pd.notna(selected_search_data['MaxFollowers']) else 0
        st.session_state['connected_start'] = selected_search_data['ConnectedStartDate'] if pd.notna(selected_search_data['ConnectedStartDate']) else datetime.date(2020, 1, 1)
        st.session_state['connected_end'] = selected_search_data['ConnectedEndDate'] if pd.notna(selected_search_data['ConnectedEndDate']) else datetime.date.today()
        st.session_state['invited_start'] = selected_search_data['InvitedStartDate'] if pd.notna(selected_search_data['InvitedStartDate']) else datetime.date(2020, 1, 1)
        st.session_state['invited_end'] = selected_search_data['InvitedEndDate'] if pd.notna(selected_search_data['InvitedEndDate']) else datetime.date.today()
        st.session_state['client_name_from_search'] = selected_search_data['ClientName'] # Store client name from search

        st.rerun() # Rerun to apply filters

    # Delete search
    if selected_saved_search_name != "-- Select a saved search --":
        if st.button("🗑️ Delete Selected Search"):
            search_id_to_delete = saved_searches_df[saved_searches_df['SearchName'] == selected_saved_search_name]['SearchID'].iloc[0]
            db_conn = get_db_connection()
            delete_search(db_conn, search_id_to_delete)
            db_conn.close()
            st.rerun() # Rerun to update list

    # --- Filter UI ---
    st.subheader("Filter Connections")

    # Initialize session state for filters if not already present
    if 'selected_categories' not in st.session_state:
        st.session_state['selected_categories'] = ["🌟 All Categories"]
    if 'title_include_keywords' not in st.session_state:
        st.session_state['title_include_keywords'] = ""
    if 'title_exclude_keywords' not in st.session_state:
        st.session_state['title_exclude_keywords'] = ""
    if 'org_filter' not in st.session_state:
        st.session_state['org_filter'] = ""
    if 'min_followers' not in st.session_state:
        st.session_state['min_followers'] = 0
    if 'max_followers' not in st.session_state:
        st.session_state['max_followers'] = 0
    if 'connected_start' not in st.session_state:
        st.session_state['connected_start'] = datetime.date(2020, 1, 1) # Reasonable start date
    if 'connected_end' not in st.session_state:
        st.session_state['connected_end'] = datetime.date.today()
    if 'invited_start' not in st.session_state:
        st.session_state['invited_start'] = datetime.date(2020, 1, 1) # Reasonable start date
    if 'invited_end' not in st.session_state:
        st.session_state['invited_end'] = datetime.date.today()
    if 'client_name_from_search' not in st.session_state:
        st.session_state['client_name_from_search'] = client_name # Default to current client

    # Update client selection based on saved search if applicable
    if 'client_name_from_search' in st.session_state and st.session_state['client_name_from_search'] in unique_clients:
        client_name = st.session_state['client_name_from_search']
        client_name_index = unique_clients.index(client_name)
    else:
        client_name_index = 0
        
    # Update the client selection to reflect any changes from saved search
    client_name = st.selectbox(
        "🏢 Current Client Filter",
        unique_clients,
        index=client_name_index,
        key='main_client_selector'
    )
    
    # Update client-specific data based on current selection
    client_connections = df_connections[df_connections['Client'] == client_name]
    client_invited = df_invited_clean[df_invited_clean['ClientName'] == client_name]
    
    # Update categories for current client
    if not client_invited.empty:
        unique_categories = ["🌟 All Categories"] + sorted(
            client_invited['Category'].dropna().unique()
        )
    else:
        unique_categories = ["🌟 All Categories"]
    
    # Merge to find accepted connections (people invited who are now connected)
    df_accepted = pd.merge(
        client_invited, 
        client_connections[['Name', 'ProfileDate']], 
        on='Name', 
        how='inner'
    )
    
    if df_accepted.empty:
        st.info("No accepted connections found for this client.")
        st.info("This means none of the people you invited have accepted yet, or there's a data mismatch.")
        
        # Show debugging info
        with st.expander("🔍 Debugging Information"):
            st.write("**Sample Invited Names:**")
            if not client_invited.empty:
                st.dataframe(client_invited[['Name']].head(), use_container_width=True)
            else:
                st.write("No invited profiles for this client")
            st.write("**Sample Connection Names:**")
            if not client_connections.empty:
                st.dataframe(client_connections[['Name']].head(), use_container_width=True)
            else:
                st.write("No connections for this client")
        
        return
    
    # Prepare display data (column mapping)
    df_display = df_accepted[[
        "Name", "Title", "Organization1", "ProfileURL", "Posts_URL", 
        "Followers", "Category", "DateCollected", "ProfileDate"
    ]].copy()
    
    # Rename columns for better display
    df_display.rename(columns={
        "Organization1": "Organization",
        "Posts_URL": "Posts URL",
        "DateCollected": "Invited On",
        "ProfileDate": "Connected On (Approx)",
        "ProfileURL": "Profile URL"
    }, inplace=True)

    # Category selection
    selected_categories = st.multiselect(
        "📂 Select Categories",
        unique_categories,
        default=st.session_state['selected_categories'],
        key='category_selector' # Add a key
    )

    # Advanced Filters Expander
    with st.expander("Advanced Filters"):
        # Title filters
        col_title1, col_title2 = st.columns(2)
        with col_title1:
            title_include_keywords = st.text_input("Include Title Keywords (comma-separated)", value=st.session_state['title_include_keywords'], key='title_include')
        with col_title2:
            title_exclude_keywords = st.text_input("Exclude Title Keywords (comma-separated)", value=st.session_state['title_exclude_keywords'], key='title_exclude')

        # Organization filter
        org_filter = st.text_input("Filter by Organization (contains)", value=st.session_state['org_filter'], key='org_filter')

        # Follower range filter
        st.markdown("---")
        st.markdown("**Follower Count Range:**")
        col_followers1, col_followers2 = st.columns(2)
        with col_followers1:
            min_followers = st.number_input("Minimum Followers", min_value=0, value=st.session_state['min_followers'], key='min_followers')
        with col_followers2:
            max_followers = st.number_input("Maximum Followers", min_value=0, value=st.session_state['max_followers'], key='max_followers')
            if max_followers == 0: # If max is 0, treat as no upper limit
                max_followers = df_display['Followers'].max() + 1 # Set to a value higher than any existing follower count

        # Date range filters
        st.markdown("---")
        st.markdown("**Connected Between:**")
        col_conn_date1, col_conn_date2 = st.columns(2)
        connected_start = col_conn_date1.date_input("Connected Start Date", value=st.session_state['connected_start'], key='conn_start')
        connected_end = col_conn_date2.date_input("Connected End Date", value=st.session_state['connected_end'], key='conn_end')

        st.markdown("---")
        col_inv_date1, col_inv_date2 = st.columns(2)
        invited_start = col_inv_date1.date_input("Invited Start Date", value=st.session_state['invited_start'], key='inv_start')
        invited_end = col_inv_date2.date_input("Invited End Date", value=st.session_state['invited_end'], key='inv_end')

    # Save Search
    st.markdown("---")
    new_search_name = st.text_input("Name for new saved search")
    if st.button("💾 Save Current Search"):
        if new_search_name:
            db_conn = get_db_connection()
            save_search(
                db_conn,
                new_search_name,
                client_name,
                selected_categories,
                title_include_keywords,
                title_exclude_keywords,
                org_filter,
                min_followers,
                max_followers,
                connected_start,
                connected_end,
                invited_start,
                invited_end
            )
            db_conn.close()
            st.rerun()
        else:
            st.warning("Please enter a name for the search.")

    # --- Apply Filters ---

    # Category filter
    if "🌟 All Categories" not in selected_categories:
        df_display = df_display[df_display['Category'].isin(
            [cat for cat in selected_categories if cat != "🌟 All Categories"]
        )]

    # Title include/exclude
    if title_include_keywords:
        include_patterns = [k.strip() for k in title_include_keywords.split(',') if k.strip()]
        if include_patterns:
            df_display = df_display[df_display['Title'].astype(str).str.contains('|'.join(include_patterns), case=False, na=False)]

    if title_exclude_keywords:
        exclude_patterns = [k.strip() for k in title_exclude_keywords.split(',') if k.strip()]
        if exclude_patterns:
            df_display = df_display[~df_display['Title'].astype(str).str.contains('|'.join(exclude_patterns), case=False, na=False)]

    # Organization filter
    if org_filter:
        df_display = df_display[df_display['Organization'].astype(str).str.contains(org_filter, case=False, na=False)]

    # Follower range filter
    df_display = df_display[
        (df_display['Followers'] >= min_followers) &
        (df_display['Followers'] <= max_followers)
    ]

    # Ensure date columns are datetime objects before filtering
    df_display['Connected On (Approx)'] = pd.to_datetime(df_display['Connected On (Approx)'])
    df_display['Invited On'] = pd.to_datetime(df_display['Invited On'])

    # Apply date filters
    df_display = df_display[
        (df_display['Connected On (Approx)'].dt.date >= connected_start) &
        (df_display['Connected On (Approx)'].dt.date <= connected_end)
    ]
    df_display = df_display[
        (df_display['Invited On'].dt.date >= invited_start) &
        (df_display['Invited On'].dt.date <= invited_end)
    ]

    # Sort by most recent connections
    df_display = df_display.sort_values(by='Connected On (Approx)', ascending=False)
    
    # Display options
    col1, col2, col3 = st.columns(3)
    with col1:
        display_as_dataframe = st.checkbox("📊 Display as raw dataframe", value=False)
    with col2:
        st.metric("👥 Recent Connections", len(df_display))
    with col3:
        if not df_display.empty:
            avg_followers = df_display['Followers'].mean()
            st.metric("📈 Avg Followers", f"{avg_followers:,.0f}")
    
    # Display results
    if not df_display.empty:
        st.subheader(f"📋 Recent Connections for {client_name}")
        
        # Show category breakdown
        if len(selected_categories) > 1 or "🌟 All Categories" in selected_categories:
            category_counts = df_display['Category'].value_counts()
            with st.expander(f"📊 Category Breakdown ({len(df_display)} total)"):
                for category, count in category_counts.items():
                    st.text(f"• {category}: {count} connections")
        
        if display_as_dataframe:
            # Raw dataframe display with download option
            st.dataframe(df_display, use_container_width=True)
            
            # Download option
            csv = df_display.to_csv(index=False)
            st.download_button(
                label="📥 Download Connections Data",
                data=csv,
                file_name=f"{client_name}_recent_connections.csv",
                mime="text/csv"
            )
        else:
            # Enhanced display with clickable links
            df_display_html = df_display.copy()
            df_display_html['Profile URL'] = df_display_html['Profile URL'].apply(make_clickable_link)
            df_display_html['Posts URL'] = df_display_html['Posts URL'].apply(make_clickable_link)
            
            # Custom styling
            st.markdown("""
            <style>
            table {
                width: 100%;
                border-collapse: collapse;
            }
            th, td {
                padding: 8px;
                text-align: left;
                border-bottom: 1px solid #ddd;
            }
            th {
                background-color: #f2f2f2;
                font-weight: bold;
            }
            tr:hover {
                background-color: #f5f5f5;
            }
            .recent {
                background-color: #e8f5e8;
            }
            </style>
            """, unsafe_allow_html=True)
            
            # Highlight recent connections (last 7 days)
            if 'Connected On (Approx)' in df_display_html.columns:
                try:
                    df_display_html['Connected On (Approx)'] = pd.to_datetime(df_display_html['Connected On (Approx)'])
                    recent_threshold = pd.Timestamp.now() - pd.Timedelta(days=7)
                    recent_mask = df_display_html['Connected On (Approx)'] > recent_threshold
                    if recent_mask.any():
                        st.info(f"💡 {recent_mask.sum()} connections from the last 7 days are highlighted below")
                except:
                    pass  # If date parsing fails, just display normally
            
            st.write(df_display_html.to_html(index=False, escape=False), unsafe_allow_html=True)
            
            # Quick engagement tips
            with st.expander("💡 Engagement Tips"):
                st.write("""
                **Best Practices for Recent Connections:**
                - Click "Posts URL" to see their recent LinkedIn activity
                - Like and comment on their posts within 48 hours of connecting
                - Look for posts about achievements, company news, or industry insights
                - Avoid sales-focused comments initially - focus on building relationship
                - Share relevant content that might interest them
                """)
        
        # Show engagement statistics
        with st.expander("📊 Engagement Statistics"):
            if 'Connected On (Approx)' in df_display.columns:
                try:
                    df_display['Connected On (Approx)'] = pd.to_datetime(df_display['Connected On (Approx)'])
                    
                    # Connections by time period
                    now = pd.Timestamp.now()
                    last_7_days = (df_display['Connected On (Approx)'] > (now - pd.Timedelta(days=7))).sum()
                    last_30_days = (df_display['Connected On (Approx)'] > (now - pd.Timedelta(days=30))).sum()
                    last_90_days = (df_display['Connected On (Approx)'] > (now - pd.Timedelta(days=90))).sum()
                    
                    col1, col2, col3 = st.columns(3)
                    with col1:
                        st.metric("Last 7 Days", last_7_days)
                    with col2:
                        st.metric("Last 30 Days", last_30_days)
                    with col3:
                        st.metric("Last 90 Days", last_90_days)
                        
                except:
                    st.text("Date analysis not available")
    else:
        st.info("No connections found matching your criteria.")
        
        # Suggest actions
        st.subheader("💡 Suggestions")
        st.write("Try:")
        st.write("- Selecting different categories")
        st.write("- Checking if there are recent invites that haven't been accepted yet")
        st.write("- Verifying data synchronization between invite logs and connection data")

if __name__ == '__main__':
    main()

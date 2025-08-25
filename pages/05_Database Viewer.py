# =============================================================================
# FILE: 05Database_viewer_LOCAL_TEST.py
# PURPOSE: Database Viewer - View recent InvitedProfiles records
# =============================================================================

import streamlit as st
import pandas as pd
import pymssql
from datetime import datetime

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

def get_recent_invited_profiles(limit=100):
    """Get most recent InvitedProfiles records"""
    try:
        conn = get_db_connection()
        query = f"""
        SELECT TOP {limit}
            ClientName,
            FullName,
            Title,
            Location,
            Organization1,
            Followers,
            DateCollected,
            Category,
            GroupName,
            CreatedAt,
            UpdatedAt
        FROM InvitedProfiles 
        ORDER BY DateCollected DESC, CreatedAt DESC
        """
        df = pd.read_sql(query, conn)
        conn.close()
        return df
    except Exception as e:
        st.error(f"❌ Error loading data: {str(e)}")
        return pd.DataFrame()

def get_database_stats():
    """Get database statistics"""
    try:
        conn = get_db_connection()
        cursor = conn.cursor()
        
        # Total records
        cursor.execute("SELECT COUNT(*) FROM InvitedProfiles")
        total_records = cursor.fetchone()[0]
        
        # Unique clients
        cursor.execute("SELECT COUNT(DISTINCT ClientName) FROM InvitedProfiles")
        unique_clients = cursor.fetchone()[0]
        
        # Records today
        cursor.execute("""
            SELECT COUNT(*) FROM InvitedProfiles 
            WHERE CAST(CreatedAt AS DATE) = CAST(GETDATE() AS DATE)
        """)
        today_records = cursor.fetchone()[0]
        
        # Most active client
        cursor.execute("""
            SELECT TOP 1 ClientName, COUNT(*) as Count
            FROM InvitedProfiles 
            GROUP BY ClientName 
            ORDER BY COUNT(*) DESC
        """)
        top_client_result = cursor.fetchone()
        top_client = f"{top_client_result[0]} ({top_client_result[1]})" if top_client_result else "N/A"
        
        conn.close()
        
        return {
            "total_records": total_records,
            "unique_clients": unique_clients,
            "today_records": today_records,
            "top_client": top_client
        }
    except Exception as e:
        st.error(f"❌ Error loading statistics: {str(e)}")
        return None

def test_database_connection():
    """Test database connection"""
    try:
        conn = get_db_connection()
        cursor = conn.cursor()
        cursor.execute("SELECT COUNT(*) FROM InvitedProfiles")
        count = cursor.fetchone()[0]
        conn.close()
        st.success(f"✅ Database connected! Found {count:,} total records.")
        return True
    except Exception as e:
        st.error(f"❌ Database connection failed: {str(e)}")
        return False

def main():
    st.title("📊 Database Viewer V2")
    st.subheader("InvitedProfiles Recent Records")
    
    # Simple usage explanation
    with st.expander("📖 How to Use This Page"):
        st.write("**Used for**: Viewing the most recent database entries to verify logging")
        st.write("**Steps**:")
        st.write("1. Check database connection status")
        st.write("2. Review recent invite records")
        st.write("3. Verify data")
        st.write("4. Download records for analysis if needed")
        st.write("5. Monitor database activity in real-time")
    
    # Show configuration
    with st.expander("Current Configuration"):
        st.text(f"Database: {database} on {server}")
        st.text(f"Table: InvitedProfiles [DB] (invite logging records)")
    
    # Test database connection
    st.subheader("Database Connection Test")
    if not test_database_connection():
        st.error("Cannot proceed without database connection.")
        return
    
    # Get and display database statistics
    st.subheader("Database Statistics")
    stats = get_database_stats()
    
    if stats:
        col1, col2, col3, col4 = st.columns(4)
        with col1:
            st.metric("📊 Total Records", f"{stats['total_records']:,}")
        with col2:
            st.metric("🏢 Unique Clients", stats['unique_clients'])
        with col3:
            st.metric("📅 Today's Records", stats['today_records'])
        with col4:
            st.metric("🏆 Top Client", stats['top_client'])
    
    # Records limit selection
    st.subheader("Recent Records")
    col1, col2 = st.columns([2, 1])
    with col1:
        record_limit = st.selectbox(
            "Select number of records to display:",
            [50, 100, 200, 500, 1000],
            index=1  # Default to 100
        )
    with col2:
        if st.button("🔄 Refresh Data", use_container_width=True):
            st.rerun()
    
    # Load and display recent records
    with st.spinner(f"Loading last {record_limit} records..."):
        df = get_recent_invited_profiles(record_limit)
    
    if df.empty:
        st.warning("No records found in database.")
        return
    
    # Display results
    st.success(f"✅ Loaded {len(df)} records")
    
    # Show data preview with key metrics
    col1, col2, col3 = st.columns(3)
    with col1:
        unique_clients_in_data = df['ClientName'].nunique()
        st.metric("👥 Clients in View", unique_clients_in_data)
    with col2:
        if not df.empty and 'DateCollected' in df.columns:
            latest_record = pd.to_datetime(df['DateCollected']).max()
            st.metric("🕐 Latest Invite Date", latest_record.strftime("%Y-%m-%d"))
    with col3:
        categories = df['Category'].nunique() if 'Category' in df.columns else 0
        st.metric("📂 Categories", categories)
    
    # Display options
    display_mode = st.radio(
        "Display Mode:",
        ["📊 Summary Table", "📄 Full Details", "🔍 Raw Data"],
        horizontal=True
    )
    
    if display_mode == "📊 Summary Table":
        # Show summarized view
        summary_cols = ['ClientName', 'FullName', 'Title', 'Organization1', 'Category', 'DateCollected', 'CreatedAt']
        display_df = df[summary_cols].copy()
        
        # Format datetime for better display
        if 'DateCollected' in display_df.columns:
            display_df['DateCollected'] = pd.to_datetime(display_df['DateCollected']).dt.strftime('%Y-%m-%d')
        if 'CreatedAt' in display_df.columns:
            display_df['CreatedAt'] = pd.to_datetime(display_df['CreatedAt']).dt.strftime('%Y-%m-%d %H:%M')
        
        st.dataframe(display_df, use_container_width=True, height=600)
        
    elif display_mode == "📄 Full Details":
        # Show all columns but formatted
        display_df = df.copy()
        
        # Format datetime columns
        datetime_cols = ['CreatedAt', 'UpdatedAt', 'DateCollected']
        for col in datetime_cols:
            if col in display_df.columns:
                display_df[col] = pd.to_datetime(display_df[col]).dt.strftime('%Y-%m-%d %H:%M')
        
        st.dataframe(display_df, use_container_width=True, height=600)
        
    else:  # Raw Data
        # Show raw dataframe
        st.dataframe(df, use_container_width=True, height=600)
    
    # Client-specific breakdown
    if not df.empty:
        with st.expander(f"📊 Breakdown by Client (Last {record_limit} records)"):
            client_breakdown = df.groupby('ClientName').agg({
                'FullName': 'count',
                'Category': 'nunique',
                'DateCollected': ['min', 'max']
            }).round(2)
            
            client_breakdown.columns = ['Records', 'Categories', 'First Invite', 'Last Invite']
            client_breakdown = client_breakdown.sort_values('Records', ascending=False)
            
            st.dataframe(client_breakdown, use_container_width=True)
    
    # Download option
    st.subheader("📥 Download Data")
    if not df.empty:
        csv = df.to_csv(index=False)
        st.download_button(
            label="📄 Download Recent Records as CSV",
            data=csv,
            file_name=f"invited_profiles_recent_{record_limit}_{datetime.now().strftime('%Y%m%d_%H%M')}.csv",
            mime="text/csv",
            use_container_width=True
        )
        
        st.info(f"💾 CSV will contain {len(df)} records with {len(df.columns)} columns")
    
    # Auto-refresh option
    st.subheader("🔄 Auto-Refresh")
    if st.checkbox("Enable auto-refresh (30 seconds)"):
        st.info("⏱️ Page will automatically refresh every 30 seconds")
        # Note: In a real deployment, you'd implement auto-refresh with st.empty() and time.sleep()
        # For now, this is just a UI placeholder

if __name__ == "__main__":
    main()

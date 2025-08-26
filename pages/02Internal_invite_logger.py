import pandas as pd
import streamlit as st
import datetime
import pymssql
from slack_sdk import WebClient

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

    # Slack credentials
    slack_token = st.secrets["slack_token"]
    target_channel_id = st.secrets["target_channel_id"]

    # Validate that all secrets are present
    if not all([server, database, username, password, slack_token, target_channel_id]):
        st.error("❌ Missing one or more secrets. Please check your Streamlit secrets configuration.")
        st.stop()

    st.info("🔒 Using Streamlit secrets for configuration.")

except KeyError as e:
    st.error(f"❌ Missing secret: {e}. Please check your Streamlit secrets configuration.")
    st.stop()
################################################################

# Initialize Slack WebClient
slack_client = WebClient(token=slack_token) if slack_token else None

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

def insert_to_database(df, ClientName, Category, DateInvited_str, growth_list_url):
    """Insert invite data directly to InvitedProfiles table"""
    try:
        conn = get_db_connection()
        cursor = conn.cursor()
        
        inserted_count = 0
        errors = []
        
        st.info("🔄 Processing CSV data...")
        progress_bar = st.progress(0)
        
        for index, row in df.iterrows():
            try:
                # Update progress
                progress_bar.progress((index + 1) / len(df))
                
                cursor.execute("""
                    INSERT INTO InvitedProfiles 
                    (ClientName, FullName, ProfileURL, Title, Location, Organization1, 
                     Followers, DateCollected, GroupName, Category, CreatedAt, UpdatedAt)
                    VALUES (%s, %s, %s, %s, %s, %s, %s, %s, %s, %s, GETDATE(), GETDATE())
                """, (
                    ClientName,
                    str(row.get('Full name', '')),
                    str(row.get('Profile url', '')),
                    str(row.get('Title', '')),
                    str(row.get('Location', '')),
                    str(row.get('Organization 1', '')),
                    int(row.get('Followers', 0)) if pd.notna(row.get('Followers', 0)) and str(row.get('Followers', 0)).replace(',', '').isdigit() else 0,
                    DateInvited_str,
                    growth_list_url,
                    Category
                ))
                inserted_count += 1
            except Exception as row_error:
                errors.append(f"Row {index + 1} ({row.get('Full name', 'Unknown')}): {str(row_error)}")
                continue
        
        progress_bar.empty()
        conn.commit()
        conn.close()
        
        if errors:
            st.warning(f"⚠️ Inserted {inserted_count} records. {len(errors)} errors:")
            with st.expander("🔍 View Errors"):
                for error in errors:
                    st.text(f"• {error}")
        else:
            st.success(f"✅ Successfully inserted {inserted_count} records!")
        
        # Send Slack notification
        if inserted_count > 0 and slack_client:
            message = f"LOCAL TEST: {ClientName}, {inserted_count} profiles, \"{Category}\", {DateInvited_str}, {growth_list_url}"
            send_slack_message(message)
        elif inserted_count > 0:
            st.info("📢 Slack disabled for local testing")
        
        # Show verification SQL
        st.subheader("🔍 Verify in Database")
        verification_sql = f"""
-- Run this SQL to verify your data was inserted:
SELECT TOP 10 * FROM InvitedProfiles 
WHERE ClientName = '{ClientName}' 
AND Category = '{Category}'
AND DateCollected = '{DateInvited_str}'
ORDER BY CreatedAt DESC
        """
        st.code(verification_sql, language='sql')
        
    except Exception as e:
        st.error(f"❌ Database error: {str(e)}")
        with st.expander("🔍 Connection Details"):
            st.text(f"Server: {server}")
            st.text(f"Database: {database}")
            st.text(f"Username: {username}")
            st.text(f"Error type: {type(e).__name__}")

def send_slack_message(message):
    """Send notification to Slack channel"""
    if not slack_client:
        st.info("📢 Slack notifications disabled")
        return
        
    try:
        response = slack_client.chat_postMessage(
            channel=target_channel_id,
            text=message
        )
        if response["ok"]:
            st.success("📢 Slack notification sent successfully!")
        else:
            st.error(f"❌ Slack error: {response['error']}")
    except Exception as e:
        st.error(f"Slack connection error: {str(e)}")

def get_invited_profiles():
    """Get all invited profiles from database"""
    try:
        conn = get_db_connection()
        query = "SELECT * FROM InvitedProfiles ORDER BY CreatedAt DESC"
        df = pd.read_sql(query, conn)
        conn.close()
        return df
    except Exception as e:
        st.error(f"❌ Database connection error: {str(e)}")
        return pd.DataFrame()

def test_database_connection():
    """Test if database connection works"""
    try:
        conn = get_db_connection()
        cursor = conn.cursor()
        cursor.execute("SELECT COUNT(*) FROM InvitedProfiles")
        count = cursor.fetchone()[0]
        
        # Get some recent records for preview
        cursor.execute("""
            SELECT TOP 5 ClientName, Category, DateCollected, COUNT(*) as Records
            FROM InvitedProfiles 
            GROUP BY ClientName, Category, DateCollected
            ORDER BY MAX(CreatedAt) DESC
        """)
        recent_data = cursor.fetchall()
        
        conn.close()
        
        st.success(f"✅ Database connected successfully! Found {count:,} existing records.")
        
        if recent_data:
            st.info("📊 Recent activity:")
            for row in recent_data:
                st.text(f"• {row[0]} - {row[1]} - {row[2]} ({row[3]} records)")
        
        return True
    except Exception as e:
        st.error(f"❌ Database connection failed: {str(e)}")
        st.info("💡 Common fixes:")
        st.text("• Check if your IP is in Azure SQL firewall rules")
        st.text("• Verify internet connection")
        st.text("• Ensure database server is accessible")
        
        return False

def test_slack_connection():
    """Test Slack connection"""
    if not slack_client:
        st.warning("📢 Slack client not initialized")
        return False
        
    try:
        # Test by getting channel info
        response = slack_client.conversations_info(channel=target_channel_id)
        if response["ok"]:
            channel_name = response["channel"]["name"]
            st.success(f"✅ Slack connected! Target channel: #{channel_name}")
            return True
        else:
            st.error(f"❌ Slack channel error: {response['error']}")
            return False
    except Exception as e:
        st.error(f"Slack connection error: {str(e)}")
        return False

def app():
    st.title("Growth Invite Logger V2")
    st.subheader("Property of Connected Circles")
    
    # Simple usage explanation
    with st.expander("📖 How to Use This Page"):
        st.write("**Used for**: Logging LinkedIn invites you sent")
        st.write("**Steps**:")
        st.write("1. Send LinkedIn invites to people via Circulus")
        st.write("2. Export/save the list of people you invited as CSV")
        st.write("3. Upload the CSV file")
        st.write("4. Select your client name and campaign category")
        st.write("5. Click 'Log Invites to Database'")
        st.write("6. Your team gets notified on Slack")
    
    
    # Show current configuration
    with st.expander("🔧 Current Configuration"):
        st.text(f"Database: {database} on {server}")
        st.text(f"Username: {username}")
        st.text(f"Slack Channel: {target_channel_id}")
    
    # Test connections
    st.subheader("Connection Tests")
    col1, col2 = st.columns(2)
    
    with col1:
        st.write("**Database Connection:**")
        db_connected = test_database_connection()
    
    with col2:
        st.write("**Slack Connection:**")
        slack_connected = test_slack_connection()
    
    if not db_connected:
        st.error("❌ Cannot proceed without database connection.")
        st.info("💡 Install pymssql: pip install pymssql")
        return
    
    # Get existing data for dropdowns
    with st.spinner("Loading existing data from database..."):
        invited_profiles = get_invited_profiles()
    
    if not invited_profiles.empty:
        st.info(f"📊 Database contains {len(invited_profiles):,} total records from {invited_profiles['ClientName'].nunique()} clients")
        
        # Show recent activity
        with st.expander("📈 Recent Database Activity"):
            recent_summary = invited_profiles.groupby(['ClientName', 'Category', 'DateCollected']).size().reset_index(name='Count')
            recent_summary = recent_summary.sort_values('DateCollected', ascending=False).head(10)
            st.dataframe(recent_summary, use_container_width=True)
        
        # Client selection
        existing_clients = sorted(invited_profiles['ClientName'].dropna().unique())
        client_options = existing_clients + ["➕ Enter Custom Name"]
        selected_client = st.selectbox("🏢 Select client name", client_options)
        
        if selected_client == "➕ Enter Custom Name":
            selected_client_name = st.text_input("Enter Custom Client Name", value="LOCAL TEST CLIENT MAC")
        else:
            selected_client_name = selected_client
        
        # Category selection based on selected client
        if selected_client_name and selected_client_name in existing_clients:
            client_categories = sorted(invited_profiles[
                invited_profiles['ClientName'] == selected_client_name
            ]['Category'].dropna().unique())
            category_options = client_categories + ["➕ Enter Custom Category"]
        else:
            category_options = ["➕ Enter Custom Category"]
        
        selected_category = st.selectbox("📂 Select category", category_options)
        
        if selected_category == "➕ Enter Custom Category":
            selected_category_name = st.text_input("Enter Custom Category", value="LOCAL TEST CATEGORY MAC")
        else:
            selected_category_name = selected_category
    else:
        st.info("📊 No existing data found. Starting fresh!")
        selected_client_name = st.text_input("🏢 Client Name", value="LOCAL TEST CLIENT MAC")
        selected_category_name = st.text_input("📂 Category", value="LOCAL TEST CATEGORY MAC")
    
    # Date and URL inputs
    col1, col2 = st.columns(2)
    with col1:
        DateInvited = st.date_input("📅 Date Invites Sent", datetime.date.today())
    with col2:
        growth_list_url = st.text_input("🔗 Growth List URL", value="https://example.com/mac-local-test-list")
    
    DateInvited_str = DateInvited.strftime('%Y-%m-%d')
    
    # File upload section
    st.subheader("📄 Upload Invite Data")
    st.write("Upload a CSV file containing only the people you **actually sent invites to**")
    
    # Sample CSV download
    sample_data = pd.DataFrame({
        'Full name': ['John Test Mac', 'Jane Sample Mac', 'Mike Demo Mac'],
        'Profile url': ['https://linkedin.com/in/johntestmac', 'https://linkedin.com/in/janesamplemac', 'https://linkedin.com/in/mikedemomac'],
        'Title': ['CEO', 'CTO', 'VP Sales'],
        'Location': ['New York', 'California', 'Texas'],
        'Organization 1': ['Test Corp', 'Sample Inc', 'Demo LLC'],
        'Followers': [1500, 2300, 1800]
    })
    
    sample_csv = sample_data.to_csv(index=False)
    st.download_button(
        label="📥 Download Sample CSV for Testing",
        data=sample_csv,
        file_name="mac_local_test_invites.csv",
        mime="text/csv"
    )
    
    uploaded_file = st.file_uploader(
        "Choose CSV file", 
        type="csv",
        help="Required: 'Full name', 'Profile url'. Optional: 'Title', 'Location', 'Organization 1', 'Followers'"
    )
    
    if uploaded_file is not None:
        try:
            df = pd.read_csv(uploaded_file, encoding='utf-8')
            
            # Validate required columns
            required_cols = ['Full name', 'Profile url']
            missing_cols = [col for col in required_cols if col not in df.columns]
            
            if missing_cols:
                st.error(f"❌ Missing required columns: {', '.join(missing_cols)}")
                st.info("Required columns: 'Full name', 'Profile url'")
                st.info("Available columns in your file:")
                st.code(", ".join(df.columns.tolist()))
                return
            
            # Show CSV info
            st.success(f"✅ CSV loaded successfully!")
            
            col1, col2, col3 = st.columns(3)
            with col1:
                st.metric("📊 Total Rows", len(df))
            with col2:
                st.metric("📋 Columns", len(df.columns))
            with col3:
                non_empty_names = df['Full name'].dropna().nunique()
                st.metric("👥 Unique Names", non_empty_names)
            
            # Show preview
            st.subheader("👀 Data Preview")
            st.dataframe(df, use_container_width=True)
            
            # Show column info
            with st.expander("📊 Column Information"):
                for col in df.columns:
                    non_null_count = df[col].notna().sum()
                    st.text(f"• {col}: {non_null_count}/{len(df)} non-empty values")
            
            # Data quality check
            warnings = []
            if df['Full name'].isna().sum() > 0:
                warnings.append(f"⚠️ {df['Full name'].isna().sum()} rows missing 'Full name'")
            if df['Profile url'].isna().sum() > 0:
                warnings.append(f"⚠️ {df['Profile url'].isna().sum()} rows missing 'Profile url'")
            
            if warnings:
                st.warning("Data quality issues (will be skipped):")
                for warning in warnings:
                    st.text(warning)
            
            # Submit section
            st.subheader("🚀 Submit to Database")
            
            # Final validation
            can_submit = True
            submit_messages = []
            
            if not selected_client_name:
                can_submit = False
                submit_messages.append("❌ Client name required")
            else:
                submit_messages.append(f"✅ Client: {selected_client_name}")
                
            if not selected_category_name:
                can_submit = False
                submit_messages.append("❌ Category required")
            else:
                submit_messages.append(f"✅ Category: {selected_category_name}")
                
            submit_messages.append(f"✅ Date: {DateInvited_str}")
            submit_messages.append(f"✅ Records to process: {len(df)}")
            submit_messages.append(f"✅ Database: {'Connected' if db_connected else 'Disconnected'}")
            submit_messages.append(f"✅ Slack: {'Connected' if slack_connected else 'Disabled'}")
            
            for msg in submit_messages:
                st.text(msg)
            
            # Submit button
            if can_submit:
                if st.button("🚀 Log Invites to Database", type="primary", use_container_width=True):
                    with st.spinner("Inserting data into database..."):
                        insert_to_database(
                            df, 
                            selected_client_name, 
                            selected_category_name, 
                            DateInvited_str, 
                            growth_list_url
                        )
            else:
                st.error("Please fix the issues above before submitting.")
                
        except Exception as e:
            st.error(f"❌ File processing error: {str(e)}")
            st.info("Make sure your file is a valid CSV with UTF-8 encoding.")
            
            with st.expander("🔍 Detailed File Error"):
                st.text(f"Error type: {type(e).__name__}")
                st.text(f"Error message: {str(e)}")

if __name__ == "__main__":
    app()

import streamlit as st
import pandas as pd
import requests
from datetime import datetime
import re
import os
import time
from streamlit_autorefresh import st_autorefresh

# Page configuration
st.set_page_config(
    page_title="Money & Monetary Policy Rank Tracker",
    page_icon="📊",
    layout="wide"
)

# ---------------------------- Top nav (your template) -----------------
cols = st.columns(11)
with cols[0]:
    st.page_link("streamlit_app.py", label="🏠 Home")
with cols[1]:
    st.page_link("pages/01_Reserves.py", label="🌍 Reserves")
with cols[2]:
    st.page_link("pages/01_FDIC.py", label="🏦 FDIC")
with cols[3]:
    st.page_link("pages/01_Repo.py", label="🔄 Repo")
with cols[4]:
    st.page_link("pages/01_Repo2.py", label="♻️ Repo 2")
with cols[5]:
    st.page_link("pages/01_TGA.py", label="🏛️ TGA")
with cols[6]:
    st.page_link("pages/01_PublicBalance.py", label="📊 P.Balance")
with cols[7]:
    st.page_link("pages/01_Interest.py", label="📈 Rates")
with cols[8]:
    st.page_link("pages/01_Desk.py", label="🛰️ Desk")
with cols[9]:
    st.page_link("pages/01_Yield.py", label="🌍 Yield")
with cols[10]:
    st.page_link("pages/01_Eurodollar.py", label="💡 Eurodollar")

# ---------------------------- STOP Expanded -----------------
st.markdown(
    """
<style>
    [data-testid="stSidebarNav"] {display: none;}
    section[data-testid="stSidebar"][aria-expanded="true"]{display: none;}
</style>
""",
    unsafe_allow_html=True,
)
# ---------------------------- CODE -----------------



# Book information
ASIN = "B0G584KJ73"
URL = f"https://www.amazon.com/dp/{ASIN}"
CATEGORY = "Money & Monetary Policy (Books)"
CSV_FILE = "rank_tracking.csv"

# Auto-refresh every 60 minutes (3600000 milliseconds)
count = st_autorefresh(interval=60 * 60 * 1000, key="hourly_refresh")

def fetch_book_rank():
    """Fetches the Money & Monetary Policy rank from Amazon page"""
    
    headers = {
        'User-Agent': 'Mozilla/5.0 (Windows NT 10.0; Win64; x64) AppleWebKit/537.36 (KHTML, like Gecko) Chrome/120.0.0.0 Safari/537.36',
        'Accept-Language': 'en-US,en;q=0.9',
        'Accept-Encoding': 'gzip, deflate, br',
        'Accept': 'text/html,application/xhtml+xml,application/xml;q=0.9,image/webp,*/*;q=0.8',
        'Connection': 'keep-alive',
        'Upgrade-Insecure-Requests': '1'
    }
    
    try:
        st.info(f"Fetching data from Amazon... ({datetime.now().strftime('%Y-%m-%d %H:%M:%S')})")
        
        # Fetch the page
        response = requests.get(URL, headers=headers, timeout=30)
        html_text = response.text
        
        # Find Money & Monetary Policy rank
        category_rank = None
        full_text = ""
        
        # Pattern: Rank inside Money & Monetary Policy link
        # Example: #86 in <a href='/gp/bestsellers/books/2598/ref=pd_zg_hrsr_books'>Money & Monetary Policy
        pattern = r'#(\d{1,3}(?:,\d{3})*)\s+in\s+<a[^>]*>' + re.escape("Money & Monetary Policy")
        match = re.search(pattern, html_text, re.IGNORECASE)
        
        if match:
            category_rank = match.group(1).replace(',', '')
            full_text = f"#{category_rank} in Money & Monetary Policy (Books)"
            st.success(f"✓ Money & Monetary Policy rank found: #{category_rank}")
        else:
            # Alternative pattern: More general
            pattern2 = r'#(\d{1,3}(?:,\d{3})*)\s+in\s+<a[^>]*>Money\s*&\s*Monetary\s*Policy'
            match2 = re.search(pattern2, html_text, re.IGNORECASE)
            
            if match2:
                category_rank = match2.group(1).replace(',', '')
                full_text = f"#{category_rank} in Money & Monetary Policy (Books)"
                st.success(f"✓ Found with alternative pattern: #{category_rank}")
        
        if category_rank:
            # Clean rank value
            if '.' in str(category_rank):
                category_rank = str(category_rank).split('.')[0]
            
            return {
                'timestamp': datetime.now().strftime('%Y-%m-%d %H:%M:%S'),
                'datetime': datetime.now().strftime('%Y%m%d_%H%M%S'),
                'asin': ASIN,
                'category_rank': category_rank,
                'full_rank_text': full_text,
                'category': "Money & Monetary Policy",
                'url': URL,
                'status': 'SUCCESS'
            }
        else:
            st.warning("⚠️ Money & Monetary Policy rank not found")
            
            # Debug: Show lines containing Money & Monetary Policy
            with st.expander("🔍 Debug - Lines containing Money & Monetary Policy"):
                lines = html_text.split('\n')
                cat_lines = [line.strip() for line in lines if "Money & Monetary Policy" in line]
                for i, line in enumerate(cat_lines[:10]):
                    st.code(f"{i+1}: {line}")
            
            return None
            
    except Exception as e:
        st.error(f"❌ Error occurred: {str(e)}")
        return None

def save_to_csv(data):
    """Saves data to CSV file"""
    file_exists = os.path.isfile(CSV_FILE)
    
    # Create DataFrame
    if data:
        df_new = pd.DataFrame([data])
    else:
        df_new = pd.DataFrame([{
            'timestamp': datetime.now().strftime('%Y-%m-%d %H:%M:%S'),
            'datetime': datetime.now().strftime('%Y%m%d_%H%M%S'),
            'asin': ASIN,
            'category_rank': '',
            'full_rank_text': 'DATA_NOT_FOUND',
            'category': "Money & Monetary Policy",
            'url': URL,
            'status': 'FAILED'
        }])
    
    # Append to CSV or create new
    if file_exists:
        df_existing = pd.read_csv(CSV_FILE)
        df_combined = pd.concat([df_existing, df_new], ignore_index=True)
    else:
        df_combined = df_new
    
    df_combined.to_csv(CSV_FILE, index=False)
    return df_combined

def format_rank(rank_value):
    """Formats rank value"""
    if pd.notna(rank_value) and rank_value:
        try:
            # Clean decimal numbers
            if '.' in str(rank_value):
                rank_int = int(float(str(rank_value)))
            else:
                rank_int = int(str(rank_value).replace(',', ''))
            return f"#{rank_int:,}"
        except:
            return str(rank_value)
    return '-'

def auto_fetch():
    """Automatically fetches data and saves to CSV"""
    data = fetch_book_rank()
    df = save_to_csv(data)
    if data:
        st.session_state['last_auto_fetch'] = datetime.now()
        st.session_state['auto_fetch_status'] = f"✅ Auto-fetch successful: #{data['category_rank']}"
    else:
        st.session_state['auto_fetch_status'] = "❌ Auto-fetch failed"
    return df

def main():
    # Initialize session state
    if 'last_auto_fetch' not in st.session_state:
        st.session_state['last_auto_fetch'] = None
    if 'auto_fetch_status' not in st.session_state:
        st.session_state['auto_fetch_status'] = ""
    
    st.title("💰 Money & Monetary Policy Rank Tracker")
    st.markdown("---")
    
    # Auto-refresh info
    col_info1, col_info2 = st.columns(2)
    with col_info1:
        st.info(f"🔄 Auto-fetch every hour | Refresh count: {count}")
    with col_info2:
        if st.session_state['last_auto_fetch']:
            st.success(f"Last auto-fetch: {st.session_state['last_auto_fetch'].strftime('%Y-%m-%d %H:%M:%S')}")
        if st.session_state['auto_fetch_status']:
            st.caption(st.session_state['auto_fetch_status'])
    
    # Perform auto-fetch on refresh
    if count > 0 and count % 60 == 0:  # This runs on every auto-refresh (hourly)
        auto_fetch()
    
    # Sidebar
    with st.sidebar:
        st.header("📌 Book Information")
        st.info(f"**ASIN:** {ASIN}")
        st.info(f"**Category:** Money & Monetary Policy")
        st.info(f"**CSV File:** {CSV_FILE}")
        
        st.markdown("---")
        if st.button("🔄 Manual Check", type="primary"):
            with st.spinner("Fetching data..."):
                data = fetch_book_rank()
                df = save_to_csv(data)
                if data:
                    st.success(f"✓ Data saved!")
                    st.info(f"🏷️ Rank: #{data['category_rank']}")
                else:
                    st.error("✗ Failed to fetch data")
                st.rerun()
    
    # Main content
    col1, col2 = st.columns(2)
    
    with col1:
        st.subheader("📈 Latest Rank Information")
        if os.path.isfile(CSV_FILE):
            df = pd.read_csv(CSV_FILE)
            if not df.empty:
                latest_record = df.iloc[-1]
                if latest_record['status'] == 'SUCCESS':
                    if pd.notna(latest_record['category_rank']) and latest_record['category_rank']:
                        st.metric(
                            label="🏷️ Money & Monetary Policy", 
                            value=format_rank(latest_record['category_rank'])
                        )
                    
                    st.caption(f"Last update: {latest_record['timestamp']}")
                    
                    if pd.notna(latest_record['full_rank_text']) and latest_record['full_rank_text']:
                        st.info(f"**Full text:** {latest_record['full_rank_text']}")
                else:
                    st.warning("⚠️ Last check failed")
            else:
                st.info("📭 No data yet")
    
    with col2:
        st.subheader("📊 Rank Chart")
        if os.path.isfile(CSV_FILE):
            df = pd.read_csv(CSV_FILE)
            if len(df) > 1 and df['category_rank'].notna().any():
                df_plot = df[df['category_rank'].notna()].copy()
                
                def clean_rank(x):
                    if pd.notna(x) and x:
                        try:
                            if '.' in str(x):
                                return int(float(str(x)))
                            return int(str(x).replace(',', ''))
                        except:
                            return None
                    return None
                
                df_plot['category_rank_num'] = df_plot['category_rank'].apply(clean_rank)
                df_plot['timestamp_dt'] = pd.to_datetime(df_plot['timestamp'])
                
                if not df_plot.empty and df_plot['category_rank_num'].notna().any():
                    fig_data = df_plot[['timestamp_dt', 'category_rank_num']].dropna()
                    if not fig_data.empty:
                        st.line_chart(
                            fig_data.set_index('timestamp_dt'),
                            color='#ff4b4b'
                        )
                        
                        latest_rank = fig_data['category_rank_num'].iloc[-1]
                        st.caption(f"Latest rank: #{latest_rank:,}")
                        
                        min_rank = fig_data['category_rank_num'].min()
                        max_rank = fig_data['category_rank_num'].max()
                        st.caption(f"Min: #{min_rank:,} | Max: #{max_rank:,}")
                else:
                    st.info("📭 Not enough data for chart")
            else:
                st.info("📭 Not enough data for chart")
    
    # Table
    st.markdown("---")
    st.subheader("📋 Last 20 Records")
    if os.path.isfile(CSV_FILE):
        df = pd.read_csv(CSV_FILE)
        if not df.empty:
            df_display = df.tail(20).copy()
            df_display['category_rank_display'] = df_display['category_rank'].apply(format_rank)
            
            display_cols = ['timestamp', 'category_rank_display', 'status']
            df_display = df_display[display_cols]
            df_display.columns = ['Date', 'Money & Monetary Policy Rank', 'Status']
            
            st.dataframe(df_display, use_container_width=True)
            
            # Statistics
            st.markdown("---")
            st.subheader("📊 Statistics")
            col3, col4, col5 = st.columns(3)
            
            successful = df[df['status'] == 'SUCCESS'].shape[0]
            failed = df[df['status'] == 'FAILED'].shape[0]
            
            with col3:
                st.metric("Total Checks", len(df))
            with col4:
                st.metric("Successful", successful)
            with col5:
                st.metric("Failed", failed)
            
            # Average rank
            successful_df = df[df['status'] == 'SUCCESS']
            if not successful_df.empty and successful_df['category_rank'].notna().any():
                ranks = []
                for r in successful_df['category_rank'].dropna():
                    try:
                        if '.' in str(r):
                            ranks.append(int(float(str(r))))
                        else:
                            ranks.append(int(str(r).replace(',', '')))
                    except:
                        pass
                if ranks:
                    avg_rank = sum(ranks) / len(ranks)
                    st.metric("Average Rank", f"#{int(avg_rank):,}")
            
            # CSV download button
            csv_data = df.to_csv(index=False)
            st.download_button(
                label="📥 Download CSV",
                data=csv_data,
                file_name=f"money_policy_rank_{datetime.now().strftime('%Y%m%d')}.csv",
                mime="text/csv"
            )
        else:
            st.info("📭 No records yet")
    else:
        st.info("📭 CSV file not created yet. Click 'Manual Check' to create the first record.")
    
    # File information section
    st.markdown("---")
    st.subheader("📁 File Information")

    if os.path.isfile(CSV_FILE):
        df = pd.read_csv(CSV_FILE)
        
        col1, col2, col3 = st.columns(3)
        with col1:
            st.metric("Total Records", len(df))
        with col2:
            st.metric("File Size", f"{os.path.getsize(CSV_FILE)/1024:.1f} KB")
        with col3:
            st.metric("Last Update", datetime.fromtimestamp(os.path.getmtime(CSV_FILE)).strftime('%Y-%m-%d %H:%M'))
        
        # Show file path
        st.code(f"📂 {os.path.abspath(CSV_FILE)}")
        
        # Download button
        with open(CSV_FILE, "rb") as f:
            st.download_button(
                label="📥 Download CSV File",
                data=f,
                file_name=f"rank_tracking_{datetime.now().strftime('%Y%m%d_%H%M')}.csv",
                mime="text/csv"
            )
        
        # Show last 10 records
        with st.expander("📋 Last 10 Records"):
            st.dataframe(df.tail(10))
    else:
        st.warning("⚠️ CSV file not created yet. Click 'Manual Check' to create the first record.")

if __name__ == "__main__":
    main()
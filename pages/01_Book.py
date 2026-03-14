import streamlit as st
st.set_page_config(page_title="Money & Monetary Policy Rank Tracker", layout="wide")

import pandas as pd
import requests
from datetime import datetime
import re
import os
import base64
from streamlit_autorefresh import st_autorefresh

# Book information
ASIN = "B0G584KJ73"
URL = f"https://www.amazon.com/dp/{ASIN}"
CATEGORY = "Money & Monetary Policy (Books)"
CSV_FILE = "rank_tracking.csv"

# Required columns
REQUIRED_COLUMNS = ['timestamp', 'datetime', 'asin', 'category_rank', 'full_rank_text', 'category', 'url', 'status']

def get_csv_download_link(df, filename="rank_tracking.csv"):
    """CSV indirme linki oluşturur"""
    csv = df.to_csv(index=False)
    b64 = base64.b64encode(csv.encode()).decode()
    href = f'<a href="data:file/csv;base64,{b64}" download="{filename}">📥 CSV Dosyasını İndir</a>'
    return href

def show_csv_content():
    """CSV içeriğini gösterir ve indirme linki verir"""
    st.subheader("📁 CSV Dosyası")
    
    if os.path.isfile(CSV_FILE):
        try:
            df = pd.read_csv(CSV_FILE)
            st.dataframe(df)
            
            # Dosya bilgileri
            col1, col2, col3 = st.columns(3)
            with col1:
                st.metric("Kayıt Sayısı", len(df))
            with col2:
                st.metric("Dosya Boyutu", f"{os.path.getsize(CSV_FILE)/1024:.2f} KB")
            with col3:
                st.metric("Son Güncelleme", datetime.fromtimestamp(os.path.getmtime(CSV_FILE)).strftime('%H:%M:%S'))
            
            # İndirme linki
            st.markdown(get_csv_download_link(df), unsafe_allow_html=True)
            
            # Dosya yolunu göster (Streamlit Cloud'da geçici bir yoldur)
            st.caption(f"📂 Sunucu yolu: {os.path.abspath(CSV_FILE)}")
            st.caption("⚠️ Bu dosya Streamlit Cloud sunucusunda. Yerel bilgisayarınıza indirmek için yukarıdaki linki kullanın.")
            
        except Exception as e:
            st.error(f"CSV okuma hatası: {e}")
    else:
        st.warning("CSV dosyası bulunamadı!")

def fix_csv_columns():
    """CSV dosyasına sütunları ekler"""
    try:
        if os.path.isfile(CSV_FILE):
            df = pd.read_csv(CSV_FILE)
            current_columns = list(df.columns)
            
            if current_columns != REQUIRED_COLUMNS:
                st.warning("🔄 Sütunlar düzeltiliyor...")
                new_df = pd.DataFrame(columns=REQUIRED_COLUMNS)
                
                if len(df) > 0:
                    for col in REQUIRED_COLUMNS:
                        if col in current_columns:
                            new_df[col] = df[col]
                        else:
                            new_df[col] = ""
                
                new_df.to_csv(CSV_FILE, index=False)
                return True, f"✅ Sütunlar düzeltildi! {len(new_df)} kayıt korundu."
            else:
                return True, "✅ Sütunlar zaten doğru."
        else:
            df = pd.DataFrame(columns=REQUIRED_COLUMNS)
            df.to_csv(CSV_FILE, index=False)
            return True, f"✅ Yeni CSV oluşturuldu!"
    except Exception as e:
        df = pd.DataFrame(columns=REQUIRED_COLUMNS)
        df.to_csv(CSV_FILE, index=False)
        return True, f"✅ CSV sıfırlandı!"

# Auto-refresh
count = st_autorefresh(interval=60 * 60 * 1000, key="hourly_refresh")

def fetch_book_rank():
    """Fetches the Money & Monetary Policy rank from Amazon page"""
    headers = {
        'User-Agent': 'Mozilla/5.0 (Windows NT 10.0; Win64; x64) AppleWebKit/537.36 (KHTML, like Gecko) Chrome/120.0.0.0 Safari/537.36',
    }
    
    try:
        response = requests.get(URL, headers=headers, timeout=30)
        html_text = response.text
        
        # Find Money & Monetary Policy rank
        pattern = r'#(\d{1,3}(?:,\d{3})*)\s+in\s+<a[^>]*>' + re.escape("Money & Monetary Policy")
        match = re.search(pattern, html_text, re.IGNORECASE)
        
        if match:
            category_rank = match.group(1).replace(',', '')
            full_text = f"#{category_rank} in Money & Monetary Policy (Books)"
            
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
        return None
    except Exception as e:
        st.error(f"Error: {e}")
        return None

def save_to_csv(data):
    """Saves data to CSV file"""
    try:
        if not os.path.isfile(CSV_FILE):
            fix_csv_columns()
        
        df_existing = pd.read_csv(CSV_FILE)
        
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
        
        df_combined = pd.concat([df_existing, df_new], ignore_index=True)
        df_combined.to_csv(CSV_FILE, index=False)
        return df_combined
    except Exception as e:
        st.error(f"CSV kaydedilirken hata: {e}")
        return None

def main():
    st.title("💰 Money & Monetary Policy Rank Tracker")
    st.markdown("---")
    
    # CSV İŞLEMLERİ - En üstte
    with st.expander("📁 CSV Dosya İşlemleri", expanded=True):
        col1, col2, col3 = st.columns(3)
        
        with col1:
            if st.button("🛠️ CSV Sütunlarını Düzelt", use_container_width=True):
                with st.spinner("Düzeltiliyor..."):
                    success, message = fix_csv_columns()
                    st.success(message)
                    st.rerun()
        
        with col2:
            if st.button("📥 CSV'yi İndir", use_container_width=True):
                if os.path.isfile(CSV_FILE):
                    df = pd.read_csv(CSV_FILE)
                    csv = df.to_csv(index=False)
                    b64 = base64.b64encode(csv.encode()).decode()
                    href = f'<a href="data:file/csv;base64,{b64}" download="rank_tracking.csv">Tıklayın</a>'
                    st.markdown(f"İndirme linki: {href}", unsafe_allow_html=True)
                else:
                    st.warning("CSV yok")
        
        with col3:
            if st.button("👁️ CSV İçeriğini Göster", use_container_width=True):
                st.session_state['show_csv'] = not st.session_state.get('show_csv', False)
        
        # CSV içeriğini göster
        if st.session_state.get('show_csv', False):
            show_csv_content()
    
    st.markdown("---")
    
    # Auto-refresh info
    st.info(f"🔄 Auto-fetch every hour | Refresh count: {count}")
    
    # Perform auto-fetch
    if count > 0 and count % 60 == 0:
        data = fetch_book_rank()
        if data:
            save_to_csv(data)
            st.success(f"Auto-fetch: #{data['category_rank']}")
    
    # Sidebar
    with st.sidebar:
        st.header("📌 Book Info")
        st.info(f"ASIN: {ASIN}")
        
        if st.button("🔄 Manual Check", type="primary"):
            with st.spinner("Fetching..."):
                fix_csv_columns()
                data = fetch_book_rank()
                if data:
                    save_to_csv(data)
                    st.success(f"Rank: #{data['category_rank']}")
                else:
                    st.error("Failed")
                st.rerun()
    
    # Ana içerik
    if os.path.isfile(CSV_FILE):
        df = pd.read_csv(CSV_FILE)
        
        if not df.empty:
            # Son rank
            latest = df.iloc[-1]
            if latest['status'] == 'SUCCESS':
                st.metric("Current Rank", f"#{latest['category_rank']}")
                st.caption(f"Last update: {latest['timestamp']}")
            
            # Chart
            if len(df) > 1:
                df_plot = df[df['category_rank'].notna()].copy()
                df_plot['rank_num'] = pd.to_numeric(df_plot['category_rank'], errors='coerce')
                df_plot['timestamp'] = pd.to_datetime(df_plot['timestamp'])
                st.line_chart(df_plot.set_index('timestamp')['rank_num'])
            
            # Table
            st.subheader("📋 Last 10 Records")
            st.dataframe(df[['timestamp', 'category_rank', 'status']].tail(10))
            
            # Stats
            successful = df[df['status'] == 'SUCCESS'].shape[0]
            st.metric("Total Checks", len(df))
            st.metric("Successful", successful)
        else:
            st.info("No data yet")
    else:
        st.warning("CSV not found. Click 'Fix CSV Columns' to create it.")

if __name__ == "__main__":
    main()
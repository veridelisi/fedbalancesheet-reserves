import streamlit as st
st.set_page_config(page_title="Money & Monetary Policy Rank Tracker", layout="wide")

import pandas as pd
import requests
from datetime import datetime
import re
import base64
from github import Github
from github import GithubException
from streamlit_autorefresh import st_autorefresh
import time

# ========== KONFİGÜRASYON ==========
ASIN = "B0G584KJ73"
URL = f"https://www.amazon.com/dp/{ASIN}"
CATEGORY = "Money & Monetary Policy (Books)"
REQUIRED_COLUMNS = ['timestamp', 'datetime', 'asin', 'category_rank', 'full_rank_text', 'category', 'url', 'status']

# GitHub bilgileri (Streamlit Cloud Secrets'tan alınacak)
GITHUB_TOKEN = st.secrets["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"]
REPO_NAME = "veridelisi/fedbalancesheet-reserves"
BRANCH = "main"
CSV_PATH_IN_REPO = "pages/rank_tracking.csv"

# Auto-refresh every 60 minutes (3600000 milliseconds)
count = st_autorefresh(interval=60 * 60 * 1000, key="hourly_refresh")

# ========== GITHUB İŞLEMLERİ ==========
@st.cache_data(ttl=60)
def read_csv_from_github():
    """GitHub'dan CSV'yi okur ve DataFrame olarak döndürür"""
    try:
        g = Github(GITHUB_TOKEN)
        repo = g.get_repo(REPO_NAME)
        
        try:
            contents = repo.get_contents(CSV_PATH_IN_REPO, ref=BRANCH)
            csv_content = base64.b64decode(contents.content).decode('utf-8')
            
            from io import StringIO
            df = pd.read_csv(StringIO(csv_content))
            
            if list(df.columns) != REQUIRED_COLUMNS:
                new_df = pd.DataFrame(columns=REQUIRED_COLUMNS)
                for col in REQUIRED_COLUMNS:
                    if col in df.columns:
                        new_df[col] = df[col]
                df = new_df
            
            return df, contents.sha
            
        except GithubException as e:
            if e.status == 404:
                df = pd.DataFrame(columns=REQUIRED_COLUMNS)
                return df, None
            else:
                st.error(f"GitHub hatası: {e}")
                return pd.DataFrame(columns=REQUIRED_COLUMNS), None
                
    except Exception as e:
        st.error(f"GitHub bağlantı hatası: {e}")
        return pd.DataFrame(columns=REQUIRED_COLUMNS), None

def write_csv_to_github(df, current_sha=None):
    """DataFrame'i GitHub'daki CSV'ye yazar"""
    try:
        g = Github(GITHUB_TOKEN)
        repo = g.get_repo(REPO_NAME)
        
        csv_string = df.to_csv(index=False)
        commit_message = f"📊 Rank güncellemesi {datetime.now().strftime('%Y-%m-%d %H:%M')}"
        
        if current_sha:
            repo.update_file(CSV_PATH_IN_REPO, commit_message, csv_string, current_sha, branch=BRANCH)
        else:
            repo.create_file(CSV_PATH_IN_REPO, commit_message, csv_string, branch=BRANCH)
        
        return True
        
    except Exception as e:
        st.error(f"GitHub'a yazma hatası: {e}")
        return False

# ========== AMAZON RANK ÇEKME ==========
def fetch_book_rank():
    """Amazon sayfasından Money & Monetary Policy rankını çeker"""
    
    headers = {
        'User-Agent': 'Mozilla/5.0 (Windows NT 10.0; Win64; x64) AppleWebKit/537.36 (KHTML, like Gecko) Chrome/120.0.0.0 Safari/537.36',
        'Accept-Language': 'en-US,en;q=0.9',
    }
    
    try:
        response = requests.get(URL, headers=headers, timeout=30)
        html_text = response.text
        
        category_rank = None
        
        pattern = r'#(\d{1,3}(?:,\d{3})*)\s+in\s+<a[^>]*>' + re.escape("Money & Monetary Policy")
        match = re.search(pattern, html_text, re.IGNORECASE)
        
        if match:
            category_rank = match.group(1).replace(',', '')
        
        if not category_rank:
            pattern2 = r'#(\d{1,3}(?:,\d{3})*)\s+in\s+Money\s*&\s*Monetary\s*Policy'
            match2 = re.search(pattern2, html_text, re.IGNORECASE)
            if match2:
                category_rank = match2.group(1).replace(',', '')
        
        if category_rank:
            if '.' in str(category_rank):
                category_rank = str(category_rank).split('.')[0]
            
            return {
                'timestamp': datetime.now().strftime('%Y-%m-%d %H:%M:%S'),
                'datetime': datetime.now().strftime('%Y%m%d_%H%M%S'),
                'asin': ASIN,
                'category_rank': str(category_rank),
                'full_rank_text': f"#{category_rank} in Money & Monetary Policy (Books)",
                'category': "Money & Monetary Policy",
                'url': URL,
                'status': 'SUCCESS'
            }
        else:
            return None
            
    except Exception as e:
        st.error(f"Amazon bağlantı hatası: {e}")
        return None

# ========== VERİ KAYDETME ==========
def save_rank_to_github():
    """Rank verisini çeker ve GitHub'daki CSV'ye kaydeder"""
    
    df, sha = read_csv_from_github()
    data = fetch_book_rank()
    
    if data:
        new_row = pd.DataFrame([data])
        df = pd.concat([df, new_row], ignore_index=True)
        
        if len(df) > 1000:
            df = df.tail(1000)
        
        success = write_csv_to_github(df, sha)
        
        if success:
            return True, data
        else:
            return False, None
    else:
        failed_data = {
            'timestamp': datetime.now().strftime('%Y-%m-%d %H:%M:%S'),
            'datetime': datetime.now().strftime('%Y%m%d_%H%M%S'),
            'asin': ASIN,
            'category_rank': '',
            'full_rank_text': 'VERI_BULUNAMADI',
            'category': "Money & Monetary Policy",
            'url': URL,
            'status': 'FAILED'
        }
        new_row = pd.DataFrame([failed_data])
        df = pd.concat([df, new_row], ignore_index=True)
        
        success = write_csv_to_github(df, sha)
        return False, None

# ========== ANA UYGULAMA ==========
def main():
    st.title("💰 Money & Monetary Policy Rank Tracker")
    st.markdown("---")
    
    # GitHub token kontrolü
    if 'GITHUB_TOKEN' not in st.secrets:
        st.error("❌ GitHub token'ı bulunamadı! Lütfen Streamlit Cloud Secrets'a ekleyin.")
        return
    
    # Session state başlangıcı
    if 'last_update' not in st.session_state:
        st.session_state.last_update = None
    if 'last_rank' not in st.session_state:
        st.session_state.last_rank = "Veri yok"
    if 'auto_run' not in st.session_state:
        st.session_state.auto_run = False
    if 'show_csv' not in st.session_state:
        st.session_state.show_csv = False
    
    # Üst bilgiler
    col1, col2, col3 = st.columns(3)
    
    with col1:
        st.info(f"🔄 Otomatik: Saat başı")
        st.caption(f"Sayaç: {count}")
    
    with col2:
        df, _ = read_csv_from_github()
        if not df.empty and df['status'].iloc[-1] == 'SUCCESS':
            son_rank = df['category_rank'].iloc[-1]
            son_zaman = df['timestamp'].iloc[-1]
            st.metric("Son Rank", f"#{son_rank}")
            st.caption(f"🕐 {son_zaman}")
        else:
            st.metric("Son Rank", "Veri yok")
    
    with col3:
        if df is not None and not df.empty:
            st.metric("Toplam Kayıt", len(df))
    
    # Butonlar
    col_btn1, col_btn2, col_btn3 = st.columns(3)
    
    with col_btn1:
        if st.button("🔄 Şimdi Kontrol Et ve Kaydet", type="primary", use_container_width=True):
            with st.spinner("Amazon kontrol ediliyor..."):
                success, data = save_rank_to_github()
                if success and data:
                    st.success(f"✅ Rank #{data['category_rank']} kaydedildi!")
                    st.balloons()
                else:
                    st.error("❌ Veri çekilemedi")
                time.sleep(2)
                st.rerun()
    
    with col_btn2:
        if st.button("📥 GitHub'dan CSV'yi Göster", use_container_width=True):
            st.session_state.show_csv = not st.session_state.show_csv
            st.rerun()
    
    with col_btn3:
        github_url = f"https://github.com/{REPO_NAME}/blob/{BRANCH}/{CSV_PATH_IN_REPO}"
        st.markdown(f"[🔗 GitHub'da Aç]({github_url})")
    
    # Otomatik saatlik kontrol
    if count > 0 and count % 60 == 0 and not st.session_state.auto_run:
        st.session_state.auto_run = True
        with st.spinner("⏰ Otomatik kontrol yapılıyor..."):
            success, data = save_rank_to_github()
            if success:
                st.success(f"✅ Otomatik güncelleme: #{data['category_rank']}")
            else:
                st.warning("⚠️ Otomatik güncelleme başarısız")
        st.session_state.auto_run = False
        st.rerun()
    
    # CSV içeriği göster
    if st.session_state.show_csv:
        st.markdown("---")
        st.subheader("📋 GitHub'daki CSV İçeriği")
        
        df, _ = read_csv_from_github()
        
        if not df.empty:
            # İstatistikler
            col_s1, col_s2, col_s3 = st.columns(3)
            with col_s1:
                success_count = df[df['status'] == 'SUCCESS'].shape[0]
                st.metric("✅ Başarılı", success_count)
            with col_s2:
                fail_count = df[df['status'] == 'FAILED'].shape[0]
                st.metric("❌ Başarısız", fail_count)
            with col_s3:
                success_rate = (success_count/len(df)*100) if len(df) > 0 else 0
                st.metric("📊 Başarı Oranı", f"{success_rate:.1f}%")
            
            # Grafik
            if len(df) > 1:
                df_plot = df[df['status'] == 'SUCCESS'].copy()
                if not df_plot.empty:
                    df_plot['rank_num'] = pd.to_numeric(df_plot['category_rank'], errors='coerce')
                    df_plot['timestamp_dt'] = pd.to_datetime(df_plot['timestamp'])
                    df_plot = df_plot.dropna(subset=['rank_num'])
                    
                    if not df_plot.empty:
                        st.subheader("📈 Rank Grafiği")
                        st.line_chart(df_plot.set_index('timestamp_dt')['rank_num'])
            
            # Son kayıtlar
            st.subheader("📜 Son 20 Kayıt")
            display_df = df[['timestamp', 'category_rank', 'status']].tail(20)
            display_df.columns = ['Tarih', 'Rank', 'Durum']
            st.dataframe(display_df, use_container_width=True)
            
            # CSV indirme
            csv_data = df.to_csv(index=False)
            st.download_button(
                label="📥 CSV'yi İndir",
                data=csv_data,
                file_name=f"rank_tracking_{datetime.now().strftime('%Y%m%d_%H%M')}.csv",
                mime="text/csv"
            )
        else:
            st.info("📭 CSV'de henüz kayıt yok")
    
    # Sidebar
    with st.sidebar:
        st.header("📌 Kitap Bilgileri")
        st.info(f"**ASIN:** {ASIN}")
        st.info(f"**Kategori:** {CATEGORY}")
        
        st.markdown("---")
        st.subheader("🔧 GitHub Durumu")
        
        if GITHUB_TOKEN.startswith("ghp_"):
            st.success("✅ Token geçerli")
        else:
            st.error("❌ Token formatı hatalı")
        
        try:
            g = Github(GITHUB_TOKEN)
            repo = g.get_repo(REPO_NAME)
            st.success(f"✅ Repo: {REPO_NAME}")
        except:
            st.error("❌ Repo'ya erişilemiyor")
        
        st.markdown("---")
        st.caption("🔄 Her saat başı otomatik güncellenir")
        st.caption(f"📁 {CSV_PATH_IN_REPO}")

if __name__ == "__main__":
    main()
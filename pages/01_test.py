import streamlit as st
import pandas as pd
import requests
from datetime import datetime
import re
import os
import time

# Kitap bilgileri
ASIN = "B0G584KJ73"
URL = f"https://www.amazon.com/dp/{ASIN}"
CATEGORY = "Money & Monetary Policy (Books)"
CSV_FILE = "rank_tracking.csv"

def fetch_book_rank():
    """Amazon sayfasından kitabın güncel sıralamasını çeker (requests_html olmadan)"""
    
    headers = {
        'User-Agent': 'Mozilla/5.0 (Windows NT 10.0; Win64; x64) AppleWebKit/537.36 (KHTML, like Gecko) Chrome/120.0.0.0 Safari/537.36',
        'Accept-Language': 'en-US,en;q=0.9',
        'Accept-Encoding': 'gzip, deflate, br',
        'Accept': 'text/html,application/xhtml+xml,application/xml;q=0.9,image/webp,*/*;q=0.8',
        'Connection': 'keep-alive',
        'Upgrade-Insecure-Requests': '1'
    }
    
    try:
        st.info(f"Amazon'dan veri çekiliyor... ({datetime.now().strftime('%Y-%m-%d %H:%M:%S')})")
        
        # Sayfayı çek
        response = requests.get(URL, headers=headers, timeout=30)
        html_text = response.text
        
        # Best Sellers Rank bilgisini bul
        rank_text = None
        
        # Pattern 1: Best Sellers Rank metnini bul
        pattern1 = r'Best Sellers Rank[:\s]+([^#]+?)(?=#|\n|$)'
        match1 = re.search(pattern1, html_text, re.IGNORECASE)
        if match1:
            rank_text = match1.group(1).strip()
        
        # Pattern 2: Detaylı rank bilgisi
        if not rank_text:
            pattern2 = r'#(\d{1,3}(?:,\d{3})*)\s+in\s+Books'
            match2 = re.search(pattern2, html_text)
            if match2:
                rank_text = f"#{match2.group(1)} in Books"
        
        if rank_text:
            # Ana rank sayısını bul
            main_rank = None
            rank_numbers = re.findall(r'#(\d{1,3}(?:,\d{3})*)', rank_text)
            if rank_numbers:
                main_rank = rank_numbers[0].replace(',', '')
            
            # Kategori sıralamasını bul
            category_rank = None
            if CATEGORY in html_text:
                cat_idx = html_text.find(CATEGORY)
                search_start = max(0, cat_idx - 50)
                search_area = html_text[search_start:cat_idx]
                numbers = re.findall(r'#?(\d{1,3}(?:,\d{3})*(?:\.\d+)?)', search_area)
                if numbers:
                    category_rank = numbers[-1].replace(',', '')
            
            return {
                'timestamp': datetime.now().strftime('%Y-%m-%d %H:%M:%S'),
                'datetime': datetime.now().strftime('%Y%m%d_%H%M%S'),
                'asin': ASIN,
                'main_rank': main_rank,
                'category_rank': category_rank,
                'full_rank_text': rank_text,
                'category': CATEGORY,
                'url': URL,
                'status': 'SUCCESS'
            }
        else:
            st.warning("Rank bilgisi bulunamadı")
            return None
            
    except Exception as e:
        st.error(f"Hata oluştu: {str(e)}")
        return None

def save_to_csv(data):
    """Verileri CSV'ye kaydeder"""
    file_exists = os.path.isfile(CSV_FILE)
    
    # DataFrame oluştur
    if data:
        df_new = pd.DataFrame([data])
    else:
        df_new = pd.DataFrame([{
            'timestamp': datetime.now().strftime('%Y-%m-%d %H:%M:%S'),
            'datetime': datetime.now().strftime('%Y%m%d_%H%M%S'),
            'asin': ASIN,
            'main_rank': '',
            'category_rank': '',
            'full_rank_text': 'VERI_BULUNAMADI',
            'category': CATEGORY,
            'url': URL,
            'status': 'FAILED'
        }])
    
    # CSV'ye ekle veya oluştur
    if file_exists:
        df_existing = pd.read_csv(CSV_FILE)
        df_combined = pd.concat([df_existing, df_new], ignore_index=True)
    else:
        df_combined = df_new
    
    df_combined.to_csv(CSV_FILE, index=False)
    return df_combined

def main():
    st.set_page_config(page_title="Amazon Rank Takip", layout="wide")
    
    st.title("📊 Amazon Rank Takip Sistemi")
    st.markdown("---")
    
    # Sidebar
    with st.sidebar:
        st.header("📌 Kitap Bilgileri")
        st.info(f"**ASIN:** {ASIN}")
        st.info(f"**Kategori:** {CATEGORY}")
        st.info(f"**CSV Dosyası:** {CSV_FILE}")
        
        st.markdown("---")
        if st.button("🔄 Yeni Kontrol Yap", type="primary"):
            with st.spinner("Veri çekiliyor..."):
                data = fetch_book_rank()
                df = save_to_csv(data)
                st.success("Veri kaydedildi!")
                st.rerun()
    
    # Ana içerik
    col1, col2 = st.columns(2)
    
    with col1:
        st.subheader("📈 Son Rank Bilgisi")
        if os.path.isfile(CSV_FILE):
            df = pd.read_csv(CSV_FILE)
            if not df.empty:
                son_kayit = df.iloc[-1]
                if son_kayit['status'] == 'SUCCESS':
                    st.metric(
                        label="Ana Rank", 
                        value=f"#{son_kayit['main_rank']}" if pd.notna(son_kayit['main_rank']) else "Bulunamadı"
                    )
                    if pd.notna(son_kayit['category_rank']) and son_kayit['category_rank']:
                        st.metric(label="Kategori Rank", value=f"#{son_kayit['category_rank']}")
                    st.caption(f"Son güncelleme: {son_kayit['timestamp']}")
                else:
                    st.warning("Son kontrol başarısız")
            else:
                st.info("Henüz veri yok")
    
    with col2:
        st.subheader("📊 Rank Grafiği")
        if os.path.isfile(CSV_FILE):
            df = pd.read_csv(CSV_FILE)
            if len(df) > 1 and df['main_rank'].notna().any():
                # Rank değerlerini sayıya çevir
                df_plot = df[df['main_rank'].notna()].copy()
                df_plot['main_rank_num'] = pd.to_numeric(df_plot['main_rank'], errors='coerce')
                df_plot['timestamp_dt'] = pd.to_datetime(df_plot['timestamp'])
                
                if not df_plot.empty:
                    fig_data = df_plot[['timestamp_dt', 'main_rank_num']].dropna()
                    if not fig_data.empty:
                        st.line_chart(
                            fig_data.set_index('timestamp_dt'),
                            color='#ff4b4b'
                        )
            else:
                st.info("Grafik için yeterli veri yok")
    
    # Tablo
    st.markdown("---")
    st.subheader("📋 Tüm Kayıtlar")
    if os.path.isfile(CSV_FILE):
        df = pd.read_csv(CSV_FILE)
        if not df.empty:
            # Son 20 kaydı göster
            df_display = df.tail(20).copy()
            df_display = df_display[['timestamp', 'main_rank', 'category_rank', 'status']]
            df_display.columns = ['Tarih', 'Ana Rank', 'Kategori Rank', 'Durum']
            st.dataframe(df_display, use_container_width=True)
            
            # İstatistikler
            st.markdown("---")
            st.subheader("📊 İstatistikler")
            col3, col4, col5 = st.columns(3)
            
            basarili = df[df['status'] == 'SUCCESS'].shape[0]
            basarisiz = df[df['status'] == 'FAILED'].shape[0]
            
            with col3:
                st.metric("Toplam Kontrol", len(df))
            with col4:
                st.metric("Başarılı", basarili)
            with col5:
                st.metric("Başarısız", basarisiz)
            
            # CSV indirme butonu
            csv_data = df.to_csv(index=False)
            st.download_button(
                label="📥 CSV İndir",
                data=csv_data,
                file_name=f"amazon_rank_{datetime.now().strftime('%Y%m%d')}.csv",
                mime="text/csv"
            )
        else:
            st.info("Henüz kayıt yok")
    else:
        st.info("CSV dosyası henüz oluşturulmamış. 'Yeni Kontrol Yap' butonuyla ilk kaydı oluşturun.")

if __name__ == "__main__":
    main()
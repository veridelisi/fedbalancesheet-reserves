import streamlit as st
import pandas as pd
import requests
from datetime import datetime
import re
import os

# Kitap bilgileri
ASIN = "B0G584KJ73"
URL = f"https://www.amazon.com/dp/{ASIN}"
CATEGORY = "Money & Monetary Policy (Books)"
CSV_FILE = "rank_tracking.csv"

def fetch_book_rank():
    """Amazon sayfasından kitabın güncel sıralamasını çeker"""
    
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
        main_rank = None
        category_rank = None
        full_text = ""
        
        # Pattern 1: İki satırlı format (ekran görüntünüzdeki gibi)
        # "Best Sellers Rank: #177,453 in Books (See Top 100 in Books) #86 in Money & Monetary Policy (Books)"
        pattern_double = r'Best Sellers Rank[:\s]+#(\d{1,3}(?:,\d{3})*)\s+in\s+Books[^#]+#(\d{1,3}(?:,\d{3})*)\s+in\s+' + re.escape(CATEGORY)
        match_double = re.search(pattern_double, html_text, re.IGNORECASE | re.DOTALL)
        
        if match_double:
            main_rank = match_double.group(1).replace(',', '')
            category_rank = match_double.group(2).replace(',', '')
            full_text = f"Best Sellers Rank: #{main_rank} in Books, #{category_rank} in {CATEGORY}"
            st.success(f"✓ Çift rank bulundu - Books: #{main_rank}, {CATEGORY}: #{category_rank}")
        
        # Pattern 2: Ayrı ayrı satırlar
        if not main_rank:
            # Books rank satırı
            pattern_books = r'#(\d{1,3}(?:,\d{3})*)\s+in\s+Books'
            match_books = re.search(pattern_books, html_text)
            if match_books:
                main_rank = match_books.group(1).replace(',', '')
            
            # Kategori rank satırı - tam eşleme
            pattern_category = r'#(\d{1,3}(?:,\d{3})*)\s+in\s+' + re.escape(CATEGORY)
            match_category = re.search(pattern_category, html_text)
            if match_category:
                category_rank = match_category.group(1).replace(',', '')
            
            if main_rank or category_rank:
                full_text = f"#{main_rank} in Books, #{category_rank} in {CATEGORY}"
                st.success(f"✓ Ayrı rankler bulundu - Books: #{main_rank}, {CATEGORY}: #{category_rank}")
        
        # Pattern 3: Best Sellers Rank genel metni
        if not main_rank and not category_rank:
            pattern_bsr = r'Best Sellers Rank[:\s]+([^#]+(?:#\d{1,3}(?:,\d{3})*[^#]*)+)'
            match_bsr = re.search(pattern_bsr, html_text, re.IGNORECASE | re.DOTALL)
            if match_bsr:
                rank_text_raw = match_bsr.group(1)
                # Tüm rankleri bul
                numbers = re.findall(r'#(\d{1,3}(?:,\d{3})*)', rank_text_raw)
                categories = re.findall(r'in\s+([^(]+?)(?:\s*\(|$)', rank_text_raw)
                
                if len(numbers) >= 1:
                    main_rank = numbers[0].replace(',', '')
                if len(numbers) >= 2:
                    category_rank = numbers[1].replace(',', '')
                
                full_text = rank_text_raw.strip()
                st.success(f"✓ Genel metin bulundu")
        
        if main_rank or category_rank:
            # Rank değerlerini temizle
            if main_rank and '.' in main_rank:
                main_rank = main_rank.split('.')[0]
            if category_rank and '.' in category_rank:
                category_rank = category_rank.split('.')[0]
            
            # Debug: Bulunan değerleri göster
            with st.expander("🔍 Debug - Bulunan Değerler"):
                st.write(f"Main Rank (Books): {main_rank}")
                st.write(f"Category Rank ({CATEGORY}): {category_rank}")
                st.write(f"Full Text: {full_text}")
            
            return {
                'timestamp': datetime.now().strftime('%Y-%m-%d %H:%M:%S'),
                'datetime': datetime.now().strftime('%Y%m%d_%H%M%S'),
                'asin': ASIN,
                'main_rank': main_rank,
                'category_rank': category_rank,
                'full_rank_text': full_text,
                'category': CATEGORY,
                'url': URL,
                'status': 'SUCCESS'
            }
        else:
            st.warning("⚠️ Rank bilgisi bulunamadı")
            
            # Debug: Best Sellers Rank geçen satırları göster
            with st.expander("🔍 Debug - Best Sellers Rank İçeren Satırlar"):
                lines = html_text.split('\n')
                bsr_lines = [line.strip() for line in lines if 'Best Sellers Rank' in line or '#86 in' in line]
                for line in bsr_lines[:5]:  # İlk 5 satır
                    st.code(line)
            
            return None
            
    except Exception as e:
        st.error(f"❌ Hata oluştu: {str(e)}")
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

def format_rank(rank_value):
    """Rank değerini formatlar"""
    if pd.notna(rank_value) and rank_value:
        try:
            # Noktalı sayıyı temizle
            if '.' in str(rank_value):
                rank_int = int(float(str(rank_value)))
            else:
                rank_int = int(str(rank_value).replace(',', ''))
            return f"#{rank_int:,}"
        except:
            return str(rank_value)
    return '-'

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
                if data:
                    st.success(f"✓ Veri kaydedildi!")
                    st.info(f"📚 Books Rank: #{data['main_rank']}")
                    st.info(f"🏷️ {CATEGORY} Rank: #{data['category_rank']}")
                else:
                    st.error("✗ Veri çekilemedi")
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
                    # Ana rank (Books)
                    if pd.notna(son_kayit['main_rank']) and son_kayit['main_rank']:
                        st.metric(
                            label="📚 Books Kategorisi Rank", 
                            value=format_rank(son_kayit['main_rank'])
                        )
                    
                    # Kategori rank
                    if pd.notna(son_kayit['category_rank']) and son_kayit['category_rank']:
                        st.metric(
                            label=f"🏷️ {CATEGORY} Rank", 
                            value=format_rank(son_kayit['category_rank'])
                        )
                    
                    st.caption(f"Son güncelleme: {son_kayit['timestamp']}")
                    
                    # Tam metin
                    if pd.notna(son_kayit['full_rank_text']) and son_kayit['full_rank_text']:
                        st.info(f"**Tam metin:** {son_kayit['full_rank_text']}")
                else:
                    st.warning("⚠️ Son kontrol başarısız")
            else:
                st.info("📭 Henüz veri yok")
    
    with col2:
        st.subheader("📊 Rank Grafiği (Kategori)")
        if os.path.isfile(CSV_FILE):
            df = pd.read_csv(CSV_FILE)
            if len(df) > 1 and df['category_rank'].notna().any():
                # Rank değerlerini sayıya çevir
                df_plot = df[df['category_rank'].notna()].copy()
                
                # Kategori rank'ini sayıya çevir
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
                        
                        # Son değer
                        son_rank = fig_data['category_rank_num'].iloc[-1]
                        st.caption(f"Son kategori rank: #{son_rank:,}")
                else:
                    st.info("📭 Grafik için yeterli veri yok")
            else:
                st.info("📭 Grafik için yeterli veri yok")
    
    # Tablo
    st.markdown("---")
    st.subheader("📋 Son 20 Kayıt")
    if os.path.isfile(CSV_FILE):
        df = pd.read_csv(CSV_FILE)
        if not df.empty:
            # Son 20 kaydı göster
            df_display = df.tail(20).copy()
            
            # Rank değerlerini formatla
            df_display['main_rank_display'] = df_display['main_rank'].apply(format_rank)
            df_display['category_rank_display'] = df_display['category_rank'].apply(format_rank)
            
            display_cols = ['timestamp', 'main_rank_display', 'category_rank_display', 'status']
            df_display = df_display[display_cols]
            df_display.columns = ['Tarih', 'Books Rank', f'{CATEGORY} Rank', 'Durum']
            
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
            st.info("📭 Henüz kayıt yok")
    else:
        st.info("📭 CSV dosyası henüz oluşturulmamış. 'Yeni Kontrol Yap' butonuyla ilk kaydı oluşturun.")

if __name__ == "__main__":
    main()
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
    """Amazon sayfasından Money & Monetary Policy rankını çeker"""
    
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
        
        # Money & Monetary Policy rankını bul
        category_rank = None
        full_text = ""
        
        # Pattern: Money & Monetary Policy linki içindeki rank
        # Örnek: #86 in <a href='/gp/bestsellers/books/2598/ref=pd_zg_hrsr_books'>Money & Monetary Policy
        pattern = r'#(\d{1,3}(?:,\d{3})*)\s+in\s+<a[^>]*>' + re.escape("Money & Monetary Policy")
        match = re.search(pattern, html_text, re.IGNORECASE)
        
        if match:
            category_rank = match.group(1).replace(',', '')
            full_text = f"#{category_rank} in Money & Monetary Policy (Books)"
            st.success(f"✓ Money & Monetary Policy rankı bulundu: #{category_rank}")
        else:
            # Alternatif pattern: Daha genel
            pattern2 = r'#(\d{1,3}(?:,\d{3})*)\s+in\s+<a[^>]*>Money\s*&\s*Monetary\s*Policy'
            match2 = re.search(pattern2, html_text, re.IGNORECASE)
            
            if match2:
                category_rank = match2.group(1).replace(',', '')
                full_text = f"#{category_rank} in Money & Monetary Policy (Books)"
                st.success(f"✓ Alternatif pattern ile bulundu: #{category_rank}")
        
        if category_rank:
            # Rank değerini temizle
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
            st.warning("⚠️ Money & Monetary Policy rankı bulunamadı")
            
            # Debug: Money & Monetary Policy içeren satırları göster
            with st.expander("🔍 Debug - Money & Monetary Policy İçeren Satırlar"):
                lines = html_text.split('\n')
                cat_lines = [line.strip() for line in lines if "Money & Monetary Policy" in line]
                for i, line in enumerate(cat_lines[:10]):
                    st.code(f"{i+1}: {line}")
            
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
            'category_rank': '',
            'full_rank_text': 'VERI_BULUNAMADI',
            'category': "Money & Monetary Policy",
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
    st.set_page_config(page_title="Money & Monetary Policy Rank Takip", layout="wide")
    
    st.title("💰 Money & Monetary Policy Rank Takip")
    st.markdown("---")
    
    # Sidebar
    with st.sidebar:
        st.header("📌 Kitap Bilgileri")
        st.info(f"**ASIN:** {ASIN}")
        st.info(f"**Kategori:** Money & Monetary Policy")
        st.info(f"**CSV Dosyası:** {CSV_FILE}")
        
        st.markdown("---")
        if st.button("🔄 Yeni Kontrol Yap", type="primary"):
            with st.spinner("Veri çekiliyor..."):
                data = fetch_book_rank()
                df = save_to_csv(data)
                if data:
                    st.success(f"✓ Veri kaydedildi!")
                    st.info(f"🏷️ Rank: #{data['category_rank']}")
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
                    if pd.notna(son_kayit['category_rank']) and son_kayit['category_rank']:
                        st.metric(
                            label="🏷️ Money & Monetary Policy", 
                            value=format_rank(son_kayit['category_rank'])
                        )
                    
                    st.caption(f"Son güncelleme: {son_kayit['timestamp']}")
                    
                    if pd.notna(son_kayit['full_rank_text']) and son_kayit['full_rank_text']:
                        st.info(f"**Tam metin:** {son_kayit['full_rank_text']}")
                else:
                    st.warning("⚠️ Son kontrol başarısız")
            else:
                st.info("📭 Henüz veri yok")
    
    with col2:
        st.subheader("📊 Rank Grafiği")
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
                        
                        son_rank = fig_data['category_rank_num'].iloc[-1]
                        st.caption(f"Son rank: #{son_rank:,}")
                        
                        min_rank = fig_data['category_rank_num'].min()
                        max_rank = fig_data['category_rank_num'].max()
                        st.caption(f"Min: #{min_rank:,} | Max: #{max_rank:,}")
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
            df_display = df.tail(20).copy()
            df_display['category_rank_display'] = df_display['category_rank'].apply(format_rank)
            
            display_cols = ['timestamp', 'category_rank_display', 'status']
            df_display = df_display[display_cols]
            df_display.columns = ['Tarih', 'Money & Monetary Policy Rank', 'Durum']
            
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
            
            # Ortalama rank
            basarili_df = df[df['status'] == 'SUCCESS']
            if not basarili_df.empty and basarili_df['category_rank'].notna().any():
                ranks = []
                for r in basarili_df['category_rank'].dropna():
                    try:
                        if '.' in str(r):
                            ranks.append(int(float(str(r))))
                        else:
                            ranks.append(int(str(r).replace(',', '')))
                    except:
                        pass
                if ranks:
                    avg_rank = sum(ranks) / len(ranks)
                    st.metric("Ortalama Rank", f"#{int(avg_rank):,}")
            
            # CSV indirme butonu
            csv_data = df.to_csv(index=False)
            st.download_button(
                label="📥 CSV İndir",
                data=csv_data,
                file_name=f"money_policy_rank_{datetime.now().strftime('%Y%m%d')}.csv",
                mime="text/csv"
            )
        else:
            st.info("📭 Henüz kayıt yok")
    else:
        st.info("📭 CSV dosyası henüz oluşturulmamış. 'Yeni Kontrol Yap' butonuyla ilk kaydı oluşturun.")

if __name__ == "__main__":
    main()



import os
import streamlit as st

# CSV dosyasının tam yolunu göster
CSV_FILE = "rank_tracking.csv"
tam_yol = os.path.abspath(CSV_FILE)
st.info(f"📁 CSV Dosya Konumu: `{tam_yol}`")    
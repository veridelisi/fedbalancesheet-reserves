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
    """Amazon sayfasından rank bilgilerini çeker - DEBUG VERSİYONU"""
    
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
        
        # DEBUG: "Best Sellers Rank" içeren tüm satırları bul
        st.subheader("🔍 DEBUG: Best Sellers Rank İçeren Satırlar")
        
        lines = html_text.split('\n')
        bsr_lines = []
        
        for i, line in enumerate(lines):
            if "Best Sellers Rank" in line:
                bsr_lines.append((i, line.strip()))
        
        if bsr_lines:
            for idx, (line_no, line) in enumerate(bsr_lines[:10]):  # İlk 10 satır
                st.code(f"Satır {line_no}: {line}")
                
                # Bu satırda # ile başlayan rankleri bul
                ranks = re.findall(r'#(\d{1,3}(?:,\d{3})*)', line)
                if ranks:
                    st.write(f"Bulunan rankler: {ranks}")
        else:
            st.warning("'Best Sellers Rank' hiçbir satırda bulunamadı!")
        
        # Tüm rank pattern'lerini bul
        st.subheader("🔍 Tüm # ile başlayan rankler")
        all_ranks = re.findall(r'#(\d{1,3}(?:,\d{3})*)\s+in\s+([^(]+?)(?:\s*\(|$)', html_text)
        
        if all_ranks:
            for rank_num, rank_cat in all_ranks:
                st.write(f"Rank: #{rank_num} - Kategori: {rank_cat.strip()}")
        else:
            st.warning("Hiç rank bulunamadı!")
        
        # Belirli bir bölgeyi ara (product details)
        st.subheader("🔍 Product Details Bölgesi")
        
        # Product details div'ini bulmaya çalış
        product_details_pattern = r'productDetails[^>]*>(.*?)</div>'
        product_details = re.search(product_details_pattern, html_text, re.IGNORECASE | re.DOTALL)
        
        if product_details:
            st.code(product_details.group(1)[:500])  # İlk 500 karakter
        else:
            st.warning("Product details bölümü bulunamadı!")
        
        # Manuel olarak rank'ı bulmaya çalış
        st.subheader("🔍 Manuel Rank Arama")
        
        # #86 in Money & Monetary Policy (Books) ara
        specific_pattern = r'#86\s+in\s+Money\s+&\s+Monetary\s+Policy'
        specific_match = re.search(specific_pattern, html_text, re.IGNORECASE)
        
        if specific_match:
            st.success(f"✓ #86 rankı bulundu! {specific_match.group(0)}")
        else:
            st.warning("#86 rankı bulunamadı!")
        
        # Genel kategori rank ara
        cat_pattern = r'#(\d{1,3}(?:,\d{3})*)\s+in\s+Money\s+&\s+Monetary\s+Policy'
        cat_match = re.search(cat_pattern, html_text, re.IGNORECASE)
        
        if cat_match:
            st.success(f"✓ Kategori rankı bulundu! #{cat_match.group(1)}")
        else:
            st.warning("Kategori rankı bulunamadı!")
        
        # Best Sellers Rank'in olduğu bölümü bul
        st.subheader("🔍 Best Sellers Rank Bölümü")
        
        # Best Sellers Rank'ten sonraki 500 karakter
        bsr_index = html_text.find("Best Sellers Rank")
        if bsr_index != -1:
            bsr_section = html_text[bsr_index:bsr_index + 500]
            st.code(bsr_section)
        else:
            st.warning("Best Sellers Rank metni bulunamadı!")
        
        return None  # DEBUG: Hiçbir şey döndürme, sadece debug bilgisi göster
        
    except Exception as e:
        st.error(f"❌ Hata oluştu: {str(e)}")
        return None

def main():
    st.set_page_config(page_title="Amazon Rank Debug", layout="wide")
    
    st.title("🔍 Amazon Rank Debug Aracı")
    st.markdown("---")
    
    st.info(f"**ASIN:** {ASIN}")
    st.info(f"**Kategori:** {CATEGORY}")
    
    if st.button("🔄 Debug Yap", type="primary"):
        with st.spinner("Analiz ediliyor..."):
            fetch_book_rank()

if __name__ == "__main__":
    main()
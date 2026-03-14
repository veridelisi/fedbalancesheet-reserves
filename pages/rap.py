import csv
import time
from datetime import datetime
from requests_html import HTMLSession
import os
import re

# Kitap bilgileri
ASIN = "B0G584KJ73"
URL = f"https://www.amazon.com/dp/{ASIN}"
CATEGORY = "Money & Monetary Policy (Books)"
CSV_FILE = "rank_tracking.csv"  # Sabit dosya adı

def fetch_book_rank():
    """Amazon sayfasından kitabın güncel sıralamasını çeker"""
    session = HTMLSession()
    
    headers = {
        'User-Agent': 'Mozilla/5.0 (Windows NT 10.0; Win64; x64) AppleWebKit/537.36 (KHTML, like Gecko) Chrome/120.0.0.0 Safari/537.36',
        'Accept-Language': 'en-US,en;q=0.9',
        'Accept-Encoding': 'gzip, deflate, br',
        'Accept': 'text/html,application/xhtml+xml,application/xml;q=0.9,image/webp,*/*;q=0.8',
        'Connection': 'keep-alive',
        'Upgrade-Insecure-Requests': '1'
    }
    
    try:
        print(f"[{datetime.now().strftime('%Y-%m-%d %H:%M:%S')}] Amazon'dan veri çekiliyor...")
        
        # Sayfayı al ve JavaScript'i render et
        response = session.get(URL, headers=headers, timeout=30)
        response.html.render(sleep=3, keep_page=True, scrolldown=1)
        
        # Best Sellers Rank bilgisini bul
        rank_selectors = [
            '#productDetails_detailBullets_sections1 tr:contains("Best Sellers Rank") td span',
            '#productDetails_detailBullets_sections1 tr:contains("Best Sellers Rank") td',
            '.a-section .a-row:contains("Best Sellers Rank") span',
            '#detailBullets_feature_div span:contains("Best Sellers Rank")',
            'th:contains("Best Sellers Rank") + td',
            '#SalesRank',
            '.a-row:contains("Best Sellers Rank")'
        ]
        
        rank_text = None
        for selector in rank_selectors:
            elements = response.html.find(selector)
            if elements:
                rank_text = elements[0].text
                break
        
        if not rank_text:
            # Sayfanın tüm metninde ara
            html_text = response.html.text
            if "Best Sellers Rank" in html_text:
                # Best Sellers Rank'ten sonraki kısmı al
                pattern = r'Best Sellers Rank[:\s]+([^#]+?)(?=#|\n|$)'
                match = re.search(pattern, html_text, re.IGNORECASE)
                if match:
                    rank_text = match.group(1).strip()
        
        if rank_text:
            # Kategori sıralamasını bul
            category_rank = None
            if CATEGORY in response.html.text:
                html_text = response.html.text
                cat_idx = html_text.find(CATEGORY)
                # Kategoriden önceki sayıyı bul
                search_start = max(0, cat_idx - 50)
                search_area = html_text[search_start:cat_idx]
                numbers = re.findall(r'#?(\d{1,3}(?:,\d{3})*(?:\.\d+)?)', search_area)
                if numbers:
                    category_rank = numbers[-1].replace(',', '')
            
            # Ana rank sayısını bul
            main_rank = None
            rank_numbers = re.findall(r'#(\d{1,3}(?:,\d{3})*)', rank_text)
            if rank_numbers:
                main_rank = rank_numbers[0].replace(',', '')
            
            return {
                'timestamp': datetime.now().strftime('%Y-%m-%d %H:%M:%S'),
                'datetime': datetime.now().strftime('%Y%m%d_%H%M%S'),  # Dosya adı için format
                'asin': ASIN,
                'main_rank': main_rank,
                'category_rank': category_rank,
                'full_rank_text': rank_text,
                'category': CATEGORY,
                'url': URL
            }
        else:
            print(f"[{datetime.now().strftime('%Y-%m-%d %H:%M:%S')}] ✗ Rank bilgisi bulunamadı")
            return None
            
    except Exception as e:
        print(f"[{datetime.now().strftime('%Y-%m-%d %H:%M:%S')}] ✗ Hata oluştu: {str(e)}")
        return None
    finally:
        session.close()

def save_to_csv(data):
    """Verileri CSV'ye kaydeder - her çalıştırmada yeni satır ekler"""
    file_exists = os.path.isfile(CSV_FILE)
    
    with open(CSV_FILE, 'a', newline='', encoding='utf-8') as f:
        writer = csv.writer(f)
        
        # Dosya yoksa başlıkları yaz
        if not file_exists:
            writer.writerow([
                'Timestamp',           # Okunabilir tarih-saat
                'Datetime_File',        # Dosya adı için format
                'ASIN',
                'Main_Rank',            # Ana sıralama (#86 gibi)
                'Category_Rank',         # Kategori içindeki sıra
                'Full_Rank_Text',        # Tam rank metni
                'Category',
                'URL',
                'Status'                 # Başarılı/başarısız
            ])
        
        if data:
            writer.writerow([
                data['timestamp'],
                data['datetime'],
                data['asin'],
                data['main_rank'],
                data['category_rank'],
                data['full_rank_text'],
                data['category'],
                data['url'],
                'SUCCESS'
            ])
            print(f"[{data['timestamp']}] ✓ Veri kaydedildi - Rank: {data['main_rank']}")
        else:
            # Veri yoksa da zaman damgasıyla boş kayıt ekle
            now = datetime.now()
            writer.writerow([
                now.strftime('%Y-%m-%d %H:%M:%S'),
                now.strftime('%Y%m%d_%H%M%S'),
                ASIN,
                '',
                '',
                'VERI_BULUNAMADI',
                CATEGORY,
                URL,
                'FAILED'
            ])
            print(f"[{now.strftime('%Y-%m-%d %H:%M:%S')}] ✗ Veri yok - başarısız kayıt eklendi")

def print_last_records(n=5):
    """Son n kaydı gösterir"""
    if os.path.isfile(CSV_FILE):
        with open(CSV_FILE, 'r', encoding='utf-8') as f:
            lines = f.readlines()
            if len(lines) > 1:
                print(f"\n📊 Son {min(n, len(lines)-1)} kayıt:")
                print("-" * 80)
                for i in range(max(1, len(lines)-n), len(lines)):
                    print(lines[i].strip())

def main():
    """Ana fonksiyon - her çalıştırmada bir kere çalışır"""
    print("=" * 60)
    print("AMAZON RANK TAKİP - TEK ÇALIŞTIRMA")
    print("=" * 60)
    print(f"ASIN: {ASIN}")
    print(f"Kategori: {CATEGORY}")
    print(f"CSV Dosyası: {CSV_FILE}")
    print("-" * 60)
    
    # Veriyi çek
    data = fetch_book_rank()
    
    # CSV'ye kaydet
    save_to_csv(data)
    
    # Son kayıtları göster
    print_last_records()
    
    print("\n" + "=" * 60)
    print(f"İşlem tamamlandı! Kayıtlar {CSV_FILE} dosyasına eklendi.")
    print("=" * 60)

if __name__ == "__main__":
    main()
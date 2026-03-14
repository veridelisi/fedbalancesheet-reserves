import csv
import time
from datetime import datetime
from requests_html import HTMLSession
import os

# Kitap bilgileri
ASIN = "B0G584KJ73"
URL = f"https://www.amazon.com/dp/{ASIN}"
CATEGORY = "Money & Monetary Policy (Books)"
CSV_FILE = "amazon_rank_tracker.csv"

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
        # Sayfayı al ve JavaScript'i render et
        response = session.get(URL, headers=headers, timeout=30)
        response.html.render(sleep=3, keep_page=True, scrolldown=1)
        
        # Best Sellers Rank bilgisini bul
        # Farklı olası selector'ları dene
        rank_selectors = [
            '#productDetails_detailBullets_sections1 tr:contains("Best Sellers Rank") td span',
            '#productDetails_detailBullets_sections1 tr:contains("Best Sellers Rank") td',
            '.a-section .a-row:contains("Best Sellers Rank") span',
            '#detailBullets_feature_div span:contains("Best Sellers Rank")',
            'th:contains("Best Sellers Rank") + td',
        ]
        
        rank_text = None
        for selector in rank_selectors:
            elements = response.html.find(selector)
            if elements:
                rank_text = elements[0].text
                break
        
        if not rank_text:
            # Sayfanın HTML'inde ara
            html_text = response.html.text
            if "Best Sellers Rank" in html_text:
                # Best Sellers Rank'ten sonraki kısmı al
                start_idx = html_text.find("Best Sellers Rank") + len("Best Sellers Rank")
                end_idx = html_text.find("(", start_idx)
                if end_idx == -1:
                    end_idx = start_idx + 200
                rank_text = html_text[start_idx:end_idx].strip()
        
        if rank_text:
            # Kategori sıralamasını bul
            category_rank = None
            if CATEGORY in html_text:
                cat_idx = html_text.find(CATEGORY)
                # Kategoriden önceki sayıyı bul (sondan 20 karaktere kadar bak)
                search_start = max(0, cat_idx - 50)
                search_area = html_text[search_start:cat_idx]
                import re
                numbers = re.findall(r'#?(\d{1,3}(?:,\d{3})*(?:\.\d+)?)', search_area)
                if numbers:
                    category_rank = numbers[-1].replace(',', '')
            
            return {
                'timestamp': datetime.now().strftime('%Y-%m-%d %H:%M:%S'),
                'asin': ASIN,
                'rank_text': rank_text,
                'category_rank': category_rank,
                'category': CATEGORY,
                'url': URL
            }
        else:
            print(f"[{datetime.now()}] Rank bilgisi bulunamadı")
            return None
            
    except Exception as e:
        print(f"[{datetime.now()}] Hata oluştu: {str(e)}")
        return None
    finally:
        session.close()

def save_to_csv(data):
    """Verileri CSV'ye kaydeder"""
    file_exists = os.path.isfile(CSV_FILE)
    
    with open(CSV_FILE, 'a', newline='', encoding='utf-8') as f:
        writer = csv.writer(f)
        
        # Dosya yoksa başlıkları yaz
        if not file_exists:
            writer.writerow([
                'Timestamp', 
                'ASIN', 
                'Full Rank Text', 
                'Category Rank',
                'Category',
                'URL'
            ])
        
        if data:
            writer.writerow([
                data['timestamp'],
                data['asin'],
                data['rank_text'],
                data['category_rank'],
                data['category'],
                data['url']
            ])
            print(f"[{data['timestamp']}] Veri kaydedildi: {data['rank_text']}")
        else:
            # Veri yoksa da zaman damgasıyla boş kayıt ekle
            writer.writerow([
                datetime.now().strftime('%Y-%m-%d %H:%M:%S'),
                ASIN,
                'VERI_YOK',
                '',
                CATEGORY,
                URL
            ])
            print(f"[{datetime.now()}] Veri yok - boş kayıt eklendi")

def track_rank_hourly():
    """Saatlik takip yapar"""
    print(f"Amazon Rank Takip Başladı - ASIN: {ASIN}")
    print(f"Hedef Kategori: {CATEGORY}")
    print(f"Çıktı Dosyası: {CSV_FILE}")
    print("-" * 50)
    
    while True:
        try:
            # Veriyi çek
            data = fetch_book_rank()
            
            # CSV'ye kaydet
            save_to_csv(data)
            
            # 1 saat bekle (3600 saniye)
            next_check = datetime.now().replace(minute=0, second=0) + timedelta(hours=1)
            wait_seconds = (next_check - datetime.now()).total_seconds()
            
            if wait_seconds > 0:
                print(f"Sonraki kontrol: {next_check.strftime('%Y-%m-%d %H:%M:%S')}")
                print(f"Bekleniyor ({int(wait_seconds/60)} dakika)...")
                print("-" * 50)
                time.sleep(wait_seconds)
            
        except KeyboardInterrupt:
            print("\nTakip durduruldu.")
            break
        except Exception as e:
            print(f"Beklenmeyen hata: {e}")
            print("1 saat sonra tekrar deneniyor...")
            time.sleep(3600)

if __name__ == "__main__":
    from datetime import timedelta
    track_rank_hourly()
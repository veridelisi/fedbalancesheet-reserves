# fix_csv_columns.py
import pandas as pd
import os

# CSV dosya yolu
CSV_FILE = "pages/rank_tracking.csv"

# Sütun başlıkları
columns = [
    'timestamp', 
    'datetime', 
    'asin', 
    'category_rank', 
    'full_rank_text', 
    'category', 
    'url', 
    'status'
]

# Dosya var mı kontrol et
if os.path.isfile(CSV_FILE):
    print(f"📁 Dosya bulundu: {CSV_FILE}")
    print(f"📏 Dosya boyutu: {os.path.getsize(CSV_FILE)} bytes")
    
    try:
        # CSV'yi oku
        df = pd.read_csv(CSV_FILE)
        print(f"📊 Mevcut sütunlar: {list(df.columns)}")
        print(f"📊 Kayıt sayısı: {len(df)}")
        
    except:
        print("❌ CSV okunamadı, boş dosya olabilir")
        df = pd.DataFrame(columns=columns)
else:
    print(f"📁 Dosya bulunamadı, yeni oluşturuluyor: {CSV_FILE}")
    df = pd.DataFrame(columns=columns)

# Sütunları kontrol et ve düzelt
if list(df.columns) != columns:
    print("🔄 Sütunlar uyuşmuyor, düzeltiliyor...")
    df = pd.DataFrame(columns=columns)

# CSV'yi kaydet
df.to_csv(CSV_FILE, index=False)
print(f"✅ CSV güncellendi: {CSV_FILE}")
print(f"📊 Yeni sütunlar: {list(df.columns)}")
print(f"📏 Yeni dosya boyutu: {os.path.getsize(CSV_FILE)} bytes")

# Kontrol
df_check = pd.read_csv(CSV_FILE)
print("\n📋 CSV içeriği:")
print(df_check)
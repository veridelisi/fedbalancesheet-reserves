# csv_reset.py
import pandas as pd
import os
from datetime import datetime

CSV_FILE = "rank_tracking.csv"

# Eski CSV'yi sil (varsa)
if os.path.isfile(CSV_FILE):
    os.remove(CSV_FILE)
    print(f"✅ Eski CSV silindi: {CSV_FILE}")

# Yeni CSV oluştur (sadece başlıklarla)
df_new = pd.DataFrame(columns=[
    'timestamp', 
    'datetime', 
    'asin', 
    'category_rank', 
    'full_rank_text', 
    'category', 
    'url', 
    'status'
])

# Boş CSV'yi kaydet
df_new.to_csv(CSV_FILE, index=False)
print(f"✅ Yeni CSV oluşturuldu: {CSV_FILE}")
print(f"📁 Konum: {os.path.abspath(CSV_FILE)}")

# Kontrol
if os.path.isfile(CSV_FILE):
    df = pd.read_csv(CSV_FILE)
    print(f"📊 CSV boyutu: {len(df)} kayıt")
    print(f"📁 Dosya boyutu: {os.path.getsize(CSV_FILE)} bytes")
else:
    print("❌ CSV oluşturulamadı!")
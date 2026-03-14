# create_csv_headers.py
import pandas as pd
import os

CSV_FILE = "pages/rank_tracking.csv"  # pages klasöründe oluştur

# Column'ları olan boş DataFrame
df = pd.DataFrame(columns=[
    'timestamp', 
    'datetime', 
    'asin', 
    'category_rank', 
    'full_rank_text', 
    'category', 
    'url', 
    'status'
])

# CSV'yi kaydet
df.to_csv(CSV_FILE, index=False)

print(f"✅ CSV oluşturuldu: {os.path.abspath(CSV_FILE)}")
print(f"📊 Column'lar: {list(df.columns)}")
print(f"📁 Dosya boyutu: {os.path.getsize(CSV_FILE)} bytes")
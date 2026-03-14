import streamlit as st
import pandas as pd
import os

CSV_FILE = "rank_tracking.csv"

if os.path.isfile(CSV_FILE):
    df = pd.read_csv(CSV_FILE)
    
    st.write(f"Toplam kayıt: {len(df)}")
    st.dataframe(df.head(10))  # İlk 10 kaydı göster
    
    if st.button("🗑️ İlk 5 Kaydı Sil", type="primary"):
        # İlk 5 hariç hepsini al
        df_yeni = df.iloc[5:]
        
        # Aynı dosyaya kaydet
        df_yeni.to_csv(CSV_FILE, index=False)
        
        st.success(f"✅ İlk 5 kayıt silindi! Kalan kayıt: {len(df_yeni)}")
        st.rerun()
import streamlit as st

st.set_page_config(page_title="Veridelisi • Analytics Portal", page_icon="📊")
st.title("📊 Veridelisi • Analytics Portal")
st.write("Soldaki menüden veya aşağıdaki kısayoldan gidin.")

# YÖNTEM A (önerilen): Streamlit'in yerleşik sayfa linki
st.page_link("pages/01_Reserves.py", label="➡️ Reserves dashboard")

# (İstersen) YÖNTEM B: Buton + switch_page (düzgün kullanım)
# if st.button("➡️ Reserves dashboard"):
#     st.switch_page("pages/01_Reserves.py")


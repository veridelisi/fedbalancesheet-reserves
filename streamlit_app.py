import streamlit as st

st.set_page_config(page_title="Veridelisi • Analytics Portal", layout="wide")
st.title("📊 Veridelisi • Analytics Portal")

st.write("Soldaki menüden bir proje seçin veya aşağıdaki kısayollardan geçin:")

col1, col2, col3 = st.columns(3)

with col1:
    if st.button("🏦 H.4.1 — Reserves Impact"):
        st.switch_page("pages/01_Reserves.py")

with col2:
    if st.button("👷 Labor / Employment"):
        st.switch_page("pages/02_Labor.py")

with col3:
    if st.button("💹 Markets / Rates"):
        st.switch_page("pages/03_Markets.py")

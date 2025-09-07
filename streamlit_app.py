import streamlit as st

st.set_page_config(page_title="Veridelisi • Analytics Portal")
st.title("📊 Veridelisi • Analytics Portal")
st.write("Soldaki aşağıdaki kısayollardan gidin.")

col1, col2, col3 = st.columns(3)

with col1:
    st.page_link("pages/01_Reserves.py", label="➡️ Reserves dashboard")
# diğer projeler geldiğinde:
# with col2: st.page_link("pages/02_Labor.py", label="👷 Labor / Employment")
# with col3: st.page_link("pages/03_Markets.py", label="📈 Markets / Rates")

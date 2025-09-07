# streamlit_app.py (ana sayfa)
import streamlit as st
st.set_page_config(page_title="Veridelisi • Analytics Portal", page_icon="📊")

st.title("📊 Veridelisi • Analytics Portal")
st.write("Soldaki menüden veya aşağıdaki kısayollardan gidin.")

col1, col2, col3 = st.columns(3)
with col1:
    if st.button("➡️ Reserves dashboard", use_container_width=True):
        st.switch_page("pages/01_Reserves.py")
# ileride diğer projeler:
# with col2:
#     if st.button("👷 Labor / Employment", use_container_width=True):
#         st.switch_page("pages/02_Labor.py")
# with col3:
#     if st.button("📈 Markets / Rates", use_container_width=True):
#         st.switch_page("pages/03_Markets.py")

import streamlit as st

st.set_page_config(page_title="Veridelisi • Analytics Portal", page_icon="📊")
st.title("📊 Veridelisi • Analytics Portal")
st.write("Soldaki menüden veya aşağıdaki kısayoldan gidin.")

col1, col2, col3 = st.columns(3)
with col1:
    if st.button("➡️ Reserves dashboard", use_container_width=True):
        st.switch_page("pages/01_Reserves.py")

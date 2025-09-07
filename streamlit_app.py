import streamlit as st

st.set_page_config(page_title="Veridelisi • Analytics Portal", page_icon="📊")
st.title("📊 Veridelisi • Analytics Portal")
st.write("Soldaki menüden veya aşağıdaki kısayoldan gidin.")

st.switch_page("pages/01_Reserves.py")

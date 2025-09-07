import streamlit as st

st.set_page_config(page_title="Veridelisi • Analytics Portal")
st.title("📊 Veridelisi • Analytics Portal")


# Önce yerleşik page_link (Streamlit >= 1.37'de sorunsuz)
try:
    st.page_link("pages/01_Reserves.py", label="➡️ Reserves dashboard")
except Exception:
    # Eski sürüm veya beklenmedik durumlarda düz bağlantıya düş
    # Not: /Reserves yolu sayfa başlığından (st.set_page_config) türetilir
    st.markdown("[➡️ Reserves dashboard](/Reserves)")

st.markdown("""
    <style>
        section[data-testid="stSidebar"][aria-expanded="true"]{
            display: none;
        }
    </style>
    """, unsafe_allow_html=True)    

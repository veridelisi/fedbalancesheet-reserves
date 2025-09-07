import streamlit as st

st.page_link("streamlit_app.py", label="Home", icon="🏠")
st.page_link("pages/01_Reserves.py", label="Page 1", icon="1️⃣")
st.page_link("pages/page_2.py", label="Page 2", icon="2️⃣", disabled=True)
st.page_link("http://www.google.com", label="Google", icon="🌎")
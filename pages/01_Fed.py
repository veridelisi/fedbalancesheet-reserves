import streamlit as st
import os

st.set_page_config(page_title="Fed Guide", layout="wide")

st.title("📊 Fed Balance Sheet Policy Guide")

# ---------------------------- STOP Expanded -----------------
st.markdown(
    """
<style>
    [data-testid="stSidebarNav"] {display: none;}
    section[data-testid="stSidebar"][aria-expanded="true"]{display: none;}
</style>
""",
    unsafe_allow_html=True,
)

# Proposal listesi
proposals = [f"Proposal {i}" for i in range(1, 16)]

# session state (hangi proposal seçildi)
if "selected" not in st.session_state:
    st.session_state.selected = None

# GRID
cols = st.columns(3)

for i, proposal in enumerate(proposals):
    with cols[i % 3]:
        if st.button(proposal, key=proposal):
            st.session_state.selected = f"p{i+1}.html"

# SEÇİLDİYSE HTML GÖSTER
if st.session_state.selected:
    st.divider()
    st.subheader(f"📄 {st.session_state.selected}")

    base_dir = os.path.dirname(__file__)
    file_path = os.path.join(base_dir, "proposals", st.session_state.selected)

    try:
        with open(file_path, "r", encoding="utf-8") as f:
            html_content = f.read()

        st.components.v1.html(html_content, height=800, scrolling=True)

    except FileNotFoundError:
        st.error("HTML dosyası bulunamadı 😢")
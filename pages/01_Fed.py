import os
import streamlit as st
import streamlit.components.v1 as components

st.set_page_config(
    page_title="Fed Guide",
    page_icon="📊",
    layout="wide"
)

# ---------------------------- STOP Expanded -----------------
st.markdown(
    """
    <style>
        [data-testid="stSidebarNav"] {display: none;}
        section[data-testid="stSidebar"][aria-expanded="true"] {display: none;}
        div[data-testid="stSidebarCollapsedControl"] {display: none;}
    </style>
    """,
    unsafe_allow_html=True,
)

st.title("📊 Fed Balance Sheet Policy Guide")

# state
if "selected" not in st.session_state:
    st.session_state.selected = None

# proposal list
proposals = [f"Proposal {i}" for i in range(1, 16)]

# geri butonu
if st.session_state.selected is not None:
    if st.button("← Back to proposals"):
        st.session_state.selected = None
        st.rerun()

# grid görünümü
if st.session_state.selected is None:
    for row_start in range(0, len(proposals), 5):
        cols = st.columns(5)
        for j, proposal in enumerate(proposals[row_start:row_start+5]):
            idx = row_start + j + 1
            with cols[j]:
                st.markdown(
                    f"""
                    <div style="
                        border:1px solid #ddd;
                        border-radius:12px;
                        padding:20px;
                        height:110px;
                        background:#f8f9fb;
                        text-align:center;
                        display:flex;
                        align-items:center;
                        justify-content:center;
                        font-weight:600;
                        margin-bottom:8px;
                    ">
                        {proposal}
                    </div>
                    """,
                    unsafe_allow_html=True
                )
                if st.button(f"Open {idx}", key=f"open_{idx}"):
                    st.session_state.selected = f"p{idx}.html"
                    st.rerun()

# detay görünümü
else:
    base_dir = os.path.dirname(__file__)
    file_path = os.path.join(base_dir, "proposals", st.session_state.selected)

    st.subheader(st.session_state.selected.replace(".html", "").upper())

    if os.path.exists(file_path):
        with open(file_path, "r", encoding="utf-8") as f:
            html_content = f.read()

        components.html(html_content, height=1400, scrolling=True)
    else:
        st.error(f"{st.session_state.selected} bulunamadı.")
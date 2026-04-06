import streamlit as st
import streamlit.components.v1 as components
import os

# ---------------- CONFIG ----------------
st.set_page_config(
    page_title="Fed Balance Sheet Guide",
    page_icon="📊",
    layout="wide"
)

# Sidebar kapatma
st.markdown("""
<style>
[data-testid="stSidebarNav"] {display: none;}
section[data-testid="stSidebar"][aria-expanded="true"]{display: none;}
</style>
""", unsafe_allow_html=True)

# ---------------- STATE ----------------
if "selected" not in st.session_state:
    st.session_state.selected = None

# ---------------- PROPOSALS ----------------
proposals = [
    {"id": "p1", "title": "Policy Option 1"},
    {"id": "p2", "title": "Policy Option 2"},
    {"id": "p3", "title": "Policy Option 3"},
    {"id": "p4", "title": "Policy Option 4"},
    {"id": "p5", "title": "Policy Option 5"},
    {"id": "p6", "title": "Policy Option 6"},
    {"id": "p7", "title": "Policy Option 7"},
    {"id": "p8", "title": "Policy Option 8"},
    {"id": "p9", "title": "Policy Option 9"},
    {"id": "p10", "title": "Policy Option 10"},
    {"id": "p11", "title": "Policy Option 11"},
    {"id": "p12", "title": "Policy Option 12"},
    {"id": "p13", "title": "Policy Option 13"},
    {"id": "p14", "title": "Policy Option 14"},
    {"id": "p15", "title": "Policy Option 15"},
]

# ---------------- TITLE ----------------
st.title("A Companion Guide to Reducing the Fed Balance Sheet")

# ---------------- GRID VIEW ----------------
if st.session_state.selected is None:

    st.markdown("### Select a Policy Option")

    for i in range(0, len(proposals), 5):
        cols = st.columns(5)

        for col, proposal in zip(cols, proposals[i:i+5]):
            with col:
                st.markdown(f"""
                <div style="
                    border:1px solid #ddd;
                    border-radius:12px;
                    padding:20px;
                    height:130px;
                    background:#fafafa;
                    text-align:center;
                ">
                    <h4>{proposal['title']}</h4>
                </div>
                """, unsafe_allow_html=True)

                if st.button("Open", key=proposal["id"]):
                    st.session_state.selected = proposal["id"]
                    st.rerun()

# ---------------- DETAIL VIEW ----------------
else:
    selected = st.session_state.selected

    # geri butonu
    if st.button("← Back to proposals"):
        st.session_state.selected = None
        st.rerun()

    # HTML dosya yolu
    file_path = f"pages/proposals/{selected}.html"

    if os.path.exists(file_path):
        with open(file_path, "r", encoding="utf-8") as f:
            html_content = f.read()

        components.html(html_content, height=1200, scrolling=True)

    else:
        st.error(f"{selected}.html bulunamadı 😢")
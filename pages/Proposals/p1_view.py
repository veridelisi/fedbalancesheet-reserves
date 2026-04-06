import os
import streamlit as st
import streamlit.components.v1 as components

def render():
    left, center, right = st.columns([4, 2, 4])
    with center:
        if st.button("← Back to proposals", use_container_width=True):
            st.session_state.selected_proposal = None
            st.rerun()

    base_dir = os.path.dirname(__file__)
    file_path = os.path.join(base_dir, "p1.html")

    if os.path.exists(file_path):
        with open(file_path, "r", encoding="utf-8") as f:
            html_content = f.read()

        components.html(html_content, height=2200, scrolling=True)
    else:
        st.error(f"File not found: {file_path}")
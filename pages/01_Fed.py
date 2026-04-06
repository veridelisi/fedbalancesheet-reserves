import streamlit as st
from proposals.p1_view import render as render_p1

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

        .block-container {
            padding-top: 1.2rem;
            padding-left: 1.5rem;
            padding-right: 1.5rem;
            max-width: 100% !important;
        }
    </style>
    """,
    unsafe_allow_html=True,
)

# state
if "selected_proposal" not in st.session_state:
    st.session_state.selected_proposal = None

# proposal metadata
proposals = [
    {"id": "p1", "title": "Policy Option 1", "subtitle": "Recognize Discount Window Capacity in the LCR"},
    {"id": "p2", "title": "Policy Option 2", "subtitle": "Coming soon"},
    {"id": "p3", "title": "Policy Option 3", "subtitle": "Coming soon"},
    {"id": "p4", "title": "Policy Option 4", "subtitle": "Coming soon"},
    {"id": "p5", "title": "Policy Option 5", "subtitle": "Coming soon"},
    {"id": "p6", "title": "Policy Option 6", "subtitle": "Coming soon"},
    {"id": "p7", "title": "Policy Option 7", "subtitle": "Coming soon"},
    {"id": "p8", "title": "Policy Option 8", "subtitle": "Coming soon"},
    {"id": "p9", "title": "Policy Option 9", "subtitle": "Coming soon"},
    {"id": "p10", "title": "Policy Option 10", "subtitle": "Coming soon"},
    {"id": "p11", "title": "Policy Option 11", "subtitle": "Coming soon"},
    {"id": "p12", "title": "Policy Option 12", "subtitle": "Coming soon"},
    {"id": "p13", "title": "Policy Option 13", "subtitle": "Coming soon"},
    {"id": "p14", "title": "Policy Option 14", "subtitle": "Coming soon"},
    {"id": "p15", "title": "Policy Option 15", "subtitle": "Coming soon"},
]

# ---------------- MAIN VIEW ----------------
if st.session_state.selected_proposal is None:
    st.title("📊 Fed Balance Sheet Policy Guide")
    st.markdown("### Select a policy option")

    for row_start in range(0, len(proposals), 5):
        cols = st.columns(5)

        for j, proposal in enumerate(proposals[row_start:row_start + 5]):
            with cols[j]:
                st.markdown(
                    f"""
                    <div style="
                        border:1px solid #d9dee8;
                        border-radius:14px;
                        padding:18px 14px;
                        height:140px;
                        background:#f8f9fb;
                        display:flex;
                        flex-direction:column;
                        justify-content:center;
                        align-items:center;
                        text-align:center;
                        margin-bottom:8px;
                        box-shadow:0 2px 8px rgba(0,0,0,0.04);
                    ">
                        <div style="
                            font-size:16px;
                            font-weight:700;
                            color:#0f1e3c;
                            margin-bottom:8px;
                        ">
                            {proposal['title']}
                        </div>
                        <div style="
                            font-size:13px;
                            color:#5f6b7a;
                            line-height:1.4;
                        ">
                            {proposal['subtitle']}
                        </div>
                    </div>
                    """,
                    unsafe_allow_html=True,
                )

                button_label = f"Open {proposal['title'].split()[-1]}"
                if st.button(button_label, key=proposal["id"], use_container_width=True):
                    st.session_state.selected_proposal = proposal["id"]
                    st.rerun()

# ---------------- DETAIL VIEW ----------------
else:
    selected = st.session_state.selected_proposal

    if selected == "p1":
        render_p1()
    else:
        left, center, right = st.columns([4, 2, 4])
        with center:
            if st.button("← Back to proposals", use_container_width=True):
                st.session_state.selected_proposal = None
                st.rerun()

        st.warning(f"{selected.upper()} is not ready yet.")
import os
import streamlit as st
import streamlit.components.v1 as components

st.set_page_config(
    page_title="Fed Guide",
    page_icon="📊",
    layout="wide"
)

# ---------------------------- HIDE SIDEBAR / WIDEN PAGE ----------------------------
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

        .fed-card {
            border: 1px solid #d9dee8;
            border-radius: 16px;
            padding: 18px 14px;
            height: 170px;
            background: linear-gradient(180deg, #fbfcfe 0%, #f4f7fb 100%);
            display: flex;
            flex-direction: column;
            justify-content: center;
            align-items: center;
            text-align: center;
            box-shadow: 0 4px 14px rgba(15, 30, 60, 0.06);
            margin-bottom: 8px;
        }

        .fed-card-title {
            font-size: 16px;
            font-weight: 700;
            color: #0f1e3c;
            margin-bottom: 10px;
            line-height: 1.3;
        }

        .fed-card-subtitle {
            font-size: 13px;
            color: #5f6b7a;
            line-height: 1.45;
        }

        .fed-top-note {
            font-size: 15px;
            color: #536173;
            margin-bottom: 20px;
        }
    </style>
    """,
    unsafe_allow_html=True,
)

# ---------------------------- SESSION STATE ----------------------------
if "selected_proposal" not in st.session_state:
    st.session_state.selected_proposal = None

# ---------------------------- PROPOSAL METADATA ----------------------------
proposals = [
    {
        "id": "p1",
        "title": "Policy Option 1",
        "subtitle": "Recognize Discount Window Capacity in the LCR"
    },
    {
        "id": "p2",
        "title": "Policy Option 2",
        "subtitle": "Proposal title coming soon"
    },
    {
        "id": "p3",
        "title": "Policy Option 3",
        "subtitle": "Proposal title coming soon"
    },
    {
        "id": "p4",
        "title": "Policy Option 4",
        "subtitle": "Revise Resolution Liquidity Requirements"
    },
    {
        "id": "p5",
        "title": "Policy Option 5",
        "subtitle": "Proposal title coming soon"
    },
    {
        "id": "p6",
        "title": "Policy Option 6",
        "subtitle": "Proposal title coming soon"
    },
    {
        "id": "p7",
        "title": "Policy Option 7",
        "subtitle": "Proposal title coming soon"
    },
    {
        "id": "p8",
        "title": "Policy Option 8",
        "subtitle": "Proposal title coming soon"
    },
    {
        "id": "p9",
        "title": "Policy Option 9",
        "subtitle": "Proposal title coming soon"
    },
    {
        "id": "p10",
        "title": "Policy Option 10",
        "subtitle": "Proposal title coming soon"
    },
    {
        "id": "p11",
        "title": "Policy Option 11",
        "subtitle": "Proposal title coming soon"
    },
    {
        "id": "p12",
        "title": "Policy Option 12",
        "subtitle": "Proposal title coming soon"
    },
    {
        "id": "p13",
        "title": "Policy Option 13",
        "subtitle": "Proposal title coming soon"
    },
    {
        "id": "p14",
        "title": "Policy Option 14",
        "subtitle": "Proposal title coming soon"
    },
    {
        "id": "p15",
        "title": "Policy Option 15",
        "subtitle": "Proposal title coming soon"
    },
]

# ---------------------------- MAIN GRID ----------------------------
if st.session_state.selected_proposal is None:
    st.title("📊 Fed Balance Sheet Policy Guide")
    st.markdown(
        "<div class='fed-top-note'>Select one of the policy options below to open the companion explainer.</div>",
        unsafe_allow_html=True,
    )

    for row_start in range(0, len(proposals), 5):
        cols = st.columns(5)

        for col, proposal in zip(cols, proposals[row_start:row_start + 5]):
            with col:
                st.markdown(
                    f"""
                    <div class="fed-card">
                        <div class="fed-card-title">{proposal['title']}</div>
                        <div class="fed-card-subtitle">{proposal['subtitle']}</div>
                    </div>
                    """,
                    unsafe_allow_html=True
                )

                if st.button(
                    f"Open {proposal['title'].split()[-1]}",
                    key=proposal["id"],
                    use_container_width=True
                ):
                    st.session_state.selected_proposal = proposal["id"]
                    st.rerun()

# ---------------------------- DETAIL VIEW ----------------------------
else:
    left, center, right = st.columns([4, 2, 4])
    with center:
        if st.button("← Back to proposals", use_container_width=True):
            st.session_state.selected_proposal = None
            st.rerun()

    selected = st.session_state.selected_proposal
    base_dir = os.path.dirname(__file__)
    file_path = os.path.join(base_dir, "Proposals", f"{selected}.html")

    if os.path.exists(file_path):
        with open(file_path, "r", encoding="utf-8") as f:
            html_content = f.read()

        components.html(html_content, height=2200, scrolling=True)
    else:
        st.warning(f"{selected.upper()} is not ready yet.")
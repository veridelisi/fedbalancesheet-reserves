import streamlit as st

st.set_page_config(page_title="Fed Guide", layout="wide")

st.title("📊 Fed Balance Sheet Policy Guide")

# 15 proposal
proposals = [f"Proposal {i}" for i in range(1, 16)]

# 3 sütunlu grid
cols = st.columns(3)

for i, proposal in enumerate(proposals):
    with cols[i % 3]:
        st.markdown(f"""
        <div style="
            padding:20px;
            margin:10px;
            border-radius:15px;
            background-color:#f5f5f5;
            box-shadow: 0 4px 10px rgba(0,0,0,0.1);
            text-align:center;
            font-weight:bold;
        ">
            {proposal}
        </div>
        """, unsafe_allow_html=True)
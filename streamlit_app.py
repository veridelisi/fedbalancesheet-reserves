import streamlit as st

st.set_page_config(page_title="Veridelisi • Analytics Portal", layout="wide")

st.markdown("""
    <style>
        [data-testid="stSidebarNav"] {display: none;}
        section[data-testid="stSidebar"][aria-expanded="true"]{display: none;}
    </style>
    """, unsafe_allow_html=True)


st.markdown(
    "<h1 style='text-align:center;'>📊 Veridelisi • Analytics Portal</h1>",
    unsafe_allow_html=True
)

# ————— Reusable project card —————
def project_card(title: str, tagline: str, description_md: str, page_path: str, image_path: str, link_label: str):
    with st.container(border=True):
        c1, c2 = st.columns([1, 2], vertical_alignment="center")
        with c1:
             st.image(image_path, use_column_width=True)  # <-- fix
        with c2:
            st.subheader(title)
            if tagline:
                st.caption(tagline)
            st.markdown(description_md)
            st.page_link(page_path, label=link_label)

          

# ————— 1. Proje: Fed Reserves —————
project_card(
    title="How Fed Assets and Liabilities Affect Bank Reserves",
    tagline="Federal Reserve H.4.1 weekly release • Drivers of reserves",
    description_md=(
        "This dashboard provides comprehensive tracking of the Fed's **H.4.1** weekly release, "
        "presenting both weekly and annual changes across key balance sheet components. "
        "Through detailed breakdowns and visual analysis, users can identify the primary drivers "
        "of reserve fluctuations and assess their impact on overall liquidity conditions."
    ),
    page_path="pages/01_Reserves.py",
    image_path="assets/thumbs/veridelisi_reserves_thumb.jpg",
    link_label="➡️ Reserves dashboard"
)

# ————— 2. Proje: Primary Dealer Repo —————
project_card(
    title="Primary Dealer Repo & Reverse Repo",
    tagline="NY Fed Primary Dealer Statistics • Primary Dealer's Net Position",
    description_md=(
        "This dashboard provides a concise snapshot across Repo and Reverse Repo segments" 
        "(uncleared/cleared bilateral, GCF, tri-party). Users can also view the net market position"
          " of primary dealers, enabling a clearer understanding of their role in short-term funding" 
          "dynamics."
        
    ),
    page_path="pages/01_Repo.py",
    image_path="assets/thumbs/dealer.png",
    link_label="➡️ Repo dashboard"
)

# ————— 3. Proje: TGA —————
project_card(
    title="Treasury General Account (TGA)  Cash Position Statement",
    tagline="Daily Treasury Statement (DTS) Operating Cash Balance • TGA Cash Position ",
    description_md=(
        "A comprehensive financial monitoring tool that tracks U.S. Treasury cash"
        " flows and account balances in real-time"
        "Monitor government liquidity, cash management operations, analyze trends and patterns in Treasury cash flows"
    ),
    page_path="pages/01_TGA.py",
    image_path="assets/thumbs/tga.png",
    link_label="➡️ TGA dashboard"
)
# ————— 4. Proje: Public Balance —————
project_card(
    title="Public Balance Position Statement",
    tagline="Daily Treasury Statement (DTS) Deposits and Withdrawals of Operating Cash • TGA Cash Position",
    description_md=(
        "Tracks the **Public Balance** with daily flows and levels, offering quick "
        "TGA Flows (Taxes, Expenditures, New Debt, Debt Redemptions). "
        "Understand Public Balance from daily Taxes, Expenditures, New Debt, Debt Redemptions flows"
    ),
    page_path="pages/01_PublicBalance.py",
    image_path="assets/thumbs/public_balance.png",
    link_label="➡️ Public Balance dashboard"
)


# project_card("Project 3", "Tagline", "Açıklama...", "pages/03_Another.py", "assets/thumbs/another2.jpg")

st.markdown(
    
    "<div style='text-align:center;opacity:0.8'>"
    "Engin Yılmaz • September 2025"
    "</div>",
    unsafe_allow_html=True
)

    

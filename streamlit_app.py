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
    title="Primary Dealer's Repo & Reverse Repo",
    tagline="NY Fed Primary Dealer Statistics • Primary Dealer's Net Position",
    description_md=(
        "This dashboard provides a concise snapshot across Repo and Reverse Repo segments" 
        "(uncleared/cleared bilateral, GCF, tri-party). Users can also view the net market position"
          " of primary dealers, enabling a clearer understanding of their role in short-term funding" 
          " dynamics."
        
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
        "This dashboard tracks daily changes in the Treasury General Account (TGA). "
        "It also presents an annual TGA trend chart for longer-term perspective."
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
        "It decomposes daily inflows and outflows—tax receipts, expenditures, new issuance, and redemptions. "
        "It monitors Daily Top-10 categories in tax and expenditure categories."
    ),
    page_path="pages/01_PublicBalance.py",
    image_path="assets/thumbs/public_balance.png",
    link_label="➡️ Public Balance dashboard"
)

# 5) Money Markets Reference Rates
project_card(
    title="Money Markets Reference Rates",
    tagline="NY Fed Reference Rates • EFFR, OBFR, SOFR, BGCR, TGCR",
    description_md=(
        "Latest levels and historical charts. 7-day and YTD views with user-selectable series. "
        "SOFR-centered design for clean comparisons."
    ),
    page_path="pages/01_Interest.py",
    image_path="assets/thumbs/interest.png",
    link_label="➡️ Reference Rates dashboard"
)

# 6) Desk Operations
project_card(
    title="Desk Operations",
    tagline="Daily & weekly activities",
    description_md=(
        "Snapshot of the Desk’s day-to-day tools and flows — repo & reverse repo operations, "
        " Quick access to latest operations and history."
    ),
    page_path="pages/01_Desk.py",
    image_path="assets/thumbs/desk1.jpeg",
    link_label="➡️ Desk Operations dashboard"
)

# 7) Eurodollar Market
project_card(
    title="Eurodollar Market",
    tagline="BIS GLI • USD-only (Loans + Debt Securities)",
    description_md=(
        "Eurodollar Market Evolution (2000–latest): **Total Credit**, **Debt Securities**, and **Loans**, "
        "with **YoY** views; crisis shading (2007–09, 2020, and **Fed Tightening** from 2022-06); "
        
    ),
    page_path="pages/01_Eurodollar.py",
    image_path="assets/thumbs/bis.png",  # fallback: "assets/thumbs/bis.png"
    link_label="➡️ Eurodollar dashboard"
)



# project_card("Project 3", "Tagline", "Açıklama...", "pages/03_Another.py", "assets/thumbs/another2.jpg")

# --------------------------- Footer -------------------------------
st.markdown("---")
st.markdown(
    """
    <div style="text-align:center;color:#64748b;font-size:0.95rem;padding:20px 0;">
        <a href="https://veridelisi.substack.com/">Veri Delisi</a>🚀 <br>
        <em>Engin Yılmaz • Amherst • September 2025 </em>
    </div>
    """,
    unsafe_allow_html=True
)


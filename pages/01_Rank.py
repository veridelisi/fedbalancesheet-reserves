import streamlit as st
import requests
import csv
import pandas as pd
import plotly.graph_objects as go
from bs4 import BeautifulSoup
from datetime import datetime
from pathlib import Path

# ------------------------------ Page Config ------------------------------
st.set_page_config(
    page_title="Amazon Rank Tracker",
    page_icon="📈",
    layout="wide"
)

st.markdown("""
<style>
    [data-testid="stSidebarNav"] {display: none;}
    section[data-testid="stSidebar"][aria-expanded="true"]{display: none;}
</style>
""", unsafe_allow_html=True)

# ------------------------------ Settings ------------------------------
ASIN       = "B0G584KJ73"
URL        = f"https://www.amazon.com/dp/{ASIN}"
OUTPUT_CSV = Path(__file__).parent.parent / f"ranks_{ASIN}.csv"

HEADERS = {
    "User-Agent": "Mozilla/5.0 (X11; Linux x86_64) AppleWebKit/537.36 (KHTML, like Gecko) Chrome/44.0.2403.157 Safari/537.36",
    "Accept-Language": "en-US, en;q=0.5"
}

# ------------------------------ Fetch ------------------------------
def fetch_rank() -> dict:
    result = {
        "fetched_at": datetime.now().strftime("%Y-%m-%d %H:%M:%S"),
        "rank": None,
        "status": "ok",
    }

    try:
        webpage = requests.get(URL, headers=HEADERS, timeout=15)
    except Exception as e:
        result["status"] = f"error: {e}"
        return result

    if webpage.status_code != 200:
        result["status"] = f"http_{webpage.status_code}"
        return result

    if "captcha" in webpage.text.lower():
        result["status"] = "captcha"
        return result

    soup = BeautifulSoup(webpage.content, "lxml")

    # Exact selector from inspected HTML: subcategory ranks are in ul.zg_hrsr li
    try:
        for li in soup.select("ul.zg_hrsr li span.a-list-item"):
            text = li.get_text(" ", strip=True)
            if "Money" in text and "Monetary" in text:
                # text looks like: "#73 in Money & Monetary Policy (Books)"
                rank_str = text.split()[0].replace("#", "").replace(",", "")
                result["rank"] = int(rank_str)
                break
    except Exception as e:
        result["status"] = f"parse_error: {e}"
        return result

    if result["rank"] is None:
        result["status"] = "rank_not_found"

    return result

# ------------------------------ CSV Helpers ------------------------------
def append_csv(row: dict):
    file_exists = OUTPUT_CSV.exists()
    with open(OUTPUT_CSV, "a", newline="", encoding="utf-8") as f:
        writer = csv.DictWriter(f, fieldnames=["fetched_at", "rank", "status"])
        if not file_exists:
            writer.writeheader()
        writer.writerow(row)

def load_csv() -> pd.DataFrame:
    if not OUTPUT_CSV.exists():
        return pd.DataFrame(columns=["fetched_at", "rank", "status"])
    df = pd.read_csv(OUTPUT_CSV)
    df["fetched_at"] = pd.to_datetime(df["fetched_at"])
    df = df[df["rank"].notna()].copy()
    df["rank"] = df["rank"].astype(int)
    return df

# ------------------------------ Header ------------------------------
st.title("📈 Amazon Best Seller Rank Tracker")
st.markdown("**Money & Monetary Policy** category · ASIN: `B0G584KJ73`")
st.divider()

# ------------------------------ Button ------------------------------
col_btn, col_status = st.columns([1, 5])

with col_btn:
    fetch_clicked = st.button("🔄 Fetch Rank", use_container_width=True)

with col_status:
    if fetch_clicked:
        with st.spinner("Fetching from Amazon..."):
            data = fetch_rank()
            append_csv(data)
        if data["status"] == "ok":
            st.success(f"✅ Rank: **#{data['rank']}** · {data['fetched_at']}")
        elif data["status"] == "captcha":
            st.error("⚠️ CAPTCHA — try again in a few minutes.")
        else:
            st.error(f"❌ {data['status']}")

st.divider()

# ------------------------------ Load & Metrics ------------------------------
df = load_csv()

m1, m2, m3, m4 = st.columns(4)

current  = int(df["rank"].iloc[-1]) if len(df) > 0 else None
previous = int(df["rank"].iloc[-2]) if len(df) > 1 else None
best     = int(df["rank"].min())    if len(df) > 0 else None
worst    = int(df["rank"].max())    if len(df) > 0 else None
delta    = (current - previous)     if current and previous else None

m1.metric("Current Rank",  f"#{current}" if current else "—", delta=f"{delta:+d}" if delta else None, delta_color="inverse")
m2.metric("Best Rank",     f"#{best}"    if best    else "—")
m3.metric("Worst Rank",    f"#{worst}"   if worst   else "—")
m4.metric("Total Records", len(df))

st.divider()

# ------------------------------ Chart ------------------------------
st.subheader("📊 Rank History — Money & Monetary Policy")

if len(df) >= 2:
    fig = go.Figure()

    fig.add_hrect(
        y0=100, y1=worst + 20,
        fillcolor="rgba(255,100,100,0.05)",
        line_width=0,
        annotation_text="Below #100",
        annotation_position="top left",
        annotation_font_color="salmon",
        annotation_font_size=11,
    )

    fig.add_trace(go.Scatter(
        x=df["fetched_at"],
        y=df["rank"],
        mode="lines+markers",
        line=dict(color="#1f77b4", width=2),
        marker=dict(size=6, color="#1f77b4"),
        fill="tozeroy",
        fillcolor="rgba(31,119,180,0.07)",
        hovertemplate="<b>Rank #%{y}</b><br>%{x}<extra></extra>",
    ))

    best_row = df.loc[df["rank"].idxmin()]
    fig.add_annotation(
        x=best_row["fetched_at"],
        y=int(best_row["rank"]),
        text=f"🏆 Best: #{int(best_row['rank'])}",
        showarrow=True,
        arrowhead=2,
        arrowcolor="#2ca02c",
        font=dict(color="#2ca02c", size=12),
        bgcolor="rgba(255,255,255,0.8)",
        bordercolor="#2ca02c",
    )

    fig.update_layout(
        yaxis=dict(
            autorange="reversed",
            title="Rank (lower = better)",
            tickprefix="#",
            range=[worst + 30, 1],
        ),
        xaxis=dict(title=""),
        margin=dict(l=0, r=0, t=20, b=0),
        height=420,
        hovermode="x unified",
    )
    st.plotly_chart(fig, use_container_width=True)

elif len(df) == 1:
    st.info("Chart requires at least 2 data points. Press **Fetch Rank** again later.")
else:
    st.info("No data yet. Press **Fetch Rank** to get started.")

# ------------------------------ Methodology ------------------------------
st.markdown("### 📋 Methodology")
with st.expander("🔎 Click to expand methodology details", expanded=False):
    st.markdown(f"""
    - **Source:** Amazon product page · `ul.zg_hrsr li` selector
    - **ASIN:** `{ASIN}` · [View on Amazon]({URL})
    - **Category tracked:** Money & Monetary Policy
    - **Frequency:** Manual — press Fetch Rank button
    - **Storage:** CSV saved to project root → `ranks_{ASIN}.csv`
    - **Note:** Amazon may occasionally return a CAPTCHA. Wait a few minutes and try again.
    """)

# ------------------------------ Footer ------------------------------
st.markdown("---")
st.markdown(
    """
    <div style="text-align:center;color:#64748b;font-size:0.95rem;padding:20px 0;">
        <a href="https://veridelisi.substack.com/">Veri Delisi</a>🚀 <br>
        <em>Engin Yılmaz • Ankara • March 2026</em>
    </div>
    """,
    unsafe_allow_html=True
)
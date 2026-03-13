import streamlit as st
import requests
import pandas as pd
import plotly.graph_objects as go
from bs4 import BeautifulSoup
from datetime import datetime
from pathlib import Path
import re
import csv

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
    "User-Agent": (
        "Mozilla/5.0 (Windows NT 10.0; Win64; x64) "
        "AppleWebKit/537.36 (KHTML, like Gecko) "
        "Chrome/124.0.0.0 Safari/537.36"
    ),
    "Accept-Language": "en-US,en;q=0.9",
    "Accept": "text/html,application/xhtml+xml,application/xml;q=0.9,*/*;q=0.8",
}

# ------------------------------ Fetch ------------------------------
def fetch_rank() -> dict:
    result = {
        "fetched_at": datetime.now().strftime("%Y-%m-%d %H:%M:%S"),
        "rank": None,
        "status": "ok",
    }
    try:
        r = requests.get(URL, headers=HEADERS, timeout=15)
    except Exception as e:
        result["status"] = f"error: {e}"
        return result

    if r.status_code != 200:
        result["status"] = f"http_{r.status_code}"
        return result

    if "captcha" in r.text.lower():
        result["status"] = "captcha"
        return result

    soup = BeautifulSoup(r.text, "html.parser")
    bsr_text = ""

    for li in soup.select("#detailBulletsWrapper_feature_div li"):
        text = li.get_text(" ", strip=True)
        if "Best Sellers Rank" in text:
            bsr_text = text
            break

    if not bsr_text:
        for row in soup.select("#productDetails_db_sections tr, #prodDetails tr"):
            th, td = row.find("th"), row.find("td")
            if th and td and "Best Sellers Rank" in th.get_text():
                bsr_text = td.get_text(" ", strip=True)
                break

    if not bsr_text:
        result["status"] = "rank_not_found"
        return result

    m = re.search(r"#([\d,]+)\s+in Money & Monetary Policy", bsr_text)
    if m:
        result["rank"] = int(m.group(1).replace(",", ""))
    else:
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

# ------------------------------ Fetch Button ------------------------------
col_btn, col_status = st.columns([1, 5])

with col_btn:
    fetch_clicked = st.button("🔄 Fetch Rank", use_container_width=True)

with col_status:
    if fetch_clicked:
        with st.spinner("Fetching from Amazon..."):
            result = fetch_rank()
            append_csv(result)
        if result["status"] == "ok":
            st.success(f"✅ Rank fetched: **#{result['rank']}** at {result['fetched_at']}")
        elif result["status"] == "captcha":
            st.error("⚠️ Amazon returned a CAPTCHA. Try again in a few minutes.")
        else:
            st.error(f"❌ {result['status']}")

st.divider()

# ------------------------------ Load Data ------------------------------
df = load_csv()

# ------------------------------ Metrics ------------------------------
m1, m2, m3, m4 = st.columns(4)

current  = int(df["rank"].iloc[-1]) if len(df) > 0 else None
previous = int(df["rank"].iloc[-2]) if len(df) > 1 else None
best     = int(df["rank"].min())    if len(df) > 0 else None
worst    = int(df["rank"].max())    if len(df) > 0 else None
delta    = (current - previous)     if current and previous else None

m1.metric("Current Rank",  f"#{current}"  if current else "—", delta=f"{delta:+d}" if delta else None, delta_color="inverse")
m2.metric("Best Rank",     f"#{best}"     if best    else "—")
m3.metric("Worst Rank",    f"#{worst}"    if worst   else "—")
m4.metric("Total Records", len(df))

st.divider()

# ------------------------------ Chart ------------------------------
st.subheader("📊 Rank History")

if len(df) >= 2:
    fig = go.Figure()

    # Red shaded zone below rank 100
    fig.add_hrect(
        y0=100, y1=df["rank"].max() + 20,
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

    # Best rank annotation
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
            range=[df["rank"].max() + 30, 1],
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
    - **Source:** Amazon product page scraped via `requests` + `BeautifulSoup`
    - **ASIN:** `{ASIN}` · [View on Amazon]({URL})
    - **Category tracked:** Money & Monetary Policy
    - **Frequency:** Manual — press the Fetch Rank button to update
    - **Storage:** CSV saved to project root → `ranks_{ASIN}.csv`
    - **Rank range:** Can swing from top 10 to ~300+, chart scaled accordingly
    - **Note:** Amazon may occasionally return a CAPTCHA. If so, wait a few minutes and try again.
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
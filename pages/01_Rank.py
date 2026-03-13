import streamlit as st
import requests
import pandas as pd
import plotly.graph_objects as go
from bs4 import BeautifulSoup
from datetime import datetime
from pathlib import Path
import re
import csv
import time
import threading

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
CSV_DIR    = Path(__file__).parent.parent   # project root
OUTPUT_CSV = CSV_DIR / f"ranks_{ASIN}.csv"
INTERVAL_S = 3600

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

# ------------------------------ Background Tracker ------------------------------
def tracker_loop():
    while st.session_state.get("tracking", False):
        result = fetch_rank()
        append_csv(result)
        st.session_state["last_result"] = result
        st.session_state["last_fetch"]  = datetime.now().strftime("%H:%M:%S")
        time.sleep(INTERVAL_S)

# ------------------------------ Session State ------------------------------
if "tracking"    not in st.session_state: st.session_state["tracking"]    = False
if "last_result" not in st.session_state: st.session_state["last_result"] = None
if "last_fetch"  not in st.session_state: st.session_state["last_fetch"]  = "—"

# ------------------------------ Header ------------------------------
st.title("📈 Amazon Best Seller Rank Tracker")
st.markdown(
    f"Hourly tracking of **Money & Monetary Policy** category rank · "
    f"ASIN: `{ASIN}` · CSV saved to project root"
)
st.divider()

# ------------------------------ Controls ------------------------------
col_a, col_b, col_c = st.columns([1, 1, 6])

with col_a:
    if not st.session_state["tracking"]:
        if st.button("▶ Start", use_container_width=True):
            st.session_state["tracking"] = True
            threading.Thread(target=tracker_loop, daemon=True).start()
            st.rerun()
    else:
        if st.button("⏹ Stop", use_container_width=True):
            st.session_state["tracking"] = False
            st.rerun()

with col_b:
    if st.button("🔄 Fetch Now", use_container_width=True):
        with st.spinner("Fetching..."):
            result = fetch_rank()
            append_csv(result)
            st.session_state["last_result"] = result
            st.session_state["last_fetch"]  = datetime.now().strftime("%H:%M:%S")
        st.rerun()

with col_c:
    status_text = "🟢 Tracking active" if st.session_state["tracking"] else "⚪ Tracking stopped"
    last_result = st.session_state["last_result"]
    fetch_status = last_result["status"] if last_result else "—"
    st.markdown(
        f"<p style='margin-top:8px;color:gray;font-size:14px'>"
        f"{status_text} &nbsp;·&nbsp; Last fetch: {st.session_state['last_fetch']} "
        f"&nbsp;·&nbsp; Status: <code>{fetch_status}</code></p>",
        unsafe_allow_html=True
    )

st.divider()

# ------------------------------ Metrics ------------------------------
df = load_csv()

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

    # Shaded band: highlight when rank > 100 (big swings down to ~300)
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
    if best:
        best_row = df.loc[df["rank"].idxmin()]
        fig.add_annotation(
            x=best_row["fetched_at"],
            y=best,
            text=f"🏆 Best: #{best}",
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
            # ensure axis covers full swing range
            range=[max(df["rank"].max() + 30, worst + 30 if worst else 350), 1],
        ),
        xaxis=dict(title=""),
        margin=dict(l=0, r=0, t=20, b=0),
        height=420,
        hovermode="x unified",
    )
    st.plotly_chart(fig, use_container_width=True)

elif len(df) == 1:
    st.info("Chart requires at least 2 data points. Wait one hour or press **Fetch Now** again.")
else:
    st.info("No data yet. Press **Fetch Now** to collect the first data point.")

# ------------------------------ Methodology ------------------------------
st.markdown("### 📋 Methodology")
with st.expander("🔎 Click to expand methodology details", expanded=False):
    st.markdown(f"""
    - **Source:** Amazon product page scraped via `requests` + `BeautifulSoup`
    - **ASIN:** `{ASIN}` · [View on Amazon]({URL})
    - **Category tracked:** Money & Monetary Policy
    - **Frequency:** Every hour (background thread)
    - **Storage:** CSV file saved to project root → `ranks_{ASIN}.csv`
    - **Rank range:** Can swing from top 10 to ~300+, chart is scaled accordingly
    - **Note:** Amazon may occasionally return a CAPTCHA. If status shows `captcha`, the row is saved but rank will be empty. Retry will resume automatically next hour.
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
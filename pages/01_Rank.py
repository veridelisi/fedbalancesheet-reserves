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

# ── Page config ───────────────────────────────────────────────────────────────
st.set_page_config(
    page_title="Amazon Rank Tracker",
    page_icon="📈",
    layout="wide"
)

# ── Hide sidebar ──────────────────────────────────────────────────────────────
st.markdown("""
<style>
    [data-testid="stSidebarNav"] {display: none;}
    section[data-testid="stSidebar"][aria-expanded="true"]{display: none;}
</style>
""", unsafe_allow_html=True)

# ── Settings ──────────────────────────────────────────────────────────────────
ASIN       = "B0G584KJ73"
URL        = f"https://www.amazon.com/dp/{ASIN}"
OUTPUT_CSV = f"ranks_{ASIN}.csv"
INTERVAL_S = 3600

HEADERS = {
    "User-Agent": "Mozilla/5.0 (Windows NT 10.0; Win64; x64) "
                  "AppleWebKit/537.36 (KHTML, like Gecko) "
                  "Chrome/124.0.0.0 Safari/537.36",
    "Accept-Language": "en-US,en;q=0.9",
    "Accept": "text/html,application/xhtml+xml,application/xml;q=0.9,*/*;q=0.8",
}

# ── Fetch ─────────────────────────────────────────────────────────────────────
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

# ── CSV helpers ───────────────────────────────────────────────────────────────
def append_csv(row: dict):
    file_exists = Path(OUTPUT_CSV).exists()
    with open(OUTPUT_CSV, "a", newline="", encoding="utf-8") as f:
        writer = csv.DictWriter(f, fieldnames=["fetched_at", "rank", "status"])
        if not file_exists:
            writer.writeheader()
        writer.writerow(row)

def load_csv() -> pd.DataFrame:
    if not Path(OUTPUT_CSV).exists():
        return pd.DataFrame(columns=["fetched_at", "rank", "status"])
    df = pd.read_csv(OUTPUT_CSV)
    df["fetched_at"] = pd.to_datetime(df["fetched_at"])
    df = df[df["rank"].notna()].copy()
    df["rank"] = df["rank"].astype(int)
    return df

# ── Background tracker ────────────────────────────────────────────────────────
def tracker_loop():
    while st.session_state.get("tracking", False):
        result = fetch_rank()
        append_csv(result)
        st.session_state["last_result"] = result
        st.session_state["last_fetch"]  = datetime.now().strftime("%H:%M:%S")
        time.sleep(INTERVAL_S)

# ── Session state ─────────────────────────────────────────────────────────────
if "tracking"    not in st.session_state: st.session_state["tracking"]    = False
if "last_result" not in st.session_state: st.session_state["last_result"] = None
if "last_fetch"  not in st.session_state: st.session_state["last_fetch"]  = "—"

# ── Header ────────────────────────────────────────────────────────────────────
st.title("📈 Amazon Rank Tracker")
st.caption(f"ASIN: `{ASIN}` · Money & Monetary Policy · Saatlik takip")
st.divider()

# ── Controls ──────────────────────────────────────────────────────────────────
col_a, col_b, col_c = st.columns([1, 1, 6])

with col_a:
    if not st.session_state["tracking"]:
        if st.button("▶ Başlat", use_container_width=True):
            st.session_state["tracking"] = True
            t = threading.Thread(target=tracker_loop, daemon=True)
            t.start()
            st.rerun()
    else:
        if st.button("⏹ Durdur", use_container_width=True):
            st.session_state["tracking"] = False
            st.rerun()

with col_b:
    if st.button("🔄 Şimdi Çek", use_container_width=True):
        with st.spinner("Çekiliyor..."):
            result = fetch_rank()
            append_csv(result)
            st.session_state["last_result"] = result
            st.session_state["last_fetch"]  = datetime.now().strftime("%H:%M:%S")
        st.rerun()

with col_c:
    status_text = "🟢 Takip aktif" if st.session_state["tracking"] else "⚪ Takip durduruldu"
    st.markdown(f"<p style='margin-top:8px;color:gray;font-size:14px'>{status_text} &nbsp;·&nbsp; Son çekim: {st.session_state['last_fetch']}</p>", unsafe_allow_html=True)

st.divider()

# ── Load data ─────────────────────────────────────────────────────────────────
df = load_csv()

# ── Metrics ───────────────────────────────────────────────────────────────────
m1, m2, m3, m4 = st.columns(4)

current  = int(df["rank"].iloc[-1])  if len(df) > 0 else None
previous = int(df["rank"].iloc[-2])  if len(df) > 1 else None
best     = int(df["rank"].min())     if len(df) > 0 else None
worst    = int(df["rank"].max())     if len(df) > 0 else None
delta    = (current - previous)      if current and previous else None

m1.metric("Güncel Rank",  f"#{current}"  if current else "—", delta=f"{delta:+d}" if delta else None, delta_color="inverse")
m2.metric("En İyi Rank",  f"#{best}"     if best    else "—")
m3.metric("En Kötü Rank", f"#{worst}"    if worst   else "—")
m4.metric("Toplam Kayıt", len(df))

st.divider()

# ── Chart ─────────────────────────────────────────────────────────────────────
st.subheader("Rank Geçmişi")

if len(df) >= 2:
    fig = go.Figure()
    fig.add_trace(go.Scatter(
        x=df["fetched_at"],
        y=df["rank"],
        mode="lines+markers",
        line=dict(color="#1f77b4", width=2),
        marker=dict(size=6),
        fill="tozeroy",
        fillcolor="rgba(31,119,180,0.08)",
        hovertemplate="<b>#%{y}</b><br>%{x}<extra></extra>",
    ))
    fig.update_layout(
        yaxis=dict(autorange="reversed", title="Rank (düşük = iyi)", tickprefix="#"),
        xaxis=dict(title=""),
        margin=dict(l=0, r=0, t=10, b=0),
        height=350,
        hovermode="x unified",
    )
    st.plotly_chart(fig, use_container_width=True)
elif len(df) == 1:
    st.info("Grafik için en az 2 veri noktası gerekiyor. Bir saat bekle veya tekrar 'Şimdi Çek'e bas.")
else:
    st.info("Henüz veri yok. **Şimdi Çek** butonuna bas.")

st.divider()

# ── Table + download ─────────────────────────────────────────────────────────
st.subheader("Veri Tablosu")

if len(df) > 0:
    display_df = (
        df[["fetched_at", "rank", "status"]]
        .sort_values("fetched_at", ascending=False)
        .reset_index(drop=True)
    )
    display_df.columns = ["Tarih / Saat", "Rank", "Durum"]
    st.dataframe(display_df, use_container_width=True, height=300)

    st.download_button(
        label="⬇ CSV İndir",
        data=df.to_csv(index=False).encode("utf-8"),
        file_name=OUTPUT_CSV,
        mime="text/csv",
    )
else:
    st.info("Henüz veri yok.")

# -----------------------------------------------------------------------------
# OFR Repo Dashboard — 3 market in one chart (Triparty, DVP, GCF) [MULTIFULL]
# -----------------------------------------------------------------------------
import streamlit as st
import pandas as pd
import numpy as np
import requests
import altair as alt
import datetime as dt

# ---------------------------- Page config -----------------------------
st.set_page_config(page_title="Repo Dashboard", layout="wide")

# ---------------------------- Top nav (your template) -----------------
cols = st.columns(8)
with cols[0]:
    st.page_link("streamlit_app.py", label="🏠 Home")
with cols[1]:
    st.page_link("pages/01_Reserves.py", label="🌍 Reserves")
with cols[2]:
    st.page_link("pages/01_Repo.py", label="♻️ Repo")
with cols[3]:
    st.page_link("pages/01_TGA.py", label="🌐 TGA")
with cols[4]:
    st.page_link("pages/01_PublicBalance.py", label="💹 Public Balance")
with cols[5]:
    st.page_link("pages/01_Interest.py", label="✈️ Reference Rates")
with cols[6]:
    st.page_link("pages/01_Desk.py", label="📡 Desk")
with cols[7]:
    st.page_link("pages/01_Eurodollar.py", label="💡 Eurodollar")

st.markdown("""
<style>
    [data-testid="stSidebarNav"] {display: none;}
    section[data-testid="stSidebar"][aria-expanded="true"]{display: none;}
</style>
""", unsafe_allow_html=True)

# ---------------------------- OFR config ------------------------------
BASE = "https://data.financialresearch.gov/v1"

SERIES = {
    "Triparty": "REPO-TRI_TV_TOT-P",
    "DVP":      "REPO-DVP_OV_TOT-P",
    "GCF":      "REPO-GCF_TV_TOT-P",
}

def _pick_subkey(timeseries_dict: dict) -> str:
    # OFR multifull genelde tek anahtar döndürür: "aggregation" vb.
    return next(iter(timeseries_dict.keys()))

def compute_dates_for_zoom(zoom: str) -> tuple[str, str]:
    today = dt.date.today()
    end = today.strftime("%Y-%m-%d")

    if zoom == "1 week":
        start = (today - dt.timedelta(days=7)).strftime("%Y-%m-%d")
    elif zoom == "1 month":
        start = (today - dt.timedelta(days=30)).strftime("%Y-%m-%d")
    elif zoom == "6 months":
        start = (today - dt.timedelta(days=182)).strftime("%Y-%m-%d")
    elif zoom == "1 year":
        start = (today - dt.timedelta(days=365)).strftime("%Y-%m-%d")
    elif zoom == "YTD":
        start = dt.date(today.year, 1, 1).strftime("%Y-%m-%d")
    else:  # All
        start = "2016-01-01"
    return start, end

@st.cache_data(ttl=60*60, show_spinner=False)
def fetch_ofr_multifull(series_map: dict, start_date: str, end_date: str) -> pd.DataFrame:
    params = {
        "mnemonics": ",".join(series_map.values()),
        "start_date": start_date,
        "end_date": end_date,
    }
    resp = requests.get(f"{BASE}/series/multifull", params=params, timeout=60)
    resp.raise_for_status()
    raw = resp.json()

    frames = []
    for label, mnem in series_map.items():
        ts = raw[mnem]["timeseries"]
        sub = _pick_subkey(ts)
        tmp = pd.DataFrame(ts[sub], columns=["date", "value"])
        tmp["date"] = pd.to_datetime(tmp["date"])
        tmp["value"] = pd.to_numeric(tmp["value"], errors="coerce")
        tmp["market"] = label
        frames.append(tmp)

    df = pd.concat(frames, ignore_index=True).dropna(subset=["value"]).sort_values("date")
    return df

# ---------------------------- App -------------------------------------
st.title("♻️ OFR Repo Dashboard")

# Zoom bar (NO 10 years)
zoom = st.radio(
    "Zoom",
    options=["1 week", "1 month", "6 months", "1 year", "YTD", "All"],
    index=5,  # All default
    horizontal=True,
    label_visibility="collapsed",
)

START_DATE, END_DATE = compute_dates_for_zoom(zoom)

with st.spinner("OFR verileri çekiliyor (multifull)..."):
    plot_df = fetch_ofr_multifull(SERIES, START_DATE, END_DATE)

# ---------------------------- Chart (detail + brush) -------------------
base = alt.Chart(plot_df).encode(
    x=alt.X("date:T", title=""),
    y=alt.Y("value:Q", title="USD", axis=alt.Axis(format="~s")),
    color=alt.Color("market:N", title="Market"),
    tooltip=[
        alt.Tooltip("date:T", title="Date"),
        alt.Tooltip("market:N", title="Market"),
        alt.Tooltip("value:Q", title="Volume (USD)", format=","),
    ],
)


# ---------------------------- Chart + clickable labels ----------------------------

# Etiketleri grafiğin altına koy (legend yerine)
selected_markets = st.multiselect(
    label="",
    options=["GCF", "Triparty", "DVP"],
    default=["GCF", "Triparty", "DVP"],
    help="Aşağıdan seç, grafikte sadece seçtiklerin görünsün.",
)

# Eğer hiçbir şey seçilmezse grafiği boş bırakmayalım: hepsini geri getir
if not selected_markets:
    selected_markets = ["GCF", "Triparty", "DVP"]

filtered_df = plot_df[plot_df["market"].isin(selected_markets)].copy()

base = alt.Chart(filtered_df).encode(
    x=alt.X("date:T", title=""),
    y=alt.Y("value:Q", title="USD", axis=alt.Axis(format="~s")),
    color=alt.Color("market:N", title=None, legend=None),  # legend kapalı (etiketler altta)
    tooltip=[
        alt.Tooltip("date:T", title="Date"),
        alt.Tooltip("market:N", title="Market"),
        alt.Tooltip("value:Q", title="Volume (USD)", format=","),
    ],
)

# Brush selection (overview controls detail) — aynı davranış
brush = alt.selection_interval(encodings=["x"])

detail = base.mark_line().transform_filter(brush).properties(height=380)

overview = (
    alt.Chart(filtered_df)
    .mark_area(opacity=0.25)
    .encode(
        x=alt.X("date:T", title=""),
        y=alt.Y("value:Q", title="", axis=alt.Axis(labels=False, ticks=False)),
        color=alt.Color("market:N", legend=None),
    )
    .add_params(brush)
    .properties(height=70)
)

st.altair_chart(
    alt.vconcat(detail, overview).resolve_scale(color="shared"),
    use_container_width=True
)


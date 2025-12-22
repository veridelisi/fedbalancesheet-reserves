# -----------------------------------------------------------------------------
# OFR Repo Dashboard — 3 market in one chart (Triparty, DVP, GCF)
# -----------------------------------------------------------------------------
import streamlit as st
import pandas as pd
import numpy as np
import requests
from io import StringIO
from datetime import datetime, timedelta
import altair as alt
import datetime as dt

BASE = "https://data.financialresearch.gov/v1"

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

# ---------------------------- Helpers --------------------------------
SERIES = {
    "Triparty (TV Total)": "REPO-TRI_TV_TOT-P",
    "DVP (OV Total)": "REPO-DVP_OV_TOT-P",
    "GCF (TV Total)": "REPO-GCF_TV_TOT-P",
}

@st.cache_data(ttl=60*60, show_spinner=False)
def fetch_ofr_series(series_id: str) -> pd.DataFrame:
    """
    Tries CSV first, then JSON fallback.
    Returns columns: date, value
    """
    # CSV attempt
    csv_url = f"{BASE}/series/{series_id}/observations?format=csv"
    r = requests.get(csv_url, timeout=30)
    if r.ok and ("date" in r.text.lower()) and ("," in r.text):
        df = pd.read_csv(StringIO(r.text))
    else:
        # JSON fallback
        json_url = f"{BASE}/series/{series_id}/observations"
        r2 = requests.get(json_url, timeout=30)
        r2.raise_for_status()
        j = r2.json()
        # common patterns
        if isinstance(j, dict) and "observations" in j:
            df = pd.DataFrame(j["observations"])
        elif isinstance(j, list):
            df = pd.DataFrame(j)
        else:
            df = pd.DataFrame([])

    # Normalize columns
    # OFR usually uses 'date' and 'value' (or 'observation_date', 'observation_value')
    col_map = {}
    for c in df.columns:
        lc = c.lower()
        if lc in ["date", "observation_date", "asofdate", "obs_date"]:
            col_map[c] = "date"
        if lc in ["value", "observation_value", "obs_value", "level"]:
            col_map[c] = "value"
    df = df.rename(columns=col_map)

    if "date" not in df.columns or "value" not in df.columns:
        raise ValueError(f"Unexpected OFR response shape for {series_id}: {df.columns.tolist()}")

    df["date"] = pd.to_datetime(df["date"])
    df["value"] = pd.to_numeric(df["value"], errors="coerce")
    df = df.dropna(subset=["date", "value"]).sort_values("date").reset_index(drop=True)
    return df[["date", "value"]]

def compute_start_date(preset: str, latest: pd.Timestamp) -> pd.Timestamp | None:
    if preset == "1 week":
        return latest - pd.Timedelta(days=7)
    if preset == "1 month":
        return latest - pd.Timedelta(days=30)
    if preset == "6 months":
        return latest - pd.Timedelta(days=182)
    if preset == "1 year":
        return latest - pd.Timedelta(days=365)
    if preset == "YTD":
        return pd.Timestamp(year=latest.year, month=1, day=1)
    if preset == "All":
        return None
    return None

# ---------------------------- Load data --------------------------------
st.title("♻️ OFR Repo Dashboard")

with st.spinner("OFR verileri çekiliyor..."):
    frames = []
    for label, sid in SERIES.items():
        dfi = fetch_ofr_series(sid).copy()
        dfi["market"] = label
        frames.append(dfi)
    data = pd.concat(frames, ignore_index=True)

latest = data["date"].max()

# ---------------------------- Zoom bar (NO 10 years) -------------------
zoom = st.radio(
    "Zoom",
    options=["1 week", "1 month", "6 months", "1 year", "YTD", "All"],
    index=3,
    horizontal=True,
    label_visibility="collapsed",
)

start_date = compute_start_date(zoom, latest)
plot_df = data if start_date is None else data[data["date"] >= start_date].copy()

# ---------------------------- Altair chart (detail + brush overview) ---
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

# Brush selection (overview controls detail)
brush = alt.selection_interval(encodings=["x"])

detail = (
    base.mark_line()
    .properties(height=380)
)

overview = (
    alt.Chart(plot_df)
    .mark_area(opacity=0.25)
    .encode(
        x=alt.X("date:T", title=""),
        y=alt.Y("value:Q", title="", axis=alt.Axis(labels=False, ticks=False)),
        color=alt.Color("market:N", legend=None),
    )
    .add_params(brush)
    .properties(height=70)
)

# Apply brush to detail (if user drags)
detail = detail.transform_filter(brush)

st.altair_chart(alt.vconcat(detail, overview).resolve_scale(color="shared"), use_container_width=True)

# ---------------------------- Optional: quick table + download ----------
with st.expander("📥 Data"):
    st.dataframe(plot_df.sort_values(["date", "market"]), use_container_width=True)
    csv = plot_df.to_csv(index=False).encode("utf-8")
    st.download_button("Download CSV", data=csv, file_name="ofr_repo_3markets.csv", mime="text/csv")

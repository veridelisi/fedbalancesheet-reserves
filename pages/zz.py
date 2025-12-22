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

# ---------------------------- Chart with bottom interactive legend (NO brush) ----------------------------

selection = alt.selection_point(
    fields=["market"],
    bind="legend"
)

chart = alt.Chart(plot_df).mark_line().encode(
    x=alt.X("date:T", title=""),
    y=alt.Y("value:Q", title="USD", axis=alt.Axis(format="~s")),
    color=alt.Color(
        "market:N",
        legend=alt.Legend(
            orient="bottom",
            direction="horizontal",
            title=None
        )
    ),
    opacity=alt.condition(selection, alt.value(1.0), alt.value(0.15)),
    tooltip=[
        alt.Tooltip("date:T", title="Date"),
        alt.Tooltip("market:N", title="Market"),
        alt.Tooltip("value:Q", title="Volume (USD)", format=","),
    ],
).add_params(selection).properties(height=380)

st.altair_chart(chart, use_container_width=True)

# ---------------------------- Tri-party: Tenor + Collateral (same row) ----------------------------

START_DATE = "2025-09-01"

TENOR_SERIES = {
    "Total":            "REPO-TRI_TV_TOT-P",
    "Overnight/Open":   "REPO-TRI_TV_OO-P",
    "Term 2–7 Days":    "REPO-TRI_TV_B27-P",
    "Term 8–30 Days":   "REPO-TRI_TV_B830-P",
    "Term >30 Days":    "REPO-TRI_TV_G30-P",
}

COLLATERAL_SERIES = {
    "U.S. Treasury":      "REPO-TRI_TV_T-P",
    "Agency & GSE":       "REPO-TRI_TV_AG-P",
    "Corporate Debt":     "REPO-TRI_TV_CORD-P",
    "Other Collateral":   "REPO-TRI_TV_O-P",
    "Total":              "REPO-TRI_TV_TOT-P",
}

def _pick_subkey(timeseries_dict: dict) -> str:
    return next(iter(timeseries_dict.keys()))

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
        tmp["series"] = label
        frames.append(tmp)

    df = pd.concat(frames, ignore_index=True).dropna(subset=["value"]).sort_values("date")
    return df

def latest_available_date(df: pd.DataFrame) -> pd.Timestamp:
    # "Total" varsa onu baz al; yoksa genel max
    if (df["series"] == "Total").any():
        return df.loc[df["series"] == "Total", "date"].max()
    return df["date"].max()

def make_interactive_line_chart(df: pd.DataFrame, title: str) -> alt.Chart:
    selection = alt.selection_point(fields=["series"], bind="legend")

    base = alt.Chart(df).encode(
        x=alt.X("date:T", title=""),
        y=alt.Y("value:Q", title="USD", axis=alt.Axis(format="~s")),
        color=alt.Color(
            "series:N",
            legend=alt.Legend(orient="bottom", direction="horizontal", title=None)
        ),
        opacity=alt.condition(selection, alt.value(1.0), alt.value(0.15)),
    )

    hover = alt.selection_point(
        fields=["date", "series"],
        nearest=True,
        on="mouseover",
        empty=False,
    )

    line = base.mark_line().add_params(selection)

    # tooltip yakalama alanı
    hitbox = base.mark_line(opacity=0, strokeWidth=4).add_params(hover)

    points = base.mark_circle(size=20).encode(
        opacity=alt.condition(hover, alt.value(1), alt.value(0)),
        tooltip=[
            alt.Tooltip("date:T", title="Date"),
            alt.Tooltip("series:N", title="Series"),
            alt.Tooltip("value:Q", title="Volume (USD)", format=","),
        ],
    )

    return alt.layer(line, hitbox, points).properties(height=360, title=alt.Title(title, anchor='middle'))

# --- End date: ulaşılabilen en son veri olsun ---
today = dt.date.today().strftime("%Y-%m-%d")

with st.spinner("Tri-party tenor & collateral verileri çekiliyor..."):
    tenor_df_raw = fetch_ofr_multifull(TENOR_SERIES, START_DATE, today)
    collateral_df_raw = fetch_ofr_multifull(COLLATERAL_SERIES, START_DATE, today)

tenor_end = latest_available_date(tenor_df_raw)
coll_end = latest_available_date(collateral_df_raw)

# Ortak bir end date ile hizalayalım: ikisinin de erişebildiği en son ortak gün
end_date_final = min(tenor_end, coll_end)

tenor_df = tenor_df_raw[tenor_df_raw["date"] <= end_date_final].copy()
collateral_df = collateral_df_raw[collateral_df_raw["date"] <= end_date_final].copy()

st.caption(f"Tri-party date range: {pd.to_datetime(START_DATE).date()} → {end_date_final.date()}")

c1, c2 = st.columns(2)

with c1:
    st.altair_chart(
        make_interactive_line_chart(tenor_df, "Tri-Party Tenor"),
        use_container_width=True
    )

with c2:
    st.altair_chart(
        make_interactive_line_chart(collateral_df, "Tri-Party Collateral"),
        use_container_width=True
    )




# ---------------------------- DVP: Tenor + Collateral (same row) ----------------------------

START_DATE = "2025-09-01"

TENOR_SERIES = {
    "Total":            "REPO-DVP_TV_TOT-P",
    "Overnight/Open":   "REPO-DVP_TV_OO-P",
    "Term 2–7 Days":    "REPO-DVP_TV_B27-P",
    "Term 8–30 Days":   "REPO-DVP_TV_B830-P",
    "Term >30 Days":    "REPO-DVP_TV_G30-P",
}

COLLATERAL_SERIES = {
    "U.S. Treasury":      "REPO-DVP_TV_T-P",
    "Agency & GSE":       "REPO-DVP_TV_AG-P",
    "Corporate Debt":     "REPO-DVP_TV_CORD-P",
    "Other Collateral":   "REPO-DVP_TV_O-P",
    "Total":              "REPO-DVP_TV_TOT-P",
}


def _pick_subkey(timeseries_dict: dict) -> str:
    return next(iter(timeseries_dict.keys()))

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
        tmp["series"] = label
        frames.append(tmp)

    df = pd.concat(frames, ignore_index=True).dropna(subset=["value"]).sort_values("date")
    return df

def latest_available_date(df: pd.DataFrame) -> pd.Timestamp:
    # "Total" varsa onu baz al; yoksa genel max
    if (df["series"] == "Total").any():
        return df.loc[df["series"] == "Total", "date"].max()
    return df["date"].max()

def make_interactive_line_chart(df: pd.DataFrame, title: str) -> alt.Chart:
    selection = alt.selection_point(fields=["series"], bind="legend")

    base = alt.Chart(df).encode(
        x=alt.X("date:T", title=""),
        y=alt.Y("value:Q", title="USD", axis=alt.Axis(format="~s")),
        color=alt.Color(
            "series:N",
            legend=alt.Legend(orient="bottom", direction="horizontal", title=None)
        ),
        opacity=alt.condition(selection, alt.value(1.0), alt.value(0.15)),
    )

    hover = alt.selection_point(
        fields=["date", "series"],
        nearest=True,
        on="mouseover",
        empty=False,
    )

    line = base.mark_line().add_params(selection)

    # tooltip yakalama alanı
    hitbox = base.mark_line(opacity=0, strokeWidth=4).add_params(hover)

    points = base.mark_circle(size=20).encode(
        opacity=alt.condition(hover, alt.value(1), alt.value(0)),
        tooltip=[
            alt.Tooltip("date:T", title="Date"),
            alt.Tooltip("series:N", title="Series"),
            alt.Tooltip("value:Q", title="Volume (USD)", format=","),
        ],
    )

    return alt.layer(line, hitbox, points).properties(height=360, title=alt.Title(title, anchor='middle'))

# --- End date: ulaşılabilen en son veri olsun ---
today = dt.date.today().strftime("%Y-%m-%d")

with st.spinner("Tri-party tenor & collateral verileri çekiliyor..."):
    tenor_df_raw = fetch_ofr_multifull(TENOR_SERIES, START_DATE, today)
    collateral_df_raw = fetch_ofr_multifull(COLLATERAL_SERIES, START_DATE, today)

tenor_end = latest_available_date(tenor_df_raw)
coll_end = latest_available_date(collateral_df_raw)

# Ortak bir end date ile hizalayalım: ikisinin de erişebildiği en son ortak gün
end_date_final = min(tenor_end, coll_end)

tenor_df = tenor_df_raw[tenor_df_raw["date"] <= end_date_final].copy()
collateral_df = collateral_df_raw[collateral_df_raw["date"] <= end_date_final].copy()

st.caption(f"Tri-party date range: {pd.to_datetime(START_DATE).date()} → {end_date_final.date()}")

c1, c2 = st.columns(2)

with c1:
    st.altair_chart(
        make_interactive_line_chart(tenor_df, "DVP Tenor"),
        use_container_width=True
    )

with c2:
    st.altair_chart(
        make_interactive_line_chart(collateral_df, "DVP Collateral"),
        use_container_width=True
    )

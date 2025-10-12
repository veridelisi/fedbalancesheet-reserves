import streamlit as st
import requests
import pandas as pd
import plotly.express as px
import plotly.graph_objects as go
from datetime import datetime, date
import numpy as np
import math
import json



# Page configuration
st.set_page_config(
    page_title="Fed Repo Operations Dashboard",
    page_icon="📊",
    layout="wide"
)

# --- Gezinme Barı (Yatay Menü, saf Streamlit) ---
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



# --- Sol menü sakla ---
st.markdown("""
    <style>
        [data-testid="stSidebarNav"] {display: none;}
        section[data-testid="stSidebar"][aria-expanded="true"]{display: none;}
    </style>
    """, unsafe_allow_html=True)

# -------------------------
# 0) Utilities
# -------------------------

API_BASE = "https://stats.bis.org/api/v1"   # BIS Data Portal API v1

def _q_to_period(dt: pd.Timestamp) -> str:
    # 2005Q1 tarzı başlıklar için
    return f"{dt.year}Q{((dt.month-1)//3)+1}"

@st.cache_data(ttl=86400)  # 1 gün
def bis_series(dataset: str, key: str, start: str | None, end: str | None) -> pd.DataFrame:
    """
    Generic BIS fetcher (JSON).
    dataset examples:
      - BIS/WS_DEBT_SEC2_PUB/1.0
      - BIS/WS_LBS_D_PUB/1.0
    key examples:
      - IDS: Q.MX.3P.1.1.C.A.F.USD.A.A.A.A.A.I
      - LBS cross-border: Q.S.C.G.USD.A.5J.A.5A.A.MX.N
      - LBS local FX:     Q.S.C.A.USD.F.5J.A.MX.A.5J.R
    """
    url = f"{API_BASE}/{dataset}/{key}"
    params = {"contentType": "json"}
    if start:
        params["startPeriod"] = start
    if end:
        params["endPeriod"] = end

    r = requests.get(url, params=params, timeout=30)
    r.raise_for_status()
    data = r.json()

    # JSON -> tidy
    # Expected shape: {"structure":..., "data":{"series":[{"observations":[...]}], "attributes":...}}
    try:
        obs = data["data"]["series"][0]["observations"]
        times = [pd.to_datetime(o["period"] + "-01") for o in obs]  # quarterly period-end
        vals = [float(o["value"]) if o["value"] is not None else None for o in obs]
        df = pd.DataFrame({"Time": times, "Val": vals}).sort_values("Time")
    except Exception:
        # Fallback for alternate shape
        rows = []
        for s in data.get("data", {}).get("series", []):
            for o in s.get("observations", []):
                rows.append((o.get("period"), o.get("value")))
        df = pd.DataFrame(rows, columns=["Time", "Val"])
        if not df.empty:
            df["Time"] = pd.to_datetime(df["Time"] + "-01")
            df = df.sort_values("Time")

    return df

# -------------------------
# 1) Country map & color map
# -------------------------

COUNTRIES = {
    "Mexico": "MX", "China": "CN", "Turkey": "TR", "SaudiArabia": "SA",
    "Indonesia": "ID", "Brazil": "BR", "Korea": "KR", "Chile": "CL",
    "India": "IN", "Argentina": "AR", "Taipei": "TW", "Russia": "RU",
    "SouthAfrica": "ZA", "Malaysia": "MY",
}

PALETTE = {
    "Mexico": "#e74c3c", "China": "#8e44ad", "Turkey": "#f39c12", "SaudiArabia": "#27ae60",
    "Indonesia": "#d35400", "Brazil": "#c0392b", "Korea": "#9b59b6", "Chile": "#16a085",
    "India": "#7f8c8d", "Argentina": "#1abc9c", "Taipei": "#2ecc71", "Russia": "#d35400",
    "SouthAfrica": "#95a5a6", "Malaysia": "#9b59b6", "Others": "#bdc3c7",
    # fixed series colors:
    "_IDS": "#c0392b", "_XBL": "#2980b9", "_LLFX": "#27ae60"
}

# -------------------------
# 2) Key builders for BIS
# -------------------------
# Not: Bu anahtarlar BIS portalındaki filtrelerin bire bir kod karşılığıdır.
# IDS (debt securities, residents, foreign currencies, USD, total maturity, total rates)
def ids_key(iso3: str) -> str:
    # format: Q.<CC>.3P.1.1.C.A.F.USD.A.A.A.A.A.I
    return f"Q.{iso3}.3P.1.1.C.A.F.USD.A.A.A.A.A.I"

# LBS cross-border claims (all reporting countries -> residents of <country>), USD,
# all instruments, amount outstanding, all sectors
def lbs_cross_border_key(iso3: str) -> str:
    # format: Q.S.C.G.USD.A.5J.A.5A.A.<CC>.N
    return f"Q.S.C.G.USD.A.5J.A.5A.A.{iso3}.N"

# LBS local claims (reporting country = <country>, position = Local [R]),
# currency type = foreign (ie currencies foreign to bank location country), USD
def lbs_local_fx_key(iso3: str) -> str:
    # format: Q.S.C.A.USD.F.5J.A.<CC>.A.5J.R
    return f"Q.S.C.A.USD.F.5J.A.{iso3}.A.5J.R"

@st.cache_data(ttl=86400)
def load_ids_usd(iso3: str, start: str | None, end: str | None) -> pd.DataFrame:
    df = bis_series("BIS/WS_DEBT_SEC2_PUB/1.0", ids_key(iso3), start, end)
    return df.rename(columns={"Val": "Debt"})

@st.cache_data(ttl=86400)
def load_lbs_xborder_usd(iso3: str, start: str | None, end: str | None) -> pd.DataFrame:
    df = bis_series("BIS/WS_LBS_D_PUB/1.0", lbs_cross_border_key(iso3), start, end)
    return df.rename(columns={"Val": "CrossBorder"})

@st.cache_data(ttl=86400)
def load_lbs_localfx_usd(iso3: str, start: str | None, end: str | None) -> pd.DataFrame:
    df = bis_series("BIS/WS_LBS_D_PUB/1.0", lbs_local_fx_key(iso3), start, end)
    return df.rename(columns={"Val": "LocalFX"})

# -------------------------
# 3) UI
# -------------------------

st.markdown("## Country decomposition — **Debt, Cross-border Loans, Local FX Loans**")

# Ülke seçimi: Legend benzeri yatay radio; Mexico default
cols = list(COUNTRIES.keys())
country = st.radio(
    "Select country", cols, index=cols.index("Mexico"),
    key="cd_country_radio", horizontal=True
)

# Opsiyonel dönem (sidebar) — key çakışmasın diye cd_* prefix
with st.sidebar:
    st.markdown("### Period")
    start_year = st.number_input("Start year", 2000, 2025, 2005, key="cd_start_year")
    end_year = st.number_input("End year", 2000, 2025, 2025, key="cd_end_year")
    start_period = f"{start_year}-01"   # BIS API 'startPeriod' (YYYY-MM style accepted by v1)
    end_period = f"{end_year}-12"

iso = COUNTRIES[country]

# -------------------------
# 4) Fetch & combine
# -------------------------
try:
    ids = load_ids_usd(iso, start_period, end_period)
    xbl = load_lbs_xborder_usd(iso, start_period, end_period)
    llf = load_lbs_localfx_usd(iso, start_period, end_period)

    # merge by Time
    df = ids.merge(xbl, on="Time", how="outer").merge(llf, on="Time", how="outer")
    df = df.sort_values("Time").reset_index(drop=True)

    # USD mn -> USD bn (BIS LBS/IDS units are usually millions)
    for c in ["Debt", "CrossBorder", "LocalFX"]:
        if c in df.columns:
            df[c] = pd.to_numeric(df[c], errors="coerce")
            df[c] = df[c] / 1000.0

    df["Total"] = df[["Debt", "CrossBorder", "LocalFX"]].sum(axis=1, min_count=1)

except requests.HTTPError as e:
    st.error("BIS API request failed. Please try again later.")
    st.stop()

if df.dropna(how="all", subset=["Debt", "CrossBorder", "LocalFX"]).empty:
    st.warning("No data returned for the selected period.")
    st.stop()

# -------------------------
# 5) Plots
# -------------------------
left, right = st.columns([0.68, 0.32], gap="large")

with left:
    fig = go.Figure()
    if "Debt" in df:
        fig.add_trace(go.Scatter(
            x=df["Time"], y=df["Debt"],
            name="Debt (IDS)", mode="lines", line=dict(color=PALETTE["_IDS"], width=2.2),
            hovertemplate="%{x|%Y-%m}: Debt $%{y:.1f}B<extra></extra>"
        ))
    if "CrossBorder" in df:
        fig.add_trace(go.Scatter(
            x=df["Time"], y=df["CrossBorder"],
            name="Cross-border loans (LBS)", mode="lines", line=dict(color=PALETTE["_XBL"], width=2.2),
            hovertemplate="%{x|%Y-%m}: Cross-border $%{y:.1f}B<extra></extra>"
        ))
    if "LocalFX" in df:
        fig.add_trace(go.Scatter(
            x=df["Time"], y=df["LocalFX"],
            name="Local FX loans (LBS)", mode="lines", line=dict(color=PALETTE["_LLFX"], width=2.2),
            hovertemplate="%{x|%Y-%m}: Local FX $%{y:.1f}B<extra></extra>"
        ))

    fig.update_layout(
        title=f"{country} — Debt, Cross-border, Local FX (USD bn)",
        height=460, legend=dict(orientation="h", yanchor="top", y=-0.2, xanchor="center", x=0.5),
        margin=dict(l=10, r=10, t=60, b=60),
    )
    fig.update_yaxes(title="USD bn", rangemode="tozero")
    st.plotly_chart(fig, use_container_width=True)

with right:
    # last common snapshot (hepsinde veri olan en son tarih)
    non_na = df.dropna(subset=["Debt", "CrossBorder", "LocalFX"], how="any").copy()
    if non_na.empty:
        st.info("No common snapshot where all three components are available.")
    else:
        snap = non_na.iloc[-1]
        snap_date = pd.to_datetime(snap["Time"])
        parts = {
            "Debt": float(snap["Debt"]),
            "Cross-border": float(snap["CrossBorder"]),
            "Local FX": float(snap["LocalFX"]),
        }
        total = sum(parts.values())
        shares = {k: (v / total * 100.0 if total > 0 else 0.0) for k, v in parts.items()}

        pie = go.Figure(go.Pie(
            labels=list(parts.keys()),
            values=list(parts.values()),
            hole=0.45,
            text=[f"{k}\n{shares[k]:.1f}%" for k in parts.keys()],
            textinfo="text",
            marker=dict(colors=[PALETTE["_IDS"], PALETTE["_XBL"], PALETTE["_LLFX"]]),
            hovertemplate="%{label}: $%{value:.1f}B<br>%{percent}<extra></extra>"
        ))
        pie.update_layout(
            title=f"Composition (as of {_q_to_period(snap_date)})",
            height=340, margin=dict(l=20, r=20, t=50, b=20),
            showlegend=False
        )
        st.plotly_chart(pie, use_container_width=True)

# -------------------------
# 6) Table (compact)
# -------------------------
st.markdown("#### Latest values")
latest = df.iloc[[-1]].copy()
latest["Period"] = latest["Time"].dt.to_period("Q").astype(str)
st.dataframe(
    latest[["Period", "Debt", "CrossBorder", "LocalFX", "Total"]]
          .rename(columns={"Period": "As of", "CrossBorder": "Cross-border", "LocalFX": "Local FX"})
          .style.format({"Debt": "{:.1f}", "Cross-border": "{:.1f}", "Local FX": "{:.1f}", "Total": "{:.1f}"}),
    hide_index=True,
    use_container_width=True
)
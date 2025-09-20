# streamlit_app.py
import math, re, requests
from datetime import timedelta, date
import pandas as pd
import numpy as np
import streamlit as st
from dateutil.relativedelta import relativedelta
import matplotlib.pyplot as plt
from matplotlib.ticker import FuncFormatter, AutoLocator

st.set_page_config(page_title="Veridelisi • Reserve Page", layout="wide")

# --- Top nav ---
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

# --- Hide sidebar + small CSS + badge helper ---
st.markdown("""
<style>
  [data-testid="stSidebarNav"]{display:none;}
  section[data-testid="stSidebar"][aria-expanded="true"]{display:none;}
  .vd-badge{
    display:inline-block;padding:3px 8px;border-radius:8px;
    font-size:0.75rem;font-weight:600;letter-spacing:.2px;
    color:#111827;background:#E5E7EB;border:1px solid #D1D5DB;
    margin-left:.5rem;vertical-align:middle;
  }
</style>
""", unsafe_allow_html=True)

def badge(text, bg="#E5E7EB", fg="#111827", br="#D1D5DB"):
    return f'<span class="vd-badge" style="background:{bg};color:{fg};border-color:{br};">{text}</span>'

# --- Secrets/env loader ---
def get_secret(keys, default=None, cast=None):
    if isinstance(keys, str):
        keys = [keys]
    for k in keys:
        try:
            if k in st.secrets:
                val = st.secrets[k]
                return cast(val) if (cast and val is not None) else val
        except Exception:
            pass
    try:
        for _, section in st.secrets.items():
            if isinstance(section, dict):
                for k in keys:
                    kl = k.lower()
                    if kl in section:
                        val = section[kl]
                        return cast(val) if (cast and val is not None) else val
    except Exception:
        pass
    import os
    for k in keys:
        val = os.environ.get(k)
        if val is not None:
            return cast(val) if cast else val
    return default

# --- FRED settings ---
API_KEY    = get_secret(["API_KEY", "FRED_API_KEY"])
BASE       = get_secret(["BASE", "FRED_BASE"], default="https://api.stlouisfed.org")
RELEASE_ID = get_secret(["RELEASE_ID", "FRED_RELEASE_ID"], default=20, cast=int)
ELEMENT_ID = get_secret(["ELEMENT_ID", "FRED_ELEMENT_ID"], default=1193943, cast=int)
if not API_KEY:
    st.error("API key not set. Settings → Secrets'e `API_KEY` (veya `FRED_API_KEY`) ekleyin.")
    st.stop()

# ---------- Page ----------
st.title("🏦 Federal Reserve H.4.1 — Assets & Liabilities (Reserves Impact)")
st.caption("Weekly change vs prior week, and Annual change vs fixed baseline 2025-01-01")

# ---------- Helpers ----------
def clean_num(x):
    if x is None: return math.nan
    s = str(x).strip().replace(",", "").replace("–", "-")
    try: return float(s)
    except: return math.nan

def normalize_name(s: str) -> str:
    return re.sub(r"\s+", " ", str(s).strip())

@st.cache_data(ttl=3600)
def get_latest_available_date(series_id: str) -> str | None:
    url = f"{BASE}/fred/series/observations"
    params = dict(series_id=series_id, api_key=API_KEY, file_type="json", limit=1, sort_order="desc")
    r = requests.get(url, params=params, timeout=30)
    r.raise_for_status()
    obs = r.json().get("observations", [])
    return obs[0]["date"] if obs else None

@st.cache_data(ttl=3600)
def get_table_values(observation_date: str) -> dict:
    url = f"{BASE}/fred/release/tables"
    params = {
        "api_key": API_KEY, "file_type": "json",
        "release_id": RELEASE_ID, "element_id": ELEMENT_ID,
        "include_observation_values": "true",
        "observation_date": observation_date,
    }
    r = requests.get(url, params=params, timeout=60)
    r.raise_for_status()
    js = r.json()
    out = {}
    elements = js.get("elements", {})
    elements = elements.values() if isinstance(elements, dict) else elements
    for el in elements:
        if el.get("type") == "series":
            out[normalize_name(el.get("name",""))] = clean_num(el.get("observation_value"))
    return out

def lookup(vals: dict, name: str, default=0.0):
    key = normalize_name(name)
    for k,v in vals.items():
        if normalize_name(k) == key:
            return v if pd.notna(v) else default
    for k,v in vals.items():
        if key in normalize_name(k):
            return v if pd.notna(v) else default
    return default

# ---------- Dates & baseline ----------
TARGET_SERIES_ID = "WSHOSHO"  # weekly Wednesday (H.4.1)
_latest = get_latest_available_date(TARGET_SERIES_ID) or "2025-09-03"
t       = pd.to_datetime(_latest).date()       # latest Wednesday
t_w     = t - timedelta(days=7)                # previous week
t_fixed = date(2025, 1, 1)                     # fixed baseline

# Header chip with latest date
c1, _ = st.columns([1, 3])
with c1:
    st.markdown(
        f"""
        <div style="
            display:inline-block; padding:10px 14px; border:1px solid #e5e7eb; 
            border-radius:10px; background:#fafafa;">
            <div style="font-size:0.95rem; color:#6b7280; margin-bottom:2px;">
                Latest Wednesday
            </div>
            <div style="font-size:1.15rem; font-weight:600; letter-spacing:0.2px;">
                {t.strftime('%d.%m.%Y')}
            </div>
        </div>
        """,
        unsafe_allow_html=True
    )

# ---------- Fetch ----------
with st.spinner("Fetching H.4.1 data..."):
    vals_t = get_table_values(t.isoformat())
    vals_w = get_table_values(t_w.isoformat())
    vals_y = get_table_values(t_fixed.isoformat())   # annual baseline fixed to 2025-01-01

# ---------- Calculations ----------
def net_sec(vdict):
    return (
        lookup(vdict, "Securities held outright")
        + lookup(vdict, "Unamortized premiums on securities held outright")
        + lookup(vdict, "Unamortized discounts on securities held outright")
    )

assets_map = {
    "Securities held outright": "Securities (net of prem./disc.)",
    "Repurchase agreements": "Repurchase agreements",
    "Loans": "Loans to depository institutions",
    "Net portfolio holdings of MS Facilities 2020 LLC (Main Street Lending Program)": "Net portfolio holdings of facilities",
    "Float": "Float",
    "Central bank liquidity swaps": "Central bank liquidity swaps",
    "Other Federal Reserve assets": "Other Federal Reserve assets",
    "Foreign currency denominated assets": "Foreign currency denominated assets",
    "Gold stock": "Gold stock",
    "Special drawing rights certificate account": "Special drawing rights certificate account",
    "Treasury currency outstanding": "Treasury currency outstanding",
}

asset_rows = []
for orig, clean in assets_map.items():
    if orig == "Securities held outright":
        vt, vw, vy = net_sec(vals_t), net_sec(vals_w), net_sec(vals_y)
    else:
        vt, vw, vy = lookup(vals_t, orig), lookup(vals_w, orig), lookup(vals_y, orig)
    weekly = vt - vw
    annual = vt - vy
    if abs(weekly) >= 50 or abs(annual) >= 100:  # thresholds in millions
        asset_rows.append({"name": clean, "weekly": weekly, "annual": annual})
df_assets = pd.DataFrame(asset_rows)

liab_map = {
    "Currency in circulation": "Currency in circulation",
    "Reverse repurchase agreements": "Reverse repos",
    "Foreign official and international accounts": "Foreign official",
    "Others": "Other deposits",
    "U.S. Treasury, General Account": "Treasury General Account",
    "Other liabilities and capital": "Other liabilities",
}

liab_rows = []
for orig, clean in liab_map.items():
    cur = lookup(vals_t, orig)
    wk  = lookup(vals_w, orig)
    yr  = lookup(vals_y, orig)
    weekly_change = cur - wk
    annual_change = cur - yr
    weekly_impact = -weekly_change
    annual_impact = -annual_change
    if abs(weekly_change) >= 50 or abs(annual_change) >= 100:
        liab_rows.append({
            "name": clean,
            "weekly_change": weekly_change,
            "annual_change": annual_change,
            "weekly_impact": weekly_impact,
            "annual_impact": annual_impact,
        })
df_liab = pd.DataFrame(liab_rows)

# ---------- Plot helpers (billions) ----------
def _fmtB(x, pos):
    return f"{x:,.1f}B" if abs(x) < 10 else f"{x:,.0f}B"
fmtB = FuncFormatter(_fmtB)

def plot_barh_billions(df, col, title, xlabel):
    if df.empty or df[col].abs().max() == 0:
        return
    dd = df.copy()
    dd['val_b'] = dd[col] / 1000.0
    dd = dd.sort_values('val_b')
    colors = ['#1f77b4' if x >= 0 else 'red' for x in dd['val_b']]

    fig, ax = plt.subplots(figsize=(12, max(4, 0.45*len(dd)+2)))
    ax.barh(dd['name'], dd['val_b'], color=colors, alpha=0.85)
    ax.set_title(title, fontweight='bold')
    ax.set_xlabel(xlabel)
    ax.grid(axis='x', alpha=0.3)
    ax.axvline(0, color='black', lw=1)
    max_val = max(abs(dd['val_b'].min()), abs(dd['val_b'].max()))
    ax.set_xlim(-max_val*1.2, max_val*1.2)
    ax.xaxis.set_major_locator(AutoLocator())
    ax.xaxis.set_major_formatter(fmtB)
    st.pyplot(fig, clear_figure=True)

# ---------- Layout (two rows with badges) ----------
# Row 1 — WEEKLY
st.markdown(
    f"### Charts {badge('WEEKLY', bg='#DCFCE7', fg='#065F46', br='#A7F3D0')}",
    unsafe_allow_html=True
)
row1_left, row1_right = st.columns(2, gap="large")
with row1_left:
    st.subheader("Assets — Weekly change (billions)")
    plot_barh_billions(
        df_assets, 'weekly',
        f"Weekly change ({t.strftime('%b %d, %Y')} vs {t_w.strftime('%b %d, %Y')})",
        "Change (billions of dollars)"
    )
with row1_right:
    st.subheader("Liabilities — Weekly reserve impact (billions)")
    plot_barh_billions(
        df_liab, 'weekly_impact',
        f"Weekly impact on reserves ({t.strftime('%b %d, %Y')} vs {t_w.strftime('%b %d, %Y')})",
        "Reserve impact (billions of dollars)"
    )

st.markdown("---")

# Row 2 — 2025-01-01 baseline
st.markdown(
    f"### Charts {badge('2025-01-01 BASELINE', bg='#DBEAFE', fg='#1E3A8A', br='#BFDBFE')}",
    unsafe_allow_html=True
)
row2_left, row2_right = st.columns(2, gap="large")
with row2_left:
    st.subheader("Assets — Annual change vs baseline (billions)")
    plot_barh_billions(
        df_assets, 'annual',
        f"Annual change vs baseline {t_fixed} ({t.strftime('%b %d, %Y')} vs {t_fixed.strftime('%b %d, %Y')})",
        "Change (billions of dollars)"
    )
with row2_right:
    st.subheader("Liabilities — Annual reserve impact (billions)")
    plot_barh_billions(
        df_liab, 'annual_impact',
        f"Annual impact vs baseline {t_fixed} ({t.strftime('%b %d, %Y')} vs {t_fixed.strftime('%b %d, %Y')})",
        "Reserve impact (billions of dollars)"
    )

# ---------- Tables & Net ----------
st.markdown("---")
st.subheader("Detailed breakdown (millions)")

if not df_assets.empty:
    st.write("**Assets**")
    sdata = df_assets.rename(columns={"name":"Asset Factor", "weekly":"Weekly ($M)", "annual":"Annual ($M)"})
    st.dataframe(sdata.reset_index(drop=True), use_container_width=True)

if not df_liab.empty:
    st.write("**Liabilities** (impact on reserves shown as negative for increases)")
    tdata = df_liab.rename(columns={
        "name":"Liability Factor",
        "weekly_change":"Weekly Change ($M)",
        "annual_change":"Annual Change ($M)",
        "weekly_impact":"Weekly Reserve Impact ($M)",
        "annual_impact":"Annual Reserve Impact ($M)",
    })
    st.dataframe(tdata.reset_index(drop=True), use_container_width=True)

assets_weekly = float(df_assets["weekly"].sum()) if not df_assets.empty else 0.0
assets_annual = float(df_assets["annual"].sum()) if not df_assets.empty else 0.0
liab_weekly   = float(df_liab["weekly_impact"].sum()) if not df_liab.empty else 0.0
liab_annual   = float(df_liab["annual_impact"].sum()) if not df_liab.empty else 0.0
net_weekly = assets_weekly + liab_weekly
net_annual = assets_annual + liab_annual

st.markdown("### 💼 Net Impact on Bank Reserves")
st.metric("Weekly Net Impact ($M)", f"{net_weekly:+,.0f}")
st.metric("Annual Net Impact ($M)", f"{net_annual:+,.0f}")

# ---------------------------- Methodology -------------------------------
st.markdown("### Methodology")
with st.expander("Click to expand methodology details"):
    st.markdown("""
**Data source:** Federal Reserve H.4.1 Statistical Release (FRED release/tables)

**Thresholds for display:** ±$50M (weekly), ±$100M (annual)

**Legend:** 🔵 Positive = increases; 🔴 Negative = decreases

**Securities calculation:** held outright + unamortized premiums + unamortized discounts

**Annual baseline:** fixed to **2025-01-01** (not YoY)
""")

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

# ---------- Raw values table (Latest, Week-ago, 2025-01-01) ----------
vals_2025 = get_table_values(t_fixed.isoformat())
all_series = sorted(set(vals_t.keys()) | set(vals_w.keys()) | set(vals_2025.keys()))
df_raw = pd.DataFrame([{
    "Series": s,
    f"Latest {t.isoformat()} ($M)": vals_t.get(s, math.nan),
    f"Week-ago {t_w.isoformat()} ($M)": vals_w.get(s, math.nan),
    "2025-01-01 ($M)": vals_2025.get(s, math.nan),
} for s in all_series])
st.markdown("---")
st.subheader("Raw H.4.1 values — latest, week-ago, and 2025-01-01 (millions)")
st.dataframe(df_raw.reset_index(drop=True), use_container_width=True)

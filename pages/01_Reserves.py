# streamlit_app.py
import math, re, requests
from datetime import timedelta
import pandas as pd
import numpy as np
import streamlit as st
from dateutil.relativedelta import relativedelta
import matplotlib.pyplot as plt
from matplotlib.ticker import FuncFormatter, AutoLocator



st.set_page_config(page_title="Veridelisi • Reserve Page", layout="wide")

# --- Gezinme Barı (Yatay Menü, Streamlit-native) ---
st.markdown("""
<div style="background:#f8f9fa;padding:10px 0 10px 0;margin-bottom:24px;border-radius:8px;display:flex;gap:32px;justify-content:center;">
""", unsafe_allow_html=True)

col1, col2, col3, col4, col5, col6, col7, col8 = st.columns([1,1,1,1,1,1,1,1])
with col1:
    st.page_link("streamlit_app.py", label="🏠 Home")
with col2:
    st.page_link("pages/01_Reserves.py", label="🌍 Reserves")
with col3:
    st.page_link("pages/01_Repo.py", label="♻️ Repo")
with col4:
    st.page_link("pages/01_TGA.py", label="🌐 TGA")
with col5:
    st.page_link("pages/01_PublicBalance.py", label="💹 Public Balance")
with col6:
    st.page_link("pages/01_Interest.py", label="✈️ Reference Rates")
with col7:
    st.page_link("pages/01_Desk.py", label="📡 Desk")
with col8:
    st.page_link("pages/01_Eurodollar.py", label="💡 Eurodollar")    

st.markdown("</div>", unsafe_allow_html=True)


# --- Sol menü sakla ---
st.markdown("""
    <style>
        [data-testid="stSidebarNav"] {display: none;}
        section[data-testid="stSidebar"][aria-expanded="true"]{display: none;}
    </style>
    """, unsafe_allow_html=True)



# --- Sol menü sakla ---
st.markdown("""
    <style>
        [data-testid="stSidebarNav"] {display: none;}
        section[data-testid="stSidebar"][aria-expanded="true"]{display: none;}
    </style>
    """, unsafe_allow_html=True)

# --- Secrets/env loader: st.secrets -> section -> environment ---
def get_secret(keys, default=None, cast=None):
    if isinstance(keys, str):
        keys = [keys]

    # 1) düz st.secrets["KEY"]
    for k in keys:
        try:
            if k in st.secrets:
                val = st.secrets[k]
                return cast(val) if (cast and val is not None) else val
        except Exception:
            pass

    # 2) st.secrets tablo (örn. [fred] api_key=...)
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

    # 3) ortam değişkeni
    for k in keys:
        val = os.environ.get(k)
        if val is not None:
            return cast(val) if cast else val

    return default

# --- FRED ayarları (fallback'lı) ---
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

# ---------- Settings ----------
BASE        = "https://api.stlouisfed.org"
RELEASE_ID  = 20
ELEMENT_ID  = 1193943

# API key'i Streamlit Secrets'tan al
API_KEY = st.secrets.get("API_KEY", None)
if not API_KEY:
    st.error("API key not set. Go to Settings → Secrets and set `API_KEY`.")
    st.stop()

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
    """Return {series_name -> value in millions} for H.4.1 Table subtree."""
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

# ---------- Dates & baseline (radio) ----------
from datetime import date

TARGET_SERIES_ID = "WSHOSHO"  # weekly Wednesday (H.4.1)
_latest = get_latest_available_date(TARGET_SERIES_ID) or "2025-09-03"

t       = pd.to_datetime(_latest).date()     # Latest Wednesday
t_w     = t - timedelta(days=7)              # previous week
t_yoy   = t - relativedelta(years=1)         # YoY (t - 1 year)
t_fixed = date(2025, 1, 1)                   # 01.01.2025

fmt = "%d.%m.%Y"
c1, c2 = st.columns([1, 3])
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

with c2:
    baseline_label = st.radio(
        "Annual baseline",
        ("YoY (t - 1 year)", "01.01.2025"),
        index=0,              # default: YoY
        horizontal=True       # yuvarlak kutucuklar yatay dursun
    )

# Seçime göre yıllık baz
if baseline_label.startswith("YoY"):
    t_y = t_yoy
    base_label = "YoY"
else:
    t_y = t_fixed
    base_label = "2025-01-01"

# ---------- Fetch (seçilen baza göre) ----------
with st.spinner("Fetching H.4.1 data..."):
    vals_t = get_table_values(t.isoformat())
    vals_w = get_table_values(t_w.isoformat())
    vals_y = get_table_values(t_y.isoformat())





# ---------- Calculations ----------
def net_sec(vdict):
    return (
        lookup(vdict, "Securities held outright")
        + lookup(vdict, "Unamortized premiums on securities held outright")
        + lookup(vdict, "Unamortized discounts on securities held outright")
    )

assets_map = {
    "Securities held outright": "Securities (net of prem./disc.)",  # computed via net_sec
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

# ---------- Layout ----------
left, right = st.columns(2, gap="large")

with left:
    st.subheader("Assets — Changes (billions)")
    plot_barh_billions(
        df_assets, 'weekly',
        f"Weekly change ({t.strftime('%b %d, %Y')} vs {t_w.strftime('%b %d, %Y')})",
        "Change (billions of dollars)"
    )
    plot_barh_billions(
        df_assets, 'annual',
        f"Annual change vs baseline {t_y} ({t.strftime('%b %d, %Y')} vs {t_y.strftime('%b %d, %Y')})",
        "Change (billions of dollars)"
    )

with right:
    st.subheader("Liabilities — Reserve impact (billions)")
    plot_barh_billions(
        df_liab, 'weekly_impact',
        f"Weekly impact on reserves ({t.strftime('%b %d, %Y')} vs {t_w.strftime('%b %d, %Y')})",
        "Reserve impact (billions of dollars)"
    )
    plot_barh_billions(
        df_liab, 'annual_impact',
        f"Annual impact vs baseline {t_y} ({t.strftime('%b %d, %Y')} vs {t_y.strftime('%b %d, %Y')})",
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
    
    **Annual baseline:** fixed to YoY (t - 1 year) (not 01.01.2025)
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
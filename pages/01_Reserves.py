# streamlit_app.py
import math, re, requests
from datetime import timedelta
import pandas as pd
import numpy as np
import streamlit as st
from dateutil.relativedelta import relativedelta
from datetime import date, timedelta
from dateutil.relativedelta import relativedelta
import altair as alt



st.set_page_config(page_title="Veridelisi • Reserve Page", layout="wide")

# --- Gezinme Barı (Yatay Menü, Streamlit-native) ---
import streamlit as st

st.markdown("""
<div style="background:#f8f9fa;padding:10px 0 10px 0;margin-bottom:24px;border-radius:8px;display:flex;gap:32px;justify-content:center;">
""", unsafe_allow_html=True)

col1, col2, col3 = st.columns([1,1,1])
with col1:
    st.page_link("streamlit_app.py", label="🏠 Home")
with col2:
    st.page_link("pages/01_Reserves.py", label="📊 Reserves")
with col3:
    st.page_link("pages/01_Repo.py", label="🔄 Repo")

st.markdown("</div>", unsafe_allow_html=True)


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

COLOR_POS = "#2563eb"  # blue for +
COLOR_NEG = "#ef4444"  # red  for -

# ---------------------------------------------------------------------
# Helpers
# ---------------------------------------------------------------------
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

# ---------------------------------------------------------------------
# Dates & baseline selection
# ---------------------------------------------------------------------
TARGET_SERIES_ID = "WSHOSHO"  # weekly Wednesday (H.4.1)
_latest = get_latest_available_date(TARGET_SERIES_ID) or "2025-09-03"

t       = pd.to_datetime(_latest).date()     # Latest Wednesday
t_w     = t - timedelta(days=7)              # previous week
t_yoy   = t - relativedelta(years=1)         # YoY (t - 1 year)
t_fixed = date(2025, 1, 1)                   # 01.01.2025

c1, c2 = st.columns([1, 3])
with c1:
    st.markdown(
        f"""
        <div style="display:inline-block; padding:10px 14px; border:1px solid #e5e7eb; 
            border-radius:10px; background:#fafafa;">
            <div style="font-size:0.95rem; color:#6b7280; margin-bottom:2px;">Latest Wednesday</div>
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
        index=0,
        horizontal=True
    )

# Choose baseline date
if baseline_label.startswith("YoY"):
    t_y = t_yoy
    base_label = "YoY"
else:
    t_y = t_fixed
    base_label = "2025-01-01"

# ---------------------------------------------------------------------
# Fetch
# ---------------------------------------------------------------------
with st.spinner("Fetching H.4.1 data..."):
    vals_t = get_table_values(t.isoformat())
    vals_w = get_table_values(t_w.isoformat())
    vals_y = get_table_values(t_y.isoformat())

# ---------------------------------------------------------------------
# Calculations
# ---------------------------------------------------------------------
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

# ---------------------------------------------------------------------
# Aligned axes helpers
# ---------------------------------------------------------------------
def shared_domain(df, *cols, margin=0.10, divide=1000.0):
    """Return symmetric x-domain (min,max) shared by a set of columns (in $M)."""
    m = 0.0
    for c in cols:
        if isinstance(df, pd.DataFrame) and (c in df.columns):
            m = max(m, float(df[c].abs().max()) / divide if not df.empty else 0.0)
    M = (1.0 + margin) * m
    return (-M, M)

# ---------------------------------------------------------------------
# Altair chart helpers (billions) with fixed row height & tooltips
# ---------------------------------------------------------------------
def _prep(df: pd.DataFrame, col: str) -> pd.DataFrame:
    if df.empty: 
        return pd.DataFrame(columns=["name","val_b","Sign"])
    dd = df.copy()
    dd["val_b"] = dd[col] / 1000.0
    dd["Sign"] = np.where(dd["val_b"] >= 0, "pos", "neg")
    dd = dd.sort_values("val_b")
    return dd

def barh_billions(df: pd.DataFrame, col: str, title: str, xlabel: str, x_domain=None):
    dd = _prep(df, col)
    if dd.empty or (dd["val_b"].abs().max() == 0):
        return None

    base = alt.Chart(dd).encode(
        y=alt.Y("name:N",
                sort="-x",
                title=None,
                scale=alt.Scale(paddingInner=0.15, paddingOuter=0.10),
                axis=alt.Axis(labelLimit=220),
        x=alt.X("val_b:Q",
                title=xlabel,
                axis=alt.Axis(format=",.1f"),
                scale=alt.Scale(domain=x_domain) if x_domain else alt.Undefined),
    )

    color = alt.Color(
        "Sign:N",
        scale=alt.Scale(domain=["pos","neg"], range=[COLOR_POS, COLOR_NEG]),
        legend=None
    )

    bars = base.mark_bar().encode(
        color=color,
        tooltip=[alt.Tooltip("name:N"),
                 alt.Tooltip("val_b:Q", title="Billions", format=",.1f")]
    )
    labels = base.mark_text(dx=6, align="left", baseline="middle", fontWeight="bold").encode(
        text=alt.Text("val_b:Q", format=",.1f")
    )

    height = max(140, 26*len(dd) + 60)
    return (bars + labels).properties(
        title=alt.TitleParams(text=title, anchor="start", dy=12),
        height=height,
        padding={"top":28, "right":12, "left":8, "bottom":8},
    ).configure_title(fontSize=16, fontWeight="bold")

# ---------------------------------------------------------------------
# Layout (with shared domains)
# ---------------------------------------------------------------------
left, right = st.columns(2, gap="large")

# Shared domains per pair (assets / liabilities)
dom_assets = shared_domain(df_assets, 'weekly', 'annual')
dom_liab   = shared_domain(df_liab,   'weekly_impact', 'annual_impact')

with left:
    st.subheader("Assets — Changes (billions)")
    with st.container(border=True):
        ch = barh_billions(
            df_assets, 'weekly',
            f"Weekly change ({t.strftime('%b %d, %Y')} vs {t_w.strftime('%b %d, %Y')})",
            "Change (billions of dollars)",
            x_domain=dom_assets
        )
        if ch is not None:
            st.altair_chart(ch, use_container_width=True, theme=None)

    with st.container(border=True):
        ch = barh_billions(
            df_assets, 'annual',
            f"Annual change vs baseline {t_y.strftime('%Y-%m-%d')} "
            f"({t.strftime('%b %d, %Y')} vs {t_y.strftime('%b %d, %Y')})",
            "Change (billions of dollars)",
            x_domain=dom_assets
        )
        if ch is not None:
            st.altair_chart(ch, use_container_width=True, theme=None)

with right:
    st.subheader("Liabilities — Reserve impact (billions)")
    with st.container(border=True):
        ch = barh_billions(
            df_liab, 'weekly_impact',
            f"Weekly impact on reserves ({t.strftime('%b %d, %Y')} vs {t_w.strftime('%b %d, %Y')})",
            "Reserve impact (billions of dollars)",
            x_domain=dom_liab
        )
        if ch is not None:
            st.altair_chart(ch, use_container_width=True, theme=None)

    with st.container(border=True):
        ch = barh_billions(
            df_liab, 'annual_impact',
            f"Annual impact vs baseline {t_y.strftime('%Y-%m-%d')} "
            f"({t.strftime('%b %d, %Y')} vs {t_y.strftime('%b %d, %Y')})",
            "Reserve impact (billions of dollars)",
            x_domain=dom_liab
        )
        if ch is not None:
            st.altair_chart(ch, use_container_width=True, theme=None)

# ---------------------------------------------------------------------
# Tables & Net
# ---------------------------------------------------------------------
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

st.markdown("""
**Methodology**
- Data source: Federal Reserve H.4.1 Statistical Release (FRED `release/tables` API).
- Display thresholds: ±$50M (weekly), ±$100M (annual).
- 🔵 Positive bars increase the line item; 🔴 Negative bars decrease it.  
  For liabilities, “impact on reserves” is shown with **opposite sign** (increase in liabilities → negative reserve impact).
- **Securities (net)** = held outright + unamortized premiums + unamortized discounts.
- Annual baseline selectable: **YoY (t−1y)** or **fixed 2025-01-01**.
- Charts use **shared symmetric x-axes** within each pair and **fixed row height** to prevent layout drift.
""")

st.markdown(
    """
    <hr style="margin-top:28px; margin-bottom:10px; border:none; border-top:1px solid #e5e7eb;">
    <div style="text-align:center; color:#6b7280; font-size:0.95rem;">
        <strong>Engin Yılmaz</strong> · Visiting Research Scholar · UMASS Amherst · September 2025
    </div>
    """,
    unsafe_allow_html=True
)
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

# --- Styling extras for enhanced tables ---
st.markdown("""
<style>
  .assets-table {background:linear-gradient(135deg,#f8fafc 0%,#e2e8f0 100%);border-radius:12px;padding:16px;border:1px solid #cbd5e1;margin:16px 0;}
  .liabilities-table {background:linear-gradient(135deg,#fef2f2 0%,#fee2e2 100%);border-radius:12px;padding:16px;border:1px solid #fca5a5;margin:16px 0;}
  .table-header,.liab-table-header{font-weight:600;font-size:1.1rem;margin-bottom:12px;display:flex;align-items:center;gap:8px}
  .liab-table-header{color:#7f1d1d}
  .summary-card{background:linear-gradient(135deg,#667eea 0%,#764ba2 100%);color:#fff;padding:20px;border-radius:16px;box-shadow:0 8px 32px rgba(0,0,0,.1);margin:8px 0;position:relative;overflow:hidden}
  .summary-card::before{content:'';position:absolute;inset:0;background:rgba(255,255,255,.1);backdrop-filter:blur(10px);z-index:0}
  .card-content{position:relative;z-index:1}.card-title{font-size:.9rem;opacity:.9;margin-bottom:8px}
  .card-value{font-size:1.8rem;font-weight:700;margin-bottom:4px}.card-subtitle{font-size:.8rem;opacity:.8}
  .positive{background:linear-gradient(135deg,#10b981 0%,#059669 100%)}
  .negative{background:linear-gradient(135deg,#ef4444 0%,#dc2626 100%)}
  .neutral{background:linear-gradient(135deg,#6b7280 0%,#4b5563 100%)}
</style>
""", unsafe_allow_html=True)

# ---------- Enhanced table helpers ----------

def format_millions(value):
    if pd.isna(value) or value == 0: return "—"
    abs_val = abs(value)
    s = f"${abs_val/1000:.1f}B" if abs_val >= 1000 else f"${abs_val:,.0f}M"
    return f"+{s}" if value > 0 else f"-{s}"

def get_significance_badge(value):
    v = abs(value) if not pd.isna(value) else 0
    return "🔥 Major" if v >= 5000 else "⚡ High" if v >= 1000 else "📈 Medium" if v >= 500 else "💭 Low"

def create_enhanced_assets_table(df_assets):
    """Enhanced assets table (NO summary line)."""
    if df_assets.empty:
        st.info("No significant asset changes to display")
        return
    
    display_df = df_assets.copy()
    display_df = display_df.sort_values('weekly', key=abs, ascending=False)
    
    st.markdown(
        '<div class="assets-table"><div class="table-header">📊 Assets Reserve Impacts</div>',
        unsafe_allow_html=True
    )
    
    col1, col2, col3 = st.columns([2, 1, 1])
    with col1:
        sort_by = st.selectbox(
            "Sort by:",
            ["Weekly Impact", "Annual Impact", "Asset Name"],
            key="assets_sort"
        )
    with col2:
        show_threshold = st.selectbox(
            "Show items ≥",
            ["All", "500M+", "1B+", "5B+"],
            key="assets_threshold"
        )
    with col3:
        view_mode = st.radio("View:", ["Compact", "Detailed"], key="assets_view", horizontal=True)
    
    # filter & sort
    filtered_df = display_df.copy()
    if show_threshold != "All":
        threshold_map = {"500M+": 500, "1B+": 1000, "5B+": 5000}
        min_val = threshold_map[show_threshold]
        filtered_df = filtered_df[
            (filtered_df['weekly'].abs() >= min_val) |
            (filtered_df['annual'].abs() >= min_val)
        ]
    if sort_by == "Weekly Impact":
        filtered_df = filtered_df.sort_values('weekly', key=abs, ascending=False)
    elif sort_by == "Annual Impact":
        filtered_df = filtered_df.sort_values('annual', key=abs, ascending=False)
    else:
        filtered_df = filtered_df.sort_values('name')
    
    # rows
    rows = []
    for _, row in filtered_df.iterrows():
        if view_mode == "Compact":
            rows.append({
                "Asset": row['name'][:30] + "..." if len(row['name']) > 30 else row['name'],
                "Weekly": format_millions(row['weekly']),
                "Annual": format_millions(row['annual'])
            })
        else:
            rows.append({
                "Asset Factor": row['name'],
                "Weekly Change": format_millions(row['weekly']),
                "Weekly Impact": get_significance_badge(row['weekly']),
                "Annual Change": format_millions(row['annual']),
                "Annual Impact": get_significance_badge(row['annual'])
            })
    
    if rows:
        df_display = pd.DataFrame(rows)
        st.dataframe(
            df_display,
            use_container_width=True,
            hide_index=True,
            height=min(400, len(df_display) * 35 + 100)
        )
    
    st.markdown('</div>', unsafe_allow_html=True)


def create_enhanced_liabilities_table(df_liab):
    """Enhanced liabilities table (NO summary line, NO biggest-impact note)."""
    if df_liab.empty:
        st.info("No significant liability changes to display")
        return
    
    display_df = df_liab.copy()
    display_df = display_df.sort_values('weekly_impact', key=abs, ascending=False)
    
    st.markdown(
        '<div class="liabilities-table"><div class="liab-table-header">🏦 Liabilities Reserve Impact</div>',
        unsafe_allow_html=True
    )
    
    col1, col2, col3 = st.columns([2, 1, 1])
    with col1:
        sort_by = st.selectbox(
            "Sort by:",
            ["Weekly Impact", "Annual Impact", "Liability Name"],
            key="liab_sort"
        )
    with col2:
        show_threshold = st.selectbox(
            "Show items ≥",
            ["All", "500M+", "1B+", "5B+"],
            key="liab_threshold"
        )
    with col3:
        view_mode = st.radio("View:", ["Compact", "Detailed"], key="liab_view", horizontal=True)
    
    # filter & sort
    filtered_df = display_df.copy()
    if show_threshold != "All":
        threshold_map = {"500M+": 500, "1B+": 1000, "5B+": 5000}
        min_val = threshold_map[show_threshold]
        filtered_df = filtered_df[
            (filtered_df['weekly_impact'].abs() >= min_val) |
            (filtered_df['annual_impact'].abs() >= min_val)
        ]
    if sort_by == "Weekly Impact":
        filtered_df = filtered_df.sort_values('weekly_impact', key=abs, ascending=False)
    elif sort_by == "Annual Impact":
        filtered_df = filtered_df.sort_values('annual_impact', key=abs, ascending=False)
    else:
        filtered_df = filtered_df.sort_values('name')
    
    # rows
    rows = []
    for _, row in filtered_df.iterrows():
        if view_mode == "Compact":
            rows.append({
                "Liability": row['name'][:30] + "..." if len(row['name']) > 30 else row['name'],
                "Weekly Impact": format_millions(row['weekly_impact']),
                "Annual Impact": format_millions(row['annual_impact'])
            })
        else:
            weekly_dir = "📈" if row['weekly_change'] > 0 else "📉" if row['weekly_change'] < 0 else "➡️"
            annual_dir = "📈" if row['annual_change'] > 0 else "📉" if row['annual_change'] < 0 else "➡️"
            rows.append({
                "Liability Factor": row['name'],
                "Weekly Change": f"{weekly_dir} {format_millions(row['weekly_change'])}",
                "Weekly Reserve Impact": format_millions(row['weekly_impact']),
                "Weekly Significance": get_significance_badge(row['weekly_impact']),
                "Annual Change": f"{annual_dir} {format_millions(row['annual_change'])}",
                "Annual Reserve Impact": format_millions(row['annual_impact']),
                "Annual Significance": get_significance_badge(row['annual_impact'])
            })
    
    if rows:
        df_display = pd.DataFrame(rows)
        st.dataframe(
            df_display,
            use_container_width=True,
            hide_index=True,
            height=min(400, len(df_display) * 35 + 100)
        )
    
    st.markdown('</div>', unsafe_allow_html=True)


def create_smart_summary_cards(assets_weekly, assets_annual, liab_weekly, liab_annual, net_weekly, net_annual):
    cls_w = "positive" if net_weekly>0 else "negative" if net_weekly<0 else "neutral"
    cls_a = "positive" if net_annual>0 else "negative" if net_annual<0 else "neutral"
    emoji_w = "💰" if net_weekly>0 else "📉" if net_weekly<0 else "➖"
    emoji_a = "🚀" if net_annual>0 else "⚠️" if net_annual<0 else "➖"
    text_w = "Reserves increasing" if net_weekly>0 else "Reserves decreasing" if net_weekly<0 else "No net change"
    text_a = "Long-term growth" if net_annual>0 else "Long-term decline" if net_annual<0 else "Stable trend"

    st.markdown("### 💼 Smart Reserve Impact Summary")
    c1,c2 = st.columns(2)
    with c1:
        st.markdown(f"""<div class="summary-card {cls_w}"><div class="card-content">
        <div class="card-title">{emoji_w} Weekly Net Impact</div>
        <div class="card-value">{format_millions(net_weekly)}</div>
        <div class="card-subtitle">{text_w}</div></div></div>""", unsafe_allow_html=True)
    with c2:
        st.markdown(f"""<div class="summary-card {cls_a}"><div class="card-content">
        <div class="card-title">{emoji_a} Annual Net Impact</div>
        <div class="card-value">{format_millions(net_annual)}</div>
        <div class="card-subtitle">{text_a}</div></div></div>""", unsafe_allow_html=True)



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
    colors = ["#1fb44c" if x >= 0 else 'red' for x in dd['val_b']]

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

# ---------- Enhanced Tables & Net ----------
st.markdown("---")


# (Sunum eşleşmesi için; tabloda iki taraf aynı sayıda satır)
n_table = min(len(df_assets), len(df_liab))
assets_tbl = df_assets.loc[df_assets[['weekly','annual']].abs().max(axis=1).nlargest(n_table).index] if not df_assets.empty else df_assets
liab_tbl   = df_liab.loc[df_liab[['weekly_impact','annual_impact']].abs().max(axis=1).nlargest(n_table).index] if not df_liab.empty else df_liab

# Geliştirilmiş tablolar
create_enhanced_assets_table(assets_tbl)
create_enhanced_liabilities_table(liab_tbl)

# Net etkiler (aynı hesap)
# ---------- Totals (keep for the expander breakdown) ----------
assets_weekly = float(df_assets["weekly"].sum()) if not df_assets.empty else 0.0
assets_annual = float(df_assets["annual"].sum()) if not df_assets.empty else 0.0
liab_weekly   = float(df_liab["weekly_impact"].sum()) if not df_liab.empty else 0.0
liab_annual   = float(df_liab["annual_impact"].sum()) if not df_liab.empty else 0.0

# ---------- Smart Summary NET from H.4.1 line item ----------
# pull directly from the table snapshots (millions USD)
RB_NAME    = "Reserve balances with Federal Reserve Banks"
rb_latest  = lookup(vals_t, RB_NAME, default=math.nan)
rb_weekago = lookup(vals_w, RB_NAME, default=math.nan)
rb_base    = lookup(vals_y, RB_NAME, default=math.nan)   # baseline (e.g., 2025-01-01)

if np.isnan(rb_latest) or np.isnan(rb_weekago) or np.isnan(rb_base):
    # fallback to component sums if the line is not found
    net_weekly = assets_weekly + liab_weekly
    net_annual = assets_annual + liab_annual
else:
    # direct change in reserve balances → this is the true net impact
    net_weekly = rb_latest - rb_weekago
    net_annual = rb_latest - rb_base

# (opsiyonel: kontrol için küçük not)
# st.caption(f"Debug RB (M$): latest={rb_latest:,.0f}, wk_ago={rb_weekago:,.0f}, base={rb_base:,.0f} → Δw={net_weekly:,.0f}, Δa={net_annual:,.0f}")


# Akıllı özet kartları
create_smart_summary_cards(
    assets_weekly, assets_annual,
    liab_weekly, liab_annual,
    net_weekly, net_annual
)
# ---------------------------- Methodology -------------------------------
st.markdown("### 📋 Methodology")
with st.expander("🔎 Click to expand methodology details", expanded=False):
    st.markdown(
        f"""
**What this page shows**
- 🧭 Compares **the latest Wednesday** H.4.1 snapshot to:
  - ⏱️ **Previous Wednesday** → *Weekly* change  
  - 📅 **Fixed baseline** → *Yearly* change vs **2025-01-01**
- 🧰 Two rows of charts :
  - **WEEKLY:** Assets (Δ level) • Liabilities (Δ reserve impact) — *top-6 by |weekly|*  
  - **YEARLY:** same metrics vs **2025-01-01**

**Data source**
- 📡 Federal Reserve **H.4.1 Statistical Release** via FRED *release/tables* API  
  • H.4.1 overview: <https://fred.stlouisfed.org/release/tables?rid=20&eid=1193943>  
  • FRED API (Release Tables): <https://fred.stlouisfed.org/docs/api/fred/releasetables.html>  
  • Release/Element used: **rid=20**, **eid=1193943** (Wednesday level table)

**Units & transforms**
- 🔢 Values returned by the API are **millions of USD**; charts label **billions** (M → ÷1,000).
- 🧮 *Securities (net of prem./disc.)* =  
  **Held outright** + **Unamortized premiums** + **Unamortized discounts**.

**How changes are computed (by line item)**
- **Assets:**  
  `weekly = latest − week_ago` • `annual = latest − baseline(2025-01-01)`
- **Liabilities:**  
  `weekly_change = latest − week_ago` • `annual_change = latest − baseline`  
  Reserve-impact convention:  
  `weekly_impact = − weekly_change` • `annual_impact = − annual_change`  
  (A rise in a liability **drains** reserves ➜ negative impact.)

**Smart Reserve Impact Summary (the headline card)**
- 🧮 Net weekly/annual numbers are taken **directly** from the H.4.1 line  
  **“Reserve balances with Federal Reserve Banks.”**  
  `NET_weekly = RB(latest) − RB(week_ago)`  
  `NET_annual = RB(latest) − RB(2025-01-01)`  
  👉 This ensures the headline matches the official H.4.1 total even if individual components are filtered.

**Display rules**
- 🚧 Noise filter (applied to component lists): **±$50M** for weekly, **±$100M** for annual.
- 🟩 Positive bars increase levels / add to reserves; 🟥 negatives reduce them.
- 📋 Tables provide compact/detailed views with optional thresholds; charts show top-contributors for readability.

**Caveats**
- Minor differences can appear between component sums and the headline due to filters, rounding, or excluded small lines.  
  The **Smart** card always reflects the official **Reserve balances** change.
        """
    )


# --------------------------- Footer -------------------------------

st.markdown(
    """
    <div style="text-align:center;color:#64748b;font-size:0.95rem;padding:20px 0;">
        <a href="https://veridelisi.substack.com/">Veri Delisi</a>🚀 <br>
        <em>Engin Yılmaz • Amherst • September 2025 </em>
    </div>
    """,
    unsafe_allow_html=True
)

if False:
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


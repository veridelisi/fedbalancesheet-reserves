# streamlit_app.py
import os, math, re, requests
from datetime import timedelta, date
import pandas as pd
import numpy as np
import streamlit as st
from dateutil.relativedelta import relativedelta
import matplotlib.pyplot as plt
from matplotlib.ticker import FuncFormatter, AutoLocator

st.set_page_config(page_title="Veridelisi • Reserve Page", layout="wide")

# --- Top navigation (pure Streamlit) ---
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

# --- Styling (single CSS + badge helper) ---
st.markdown("""
<style>
  [data-testid="stSidebarNav"]{display:none;}
  section[data-testid="stSidebar"][aria-expanded="true"]{display:none;}
  div.block-container{padding-top:0.75rem;}
  .vd-badge{
    display:inline-block;padding:3px 8px;border-radius:8px;
    font-size:0.75rem;font-weight:600;letter-spacing:.2px;
    color:#111827;background:#E5E7EB;border:1px solid #D1D5DB;
    margin-left:.5rem;vertical-align:middle;
  }
</style>
""", unsafe_allow_html=True)

def badge(text, bg="#E5E7EB", fg="#111827", br="#D1D5DB"):
    # single-line HTML to avoid Markdown code block rendering
    return f'<span class="vd-badge" style="background:{bg};color:{fg};border-color:{br};">{text}</span>'


# --- Secrets/env loader: st.secrets -> section -> environment ---
def get_secret(keys, default=None, cast=None):
    if isinstance(keys, str):
        keys = [keys]
    # 1) direct st.secrets["KEY"]
    for k in keys:
        try:
            if k in st.secrets:
                val = st.secrets[k]
                return cast(val) if (cast and val is not None) else val
        except Exception:
            pass
    # 2) search nested sections (e.g., [fred])
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
    # 3) environment variable
    for k in keys:
        val = os.environ.get(k)
        if val is not None:
            return cast(val) if cast else val
    return default

# --- FRED settings (fallbacks) ---
API_KEY    = get_secret(["API_KEY", "FRED_API_KEY"])
BASE       = get_secret(["BASE", "FRED_BASE"], default="https://api.stlouisfed.org")
RELEASE_ID = get_secret(["RELEASE_ID", "FRED_RELEASE_ID"], default=20, cast=int)
ELEMENT_ID = get_secret(["ELEMENT_ID", "FRED_ELEMENT_ID"], default=1193943, cast=int)

if not API_KEY:
    st.error("API key not set. Settings → Secrets: add `API_KEY` (or `FRED_API_KEY`).")
    st.stop()

# ---------- Page ----------
st.title("🏦 Federal Reserve H.4.1 — Assets & Liabilities (Reserves Impact)")
st.caption("Weekly change vs prior week, and Annual change vs fixed baseline 2025-01-01")

# ---------- Settings (kept as in original) ----------
BASE        = "https://api.stlouisfed.org"
RELEASE_ID  = 20
ELEMENT_ID  = 1193943
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
        index=0,
        horizontal=True
    )

# Select yearly baseline
if baseline_label.startswith("YoY"):
    t_y = t_yoy
    base_label = "YoY"
else:
    t_y = t_fixed
    base_label = "2025-01-01"

# ---------- Fetch (as-is) ----------
with st.spinner("Fetching H.4.1 data..."):
    vals_t = get_table_values(t.isoformat())
    vals_w = get_table_values(t_w.isoformat())
    vals_y = get_table_values(t_y.isoformat())

# ---------- Calculations (as-is) ----------
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

def topN(df, col, n):
    if df.empty: 
        return df
    idx = df[col].abs().nlargest(n).index
    return df.loc[idx]


# ---------- Plot helpers (billions) ----------
def _fmtB(x, pos):
    return f"{x:,.1f}B" if abs(x) < 10 else f"{x:,.0f}B"
fmtB = FuncFormatter(_fmtB)

def plot_barh_billions(df, col, title, xlabel, xlim_b=None):
    """Barh in billions. If xlim_b is given, use symmetric [-xlim_b, +xlim_b]."""
    if df.empty or df[col].abs().max() == 0:
        return
    dd = df.copy()
    dd['val_b'] = dd[col] / 1000.0
    dd = dd.sort_values('val_b')
    colors = ['#16a34a' if x >= 0 else '#ef4444' for x in dd['val_b']]

    fig, ax = plt.subplots(figsize=(12, max(4, 0.45*len(dd)+2)))
    ax.barh(dd['name'], dd['val_b'], color=colors, alpha=0.85)
    ax.set_title(title, fontweight='bold')
    ax.set_xlabel(xlabel)
    ax.grid(axis='x', alpha=0.3)
    ax.axvline(0, color='black', lw=1)

    if xlim_b is None:
        max_val = max(abs(dd['val_b'].min()), abs(dd['val_b'].max()))
        ax.set_xlim(-max_val*1.2, max_val*1.2)
    else:
        ax.set_xlim(-xlim_b, xlim_b)

    ax.xaxis.set_major_locator(AutoLocator())
    ax.xaxis.set_major_formatter(fmtB)
    st.pyplot(fig, clear_figure=True)

# Enhanced table functions - replace the table section in your code

def format_millions(value):
    """Format millions with proper styling"""
    if pd.isna(value) or value == 0:
        return "—"
    
    abs_val = abs(value)
    if abs_val >= 1000:
        formatted = f"${abs_val/1000:.1f}B"
    else:
        formatted = f"${abs_val:,.0f}M"
    
    return f"+{formatted}" if value > 0 else f"-{formatted}"

def get_significance_badge(value):
    """Return significance badge based on magnitude"""
    abs_val = abs(value) if not pd.isna(value) else 0
    if abs_val >= 5000:  # 5B+
        return "🔥 Major"
    elif abs_val >= 1000:  # 1B+
        return "⚡ High"
    elif abs_val >= 500:   # 500M+
        return "📈 Medium"
    else:
        return "💭 Low"

def create_enhanced_assets_table(df_assets, show_details=True):
    """Create enhanced assets table with modern styling"""
    if df_assets.empty:
        st.info("No significant asset changes to display")
        return
    
    # Prepare data
    display_df = df_assets.copy()
    display_df = display_df.sort_values('weekly', key=abs, ascending=False)
    
    # Create display table
    table_data = []
    for _, row in display_df.iterrows():
        weekly_badge = get_significance_badge(row['weekly'])
        annual_badge = get_significance_badge(row['annual'])
        
        table_data.append({
            "Asset Factor": row['name'],
            "Weekly": format_millions(row['weekly']),
            "Weekly Impact": weekly_badge,
            "Annual": format_millions(row['annual']),
            "Annual Impact": annual_badge
        })
    
    # Display with custom styling
    st.markdown("""
    <style>
    .assets-table {
        background: linear-gradient(135deg, #f8fafc 0%, #e2e8f0 100%);
        border-radius: 12px;
        padding: 16px;
        border: 1px solid #cbd5e1;
        margin: 16px 0;
    }
    .table-header {
        color: #1e293b;
        font-weight: 600;
        font-size: 1.1rem;
        margin-bottom: 12px;
        display: flex;
        align-items: center;
        gap: 8px;
    }
    </style>
    """, unsafe_allow_html=True)
    
    st.markdown(
        '<div class="assets-table">'
        '<div class="table-header">📊 Assets Changes</div>',
        unsafe_allow_html=True
    )
    
    # Control options
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
    
    # Apply filters and sorting
    filtered_df = display_df.copy()
    
    # Apply threshold filter
    if show_threshold != "All":
        threshold_map = {"500M+": 500, "1B+": 1000, "5B+": 5000}
        min_val = threshold_map[show_threshold]
        filtered_df = filtered_df[
            (filtered_df['weekly'].abs() >= min_val) | 
            (filtered_df['annual'].abs() >= min_val)
        ]
    
    # Apply sorting
    if sort_by == "Weekly Impact":
        filtered_df = filtered_df.sort_values('weekly', key=abs, ascending=False)
    elif sort_by == "Annual Impact":
        filtered_df = filtered_df.sort_values('annual', key=abs, ascending=False)
    else:  # Asset Name
        filtered_df = filtered_df.sort_values('name')
    
    # Rebuild table data after filtering/sorting
    table_data = []
    for _, row in filtered_df.iterrows():
        if view_mode == "Compact":
            table_data.append({
                "Asset": row['name'][:30] + "..." if len(row['name']) > 30 else row['name'],
                "Weekly": format_millions(row['weekly']),
                "Annual": format_millions(row['annual'])
            })
        else:
            weekly_badge = get_significance_badge(row['weekly'])
            annual_badge = get_significance_badge(row['annual'])
            table_data.append({
                "Asset Factor": row['name'],
                "Weekly Change": format_millions(row['weekly']),
                "Weekly Impact": weekly_badge,
                "Annual Change": format_millions(row['annual']),
                "Annual Impact": annual_badge
            })
    
    # Display the table
    if table_data:
        df_display = pd.DataFrame(table_data)
        st.dataframe(
            df_display,
            use_container_width=True,
            hide_index=True,
            height=min(400, len(df_display) * 35 + 100)
        )
        
        # Summary stats
        if len(filtered_df) > 0:
            total_weekly = filtered_df['weekly'].sum()
            total_annual = filtered_df['annual'].sum()
            st.markdown(
                f"**Summary:** {len(filtered_df)} items • "
                f"Weekly total: {format_millions(total_weekly)} • "
                f"Annual total: {format_millions(total_annual)}"
            )
    else:
        st.info("No items match the selected criteria")
    
    st.markdown('</div>', unsafe_allow_html=True)

def create_enhanced_liabilities_table(df_liab, show_details=True):
    """Create enhanced liabilities table with modern styling"""
    if df_liab.empty:
        st.info("No significant liability changes to display")
        return
    
    # Prepare data
    display_df = df_liab.copy()
    display_df = display_df.sort_values('weekly_impact', key=abs, ascending=False)
    
    st.markdown("""
    <style>
    .liabilities-table {
        background: linear-gradient(135deg, #fef2f2 0%, #fee2e2 100%);
        border-radius: 12px;
        padding: 16px;
        border: 1px solid #fca5a5;
        margin: 16px 0;
    }
    .liab-table-header {
        color: #7f1d1d;
        font-weight: 600;
        font-size: 1.1rem;
        margin-bottom: 12px;
        display: flex;
        align-items: center;
        gap: 8px;
    }
    </style>
    """, unsafe_allow_html=True)
    
    st.markdown(
        '<div class="liabilities-table">'
        '<div class="liab-table-header">🏦 Liabilities Reserve Impact</div>',
        unsafe_allow_html=True
    )
    
    # Control options
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
    
    # Apply filters and sorting
    filtered_df = display_df.copy()
    
    # Apply threshold filter
    if show_threshold != "All":
        threshold_map = {"500M+": 500, "1B+": 1000, "5B+": 5000}
        min_val = threshold_map[show_threshold]
        filtered_df = filtered_df[
            (filtered_df['weekly_impact'].abs() >= min_val) | 
            (filtered_df['annual_impact'].abs() >= min_val)
        ]
    
    # Apply sorting
    if sort_by == "Weekly Impact":
        filtered_df = filtered_df.sort_values('weekly_impact', key=abs, ascending=False)
    elif sort_by == "Annual Impact":
        filtered_df = filtered_df.sort_values('annual_impact', key=abs, ascending=False)
    else:  # Liability Name
        filtered_df = filtered_df.sort_values('name')
    
    # Create table data
    table_data = []
    for _, row in filtered_df.iterrows():
        if view_mode == "Compact":
            table_data.append({
                "Liability": row['name'][:30] + "..." if len(row['name']) > 30 else row['name'],
                "Weekly Impact": format_millions(row['weekly_impact']),
                "Annual Impact": format_millions(row['annual_impact'])
            })
        else:
            weekly_badge = get_significance_badge(row['weekly_impact'])
            annual_badge = get_significance_badge(row['annual_impact'])
            
            # Direction indicators
            weekly_dir = "📈" if row['weekly_change'] > 0 else "📉" if row['weekly_change'] < 0 else "➡️"
            annual_dir = "📈" if row['annual_change'] > 0 else "📉" if row['annual_change'] < 0 else "➡️"
            
            table_data.append({
                "Liability Factor": row['name'],
                "Weekly Change": f"{weekly_dir} {format_millions(row['weekly_change'])}",
                "Weekly Reserve Impact": format_millions(row['weekly_impact']),
                "Weekly Significance": weekly_badge,
                "Annual Change": f"{annual_dir} {format_millions(row['annual_change'])}",
                "Annual Reserve Impact": format_millions(row['annual_impact']),
                "Annual Significance": annual_badge
            })
    
    # Display the table
    if table_data:
        df_display = pd.DataFrame(table_data)
        st.dataframe(
            df_display,
            use_container_width=True,
            hide_index=True,
            height=min(400, len(df_display) * 35 + 100)
        )
        
        # Summary stats
        if len(filtered_df) > 0:
            total_weekly = filtered_df['weekly_impact'].sum()
            total_annual = filtered_df['annual_impact'].sum()
            st.markdown(
                f"**Summary:** {len(filtered_df)} items • "
                f"Weekly impact: {format_millions(total_weekly)} • "
                f"Annual impact: {format_millions(total_annual)}"
            )
            
            # Additional insight
            dominant_weekly = filtered_df.loc[filtered_df['weekly_impact'].abs().idxmax(), 'name'] if len(filtered_df) > 0 else "None"
            st.caption(f"💡 Biggest weekly impact: {dominant_weekly}")
    else:
        st.info("No items match the selected criteria")
    
    st.markdown('</div>', unsafe_allow_html=True)

def create_smart_summary_cards(assets_weekly, assets_annual, liab_weekly, liab_annual, net_weekly, net_annual):
    """Create beautiful summary cards with insights"""
    
    st.markdown("""
    <style>
    .summary-container {
        display: flex;
        gap: 16px;
        margin: 24px 0;
        flex-wrap: wrap;
    }
    .summary-card {
        flex: 1;
        min-width: 200px;
        background: linear-gradient(135deg, #667eea 0%, #764ba2 100%);
        color: white;
        padding: 20px;
        border-radius: 16px;
        box-shadow: 0 8px 32px rgba(0,0,0,0.1);
        position: relative;
        overflow: hidden;
    }
    .summary-card::before {
        content: '';
        position: absolute;
        top: 0;
        left: 0;
        right: 0;
        bottom: 0;
        background: rgba(255,255,255,0.1);
        backdrop-filter: blur(10px);
        z-index: 0;
    }
    .card-content {
        position: relative;
        z-index: 1;
    }
    .card-title {
        font-size: 0.9rem;
        opacity: 0.9;
        margin-bottom: 8px;
    }
    .card-value {
        font-size: 1.8rem;
        font-weight: 700;
        margin-bottom: 4px;
    }
    .card-subtitle {
        font-size: 0.8rem;
        opacity: 0.8;
    }
    .positive { background: linear-gradient(135deg, #10b981 0%, #059669 100%); }
    .negative { background: linear-gradient(135deg, #ef4444 0%, #dc2626 100%); }
    .neutral { background: linear-gradient(135deg, #6b7280 0%, #4b5563 100%); }
    </style>
    """, unsafe_allow_html=True)
    
    # Determine card colors and insights
    net_weekly_class = "positive" if net_weekly > 0 else "negative" if net_weekly < 0 else "neutral"
    net_annual_class = "positive" if net_annual > 0 else "negative" if net_annual < 0 else "neutral"
    
    weekly_emoji = "💰" if net_weekly > 0 else "📉" if net_weekly < 0 else "➖"
    annual_emoji = "🚀" if net_annual > 0 else "⚠️" if net_annual < 0 else "➖"
    
    # Create insights
    weekly_insight = "Reserves increasing" if net_weekly > 0 else "Reserves decreasing" if net_weekly < 0 else "No net change"
    annual_insight = "Long-term growth" if net_annual > 0 else "Long-term decline" if net_annual < 0 else "Stable trend"
    
    st.markdown("### 💼 Smart Reserve Impact Summary")
    
    col1, col2 = st.columns(2)
    
    with col1:
        st.markdown(f"""
        <div class="summary-card {net_weekly_class}">
            <div class="card-content">
                <div class="card-title">{weekly_emoji} Weekly Net Impact</div>
                <div class="card-value">{format_millions(net_weekly)}</div>
                <div class="card-subtitle">{weekly_insight}</div>
            </div>
        </div>
        """, unsafe_allow_html=True)
    
    with col2:
        st.markdown(f"""
        <div class="summary-card {net_annual_class}">
            <div class="card-content">
                <div class="card-title">{annual_emoji} Annual Net Impact</div>
                <div class="card-value">{format_millions(net_annual)}</div>
                <div class="card-subtitle">{annual_insight}</div>
            </div>
        </div>
        """, unsafe_allow_html=True)
    
    # Additional breakdown
    with st.expander("🔍 Detailed Breakdown", expanded=False):
        breakdown_data = [
            {"Component": "Assets (Weekly)", "Impact": format_millions(assets_weekly), "Direction": "📈" if assets_weekly > 0 else "📉"},
            {"Component": "Liabilities (Weekly)", "Impact": format_millions(liab_weekly), "Direction": "📈" if liab_weekly > 0 else "📉"},
            {"Component": "Assets (Annual)", "Impact": format_millions(assets_annual), "Direction": "📈" if assets_annual > 0 else "📉"},
            {"Component": "Liabilities (Annual)", "Impact": format_millions(liab_annual), "Direction": "📈" if liab_annual > 0 else "📉"},
        ]
        breakdown_df = pd.DataFrame(breakdown_data)
        st.dataframe(breakdown_df, use_container_width=True, hide_index=True)

# Usage example - replace your existing table section with:
"""
# ---------- Enhanced Tables Section ----------
st.markdown("---")
st.subheader("📊 Smart Reserve Analysis")

# Create enhanced tables
create_enhanced_assets_table(assets_tbl)
create_enhanced_liabilities_table(liab_tbl)

# Create smart summary
create_smart_summary_cards(
    assets_weekly, assets_annual, 
    liab_weekly, liab_annual, 
    net_weekly, net_annual
)
"""

# ---------- Tables & Net ----------
st.markdown("---")
st.subheader("Detailed breakdown (millions)")

# Keep equal counts in tables as well (based on max(abs(weekly), abs(annual)))
n_table = min(len(df_assets), len(df_liab))
if not df_assets.empty:
    sel_idx_a = df_assets[['weekly', 'annual']].abs().max(axis=1).nlargest(n_table).index
    assets_tbl = df_assets.loc[sel_idx_a]
else:
    assets_tbl = df_assets

if not df_liab.empty:
    sel_idx_l = df_liab[['weekly_impact', 'annual_impact']].abs().max(axis=1).nlargest(n_table).index
    liab_tbl = df_liab.loc[sel_idx_l]
else:
    liab_tbl = df_liab

if not assets_tbl.empty:
    st.write("**Assets**")
    sdata = assets_tbl.rename(columns={
        "name":"Asset Factor",
        "weekly":"Weekly ($M)",
        "annual":"Annual ($M)"
    })
    st.dataframe(sdata.reset_index(drop=True), use_container_width=True)

if not liab_tbl.empty:
    st.write("**Liabilities** (impact on reserves shown as negative for increases)")
    tdata = liab_tbl.rename(columns={
        "name":"Liability Factor",
        "weekly_change":"Weekly Change ($M)",
        "annual_change":"Annual Change ($M)",
        "weekly_impact":"Weekly Reserve Impact ($M)",
        "annual_impact":"Annual Reserve Impact ($M)",
    })
    st.dataframe(tdata.reset_index(drop=True), use_container_width=True)

# Net impact uses the full data (unchanged)
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
st.markdown("### 📋 Methodology")
with st.expander("🔎 Click to expand methodology details", expanded=False):
    st.markdown(
        f"""
**What this page does**
- 🧭 Compares **the latest Wednesday** H.4.1 snapshot to:
  - ⏱️ **Previous Wednesday** → *Weekly* change
  - 📅 **Baseline** → *Yearly* change (toggle: **YoY** or **2025-01-01**)

**Data source**
- 📡 Federal Reserve **H.4.1 Statistical Release** via FRED *release/tables* API  
  • H.4.1: <https://www.federalreserve.gov/releases/h41.htm>  
  • FRED API (release/tables): <https://fred.stlouisfed.org/docs/api/fred/releasetables.html>

**Computation notes**
- 🕒 Frequency: weekly (Wednesday reference date).  
- 📐 Units: input values are **millions of USD**; charts display **billions**.  
- 🧮 *Securities (net)* = **Held outright** + **Unamortized premiums** + **Unamortized discounts**.  
- 🏦 Reserve‐impact sign convention for liabilities:  
  - Increase in a liability (e.g., **Reverse repos**, **TGA**) → **reduces** reserves → shown as **negative** impact.  
- 🚧 Display thresholds (to reduce noise): **±$50M** (weekly), **±$100M** (annual).  
- 🎨 Chart colors: positive values (add to reserves/levels) shown in **green**; negatives in **red**.
        """
    )

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

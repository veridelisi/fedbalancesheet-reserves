import math
import requests
import pandas as pd
import numpy as np
import streamlit as st
import altair as alt
from datetime import date
from dateutil.relativedelta import relativedelta



st.set_page_config(page_title="TGA — Deposits, Withdrawals & Closing Balance", layout="wide")

# --- Gezinme Barı (Yatay Menü, Streamlit-native) ---


st.markdown("""
<div style="background:#f8f9fa;padding:10px 0 10px 0;margin-bottom:24px;border-radius:8px;display:flex;gap:32px;justify-content:center;">
""", unsafe_allow_html=True)

col1, col2, col3, col4 = st.columns([1,1,1,1])
with col1:
    st.page_link("streamlit_app.py", label="🏠 Home")
with col2:
    st.page_link("pages/01_Reserves.py", label="📊 Reserves")
with col3:
    st.page_link("pages/01_Repo.py", label="🔄 Repo")
with col4:
    st.page_link("pages/01_TGA.py", label="🔄 TGA")

st.markdown("</div>", unsafe_allow_html=True)


# --- Sol menü sakla ---
st.markdown("""
    <style>
        [data-testid="stSidebarNav"] {display: none;}
        section[data-testid="stSidebar"][aria-expanded="true"]{display: none;}
    </style>
    """, unsafe_allow_html=True)

# -----------------------------------------------------------------------------------
# Constants
# -----------------------------------------------------------------------------------
BASE = "https://api.fiscaldata.treasury.gov/services/api/fiscal_service"
ENDP = "/v1/accounting/dts/operating_cash_balance"

OPEN  = "Treasury General Account (TGA) Opening Balance"
DEPO  = "Total TGA Deposits (Table II)"
WDRW  = "Total TGA Withdrawals (Table II) (-)"
CLOSE = "Treasury General Account (TGA) Closing Balance"

# Colors
COLOR_DEP = "#2563eb"  # blue
COLOR_WDR = "#ef4444"  # red
COLOR_GRAY = "#94a3b8"
COLOR_DARK = "#0f172a"

# Which columns to use per account_type (endpoint vary etse de bunlar kapsıyor)
COLUMN_PREFS = {
    OPEN : ["open_today_bal","opening_balance_today_amt","open_today_bal_amt","amount"],
    # DİKKAT: CLOSE da çoğu gün 'open_today_bal' kolonu ile geliyor
    CLOSE: ["open_today_bal","close_today_bal","closing_balance_today_amt","close_today_bal_amt","amount"],
    DEPO : ["open_today_bal","today_amt","transaction_today_amt","deposit_today_amt","amount"],
    WDRW : ["open_today_bal","today_amt","transaction_today_amt","withdraw_today_amt","amount"],
}


NUM_CANDIDATES = {
    "open_today_bal","close_today_bal",
    "opening_balance_today_amt","closing_balance_today_amt",
    "open_today_bal_amt","close_today_bal_amt",
    "today_amt","transaction_today_amt","amount",
    "deposit_today_amt","withdraw_today_amt",
}

# -----------------------------------------------------------------------------------
# Helpers
# -----------------------------------------------------------------------------------
@st.cache_data(ttl=1800)
def latest_record_date() -> str:
    r = requests.get(f"{BASE}{ENDP}", params={"fields":"record_date","sort":"-record_date","page[size]":1}, timeout=40)
    r.raise_for_status()
    js = r.json().get("data", [])
    if not js:
        raise RuntimeError("No latest record_date returned by API.")
    return js[0]["record_date"]

def _to_float(x):
    try:
        return float(str(x).replace(",", "").replace("$", ""))
    except:
        return math.nan

@st.cache_data(ttl=1800)
@st.cache_data(ttl=1800)
def get_value_on_or_before(target_date: str, account_type: str) -> float | None:
    """
    Returns the latest value (in millions of $) on/before target_date for given account_type.
    We explicitly request all numeric candidates via 'fields' to avoid missing columns.
    """
    fields = ["record_date", "account_type"] + sorted(NUM_CANDIDATES)
    r = requests.get(
        f"{BASE}{ENDP}",
        params={
            "fields": ",".join(fields),
            "filter": f"record_date:lte:{target_date},account_type:eq:{account_type}",
            "sort": "-record_date",
            "page[size]": 1
        },
        timeout=40
    )
    r.raise_for_status()
    data = r.json().get("data", [])
    if not data:
        return None
    row = data[0]
    # normalize numeric fields
    for c in NUM_CANDIDATES:
        if c in row and row[c] is not None:
            try:
                row[c] = float(str(row[c]).replace(",", "").replace("$", ""))
            except:
                row[c] = math.nan
    # pick first available from preferences
    for col in COLUMN_PREFS[account_type]:
        if col in row and pd.notna(row[col]):
            return float(row[col])
    return None


def bn(x):  # millions -> billions
    return None if x is None or pd.isna(x) else x/1000.0

def fmt_bn(x):
    if x is None or pd.isna(x): return "—"
    return f"{x:,.1f}"

def bar_two(df, xfield, ytitle, colors, title=""):
    """df: columns [label, value]"""
    if df.empty:
        return alt.Chart(pd.DataFrame({"label":[],"value":[]})).mark_bar()
    base = alt.Chart(df).encode(
        x=alt.X(f"{xfield}:Q", axis=alt.Axis(title=ytitle, format=",.1f")),
        y=alt.Y("label:N", sort="-x", title=None),
        tooltip=[
            alt.Tooltip("label:N"),
            alt.Tooltip(f"{xfield}:Q", title=ytitle, format=",.1f"),
        ],
    )
    chart = base.mark_bar().encode(
        color=alt.Color("label:N", scale=alt.Scale(range=colors), legend=None)
    )
    labels = base.mark_text(dx=6, align="left", baseline="middle", fontWeight="bold").encode(
        text=alt.Text(f"{xfield}:Q", format=",.1f")
    )
    return (chart + labels).properties(
        title=(title or ""),
        height=140,
        padding={"top": 28, "right": 12, "left": 6, "bottom": 8}
    )

def bar_delta(df, xfield, ytitle, colors, title=""):
    """df: columns [label, value] where value is a delta (can be +/-)"""
    if df.empty:
        return alt.Chart(pd.DataFrame({"label":[],"value":[]})).mark_bar()
    vmin = float(df[xfield].min()) if len(df) else -1.0
    vmax = float(df[xfield].max()) if len(df) else 1.0
    dom = (min(0, vmin*1.15), max(0, vmax*1.15))
    base = alt.Chart(df).encode(
        x=alt.X(f"{xfield}:Q", axis=alt.Axis(title=ytitle, format=",.1f"),
                scale=alt.Scale(domain=dom)),
        y=alt.Y("label:N", sort="-x", title=None),
        tooltip=[alt.Tooltip("label:N"),
                 alt.Tooltip(f"{xfield}:Q", title=ytitle, format=",.1f")],
    )
    bar = base.mark_bar().encode(
        color=alt.Color("label:N", scale=alt.Scale(range=colors), legend=None)
    )
    line0 = alt.Chart(pd.DataFrame({"x":[0]})).mark_rule(color="#111").encode(x="x:Q")
    labels = base.mark_text(dx=6, align="left", baseline="middle", fontWeight="bold").encode(
        text=alt.Text(f"{xfield}:Q", format=",.1f")
    )
    return (bar + line0 + labels).properties(
        title=(title or ""),
        height=140,
        padding={"top":28,"right":12,"left":6,"bottom":8}
    )

# -----------------------------------------------------------------------------------
# Header
# -----------------------------------------------------------------------------------
st.title("🏦 TGA — Deposits, Withdrawals & Closing Balance")
st.caption("Latest day snapshot • Annual compare vs selected baseline (YoY or 2025-01-01)")

# Latest date card + baseline selector
try:
    _latest = latest_record_date()
except Exception as e:
    st.error(f"Failed to fetch latest record date: {e}")
    st.stop()

t_latest = pd.to_datetime(_latest).date()

c1, c2 = st.columns([1,3])
with c1:
    st.markdown(
        f"""
        <div style="display:inline-block;padding:10px 14px;border:1px solid #e5e7eb;border-radius:10px;background:#fafafa;">
          <div style="font-size:0.95rem;color:#6b7280;margin-bottom:2px;">Latest Record Date</div>
          <div style="font-size:1.15rem;font-weight:600;letter-spacing:0.2px;">{t_latest.strftime('%d.%m.%Y')}</div>
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

if baseline_label.startswith("YoY"):
    t_base = (t_latest - relativedelta(years=1))
    base_tag = "YoY"
else:
    t_base = date(2025,1,1)
    base_tag = "2025-01-01"

# -----------------------------------------------------------------------------------
# Fetch values (millions $)
# -----------------------------------------------------------------------------------
open_latest  = get_value_on_or_before(t_latest.isoformat(), OPEN)
depo_latest  = get_value_on_or_before(t_latest.isoformat(), DEPO)
wdrw_latest  = get_value_on_or_before(t_latest.isoformat(), WDRW)
close_latest = get_value_on_or_before(t_latest.isoformat(), CLOSE)

open_base  = get_value_on_or_before(t_base.isoformat(), OPEN)
depo_base  = get_value_on_or_before(t_base.isoformat(), DEPO)
wdrw_base  = get_value_on_or_before(t_base.isoformat(), WDRW)
close_base = get_value_on_or_before(t_base.isoformat(), CLOSE)

# -----------------------------------------------------------------------------------
# 1) Accounting identity: Opening + Deposits - Withdrawals = Closing
# -----------------------------------------------------------------------------------
latest_check = (bn(open_latest) or 0) + (bn(depo_latest) or 0) - (bn(wdrw_latest) or 0)
latest_diff  = None if close_latest is None else latest_check - bn(close_latest)

with st.container(border=True):
    st.subheader("Latest day identity (billions of $)")
    st.markdown(
        f"""
        <div style="font-size:1.1rem;">
        <strong>Opening</strong> <span style="color:#6b7280;">(+)</span>
        <strong>Deposits</strong> <span style="color:#6b7280;">(−)</span>
        <strong>Withdrawals</strong>
        <span style="color:#6b7280;">=</span> <strong>Closing</strong><br/>
        <code>{fmt_bn(bn(open_latest))}</code> + <code style="color:{COLOR_DEP};">{fmt_bn(bn(depo_latest))}</code>
        − <code style="color:{COLOR_WDR};">{fmt_bn(bn(wdrw_latest))}</code>
        = <code>{fmt_bn(bn(close_latest))}</code>
        </div>
        """,
        unsafe_allow_html=True
    )
    if latest_diff is not None:
        st.caption(f"Check (Opening + Deposits − Withdrawals − Closing): {latest_diff:+.1f} bn")

# -----------------------------------------------------------------------------------
# 2) Row: Latest Deposits vs Withdrawals  •  Annual Δ per selected baseline
# -----------------------------------------------------------------------------------
colA, colB = st.columns(2)
with colA:
    st.subheader("Latest Day — Deposits & Withdrawals (bn)")
    df_latest = pd.DataFrame({
        "label": ["Deposits", "Withdrawals"],
        "value": [bn(depo_latest) or 0.0, bn(wdrw_latest) or 0.0]
    })
    ch = bar_two(df_latest, "value", "Billions of $", [COLOR_DEP, COLOR_WDR])
    st.altair_chart(ch, use_container_width=True, theme=None)

with colB:
    st.subheader(f"Annual Δ — per {base_tag} baseline")
    d_dep = (bn(depo_latest) or 0.0) - (bn(depo_base) or 0.0 if depo_base is not None else 0.0)
    d_wdr = (bn(wdrw_latest) or 0.0) - (bn(wdrw_base) or 0.0 if wdrw_base is not None else 0.0)
    df_delta = pd.DataFrame({"label":["Deposits Δ","Withdrawals Δ"], "value":[d_dep, d_wdr]})
    ch2 = bar_delta(df_delta, "value", "Change (billions of $)", [COLOR_DEP, COLOR_WDR])
    st.altair_chart(ch2, use_container_width=True, theme=None)

# -----------------------------------------------------------------------------------
# 3) Closing balance — baseline compare (bars: Baseline vs Latest)
# -----------------------------------------------------------------------------------
st.subheader(f"TGA Closing Balance — Baseline vs Latest (per {base_tag})")
df_close = pd.DataFrame({
    "label": [f"Baseline ({t_base.strftime('%Y-%m-%d')})", f"Latest ({t_latest.strftime('%Y-%m-%d')})"],
    "value": [bn(close_base) if close_base is not None else np.nan,
              bn(close_latest) if close_latest is not None else np.nan]
})
cl = bar_two(df_close, "value", "Billions of $", [COLOR_GRAY, COLOR_DARK])
st.altair_chart(cl, use_container_width=True, theme=None)

# -----------------------------------------------------------------------------------
# 4) Methodology
# -----------------------------------------------------------------------------------
st.markdown("### Methodology")
st.markdown(
"""
- **Source:** U.S. Treasury Fiscal Data — *Daily Treasury Statement* (`operating_cash_balance`).
- We fetch the **latest available record date** and compute values **on/before** the selected baseline (**YoY** or **2025-01-01**).
- **Units:** Millions in the raw feed; charts and text show **billions**.
- **Deposits/Withdrawals:** Reported as **positive** amounts in the source; identity uses **Opening + Deposits − Withdrawals = Closing**.
- Left chart shows **latest-day levels** (Deposits = blue, Withdrawals = red). Right chart shows **annual change (Δ)** vs the selected baseline.
- If the baseline date is a weekend/holiday, we use the **nearest observation on/before** that date.
"""
)

# -----------------------------------------------------------------------------------
# 5) Footer
# -----------------------------------------------------------------------------------
st.markdown(
    """
    <hr style="margin-top:28px;margin-bottom:10px;border:none;border-top:1px solid #e5e7eb;">
    <div style="text-align:center;color:#6b7280;font-size:0.95rem;">
        <strong>Engin Yılmaz</strong> · Visiting Research Scholar · UMASS Amherst · September 2025
    </div>
    """,
    unsafe_allow_html=True
)



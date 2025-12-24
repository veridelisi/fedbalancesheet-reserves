# streamlit_app.py
import math
from datetime import date, timedelta
import requests
import xml.etree.ElementTree as ET

import pandas as pd
import streamlit as st
import plotly.graph_objects as go

st.set_page_config(page_title="Veridelisi • Yield Curve", layout="wide")

# ---------------------------- Top nav (your template) -----------------
cols = st.columns(10)
with cols[0]:
    st.page_link("streamlit_app.py", label="🏠 Home")
with cols[1]:
    st.page_link("pages/01_Reserves.py", label="🌍 Reserves")
with cols[2]:
    st.page_link("pages/01_FDIC.py", label="🏦 FDIC")
with cols[3]:
    st.page_link("pages/01_Repo.py", label="🔄 Repo")
with cols[4]:
    st.page_link("pages/01_Repo2.py", label="♻️ Repo 2")
with cols[5]:
    st.page_link("pages/01_TGA.py", label="🏛️ TGA")
with cols[6]:
    st.page_link("pages/01_PublicBalance.py", label="📊 P.Balance")
with cols[7]:
    st.page_link("pages/01_Interest.py", label="📈 Rates")
with cols[8]:
    st.page_link("pages/01_Desk.py", label="🛰️ Desk")
with cols[9]:
    st.page_link("pages/01_Eurodollar.py", label="💡 Eurodollar")

# ---------------------------- STOP Expanded -----------------
st.markdown(
    """
<style>
    [data-testid="stSidebarNav"] {display: none;}
    section[data-testid="stSidebar"][aria-expanded="true"]{display: none;}
</style>
""",
    unsafe_allow_html=True,
)

# ============================================================
# US Treasury Yield Curve (XML)
# Curves (always shown): Today (latest), 1 Month Ago, 2025-01-02
# Tenors order: 1M -> 2M -> 3M -> 4M -> 6M -> 1Y -> 2Y -> 3Y -> 5Y -> 7Y -> 10Y
# ============================================================

# ----------------------------
# Settings
# ----------------------------
BASE = "https://home.treasury.gov/resource-center/data-chart-center/interest-rates/pages/xmlview"
DATASET = "daily_treasury_yield_curve"

TENOR_ORDER = [
    ("1M",  ["BC_1MONTH", "bc_1month", "BC_1MO", "bc_1mo"]),
    ("2M",  ["BC_2MONTH", "bc_2month", "BC_2MO", "bc_2mo"]),
    ("3M",  ["BC_3MONTH", "bc_3month", "BC_3MO", "bc_3mo"]),
    ("4M",  ["BC_4MONTH", "bc_4month", "BC_4MO", "bc_4mo"]),
    ("6M",  ["BC_6MONTH", "bc_6month", "BC_6MO", "bc_6mo"]),
    ("1Y",  ["BC_1YEAR",  "bc_1year"]),
    ("2Y",  ["BC_2YEAR",  "bc_2year"]),
    ("3Y",  ["BC_3YEAR",  "bc_3year"]),
    ("5Y",  ["BC_5YEAR",  "bc_5year"]),
    ("7Y",  ["BC_7YEAR",  "bc_7year"]),
    ("10Y", ["BC_10YEAR", "bc_10year"]),
]

DATE_KEYS = ["NEW_DATE", "new_date", "DATE", "date", "record_date", "tdr_date"]

# Y-axis styling
ROUND_STEP = 0.1
MIN_VISIBLE_RANGE = 0.30
PADDING_RATIO = 0.12
DTICK = 0.1

# Fixed reference date
REF_DATE = date(2025, 1, 2)

# Fallback yields for 2025-01-02 (from your screenshot)
REF_CURVE_FALLBACK = {
    "1M": 4.45,
    "2M": 4.36,
    "3M": 4.36,
    "4M": 4.31,
    "6M": 4.25,
    "1Y": 4.17,
    "2Y": 4.25,
    "3Y": 4.29,
    "5Y": 4.38,
    "7Y": 4.47,
    "10Y": 4.57,
}

# ----------------------------
# Helpers
# ----------------------------
def yyyymm(d: date) -> str:
    return f"{d.year}{d.month:02d}"

def month_starts_to_try_for_target(d: date):
    first = date(d.year, d.month, 1)
    prev = date(d.year - 1, 12, 1) if d.month == 1 else date(d.year, d.month - 1, 1)
    return [first, prev]

def build_url(mm: str) -> str:
    return f"{BASE}?data={DATASET}&field_tdr_date_value_month={mm}"

def strip_ns(tag: str) -> str:
    return tag.split("}", 1)[-1] if "}" in tag else tag

def fetch_xml(url: str) -> str:
    headers = {
        "User-Agent": "Mozilla/5.0",
        "Accept": "application/xml,text/xml,*/*;q=0.9",
        "Accept-Language": "en-US,en;q=0.9",
    }
    r = requests.get(url, headers=headers, timeout=30)
    r.raise_for_status()
    return r.text

def parse_month_history(xml_text: str) -> pd.DataFrame:
    root = ET.fromstring(xml_text)

    candidates = []
    for node in root.iter():
        t = strip_ns(node.tag).lower()
        if t in ("row", "record", "item", "entry"):
            candidates.append(node)
    if not candidates:
        candidates = list(root)

    rows = []
    for node in candidates:
        rec = {}
        for child in node.iter():
            tag = strip_ns(child.tag)
            if child.text and child.text.strip():
                rec[tag] = child.text.strip()

            name_attr = child.attrib.get("name") or child.attrib.get("field") or child.attrib.get("id")
            if name_attr and child.text and child.text.strip():
                rec[name_attr] = child.text.strip()

        rec_date = None
        for dk in DATE_KEYS:
            if dk in rec:
                rec_date = rec[dk]
                break

        has_any = any(any(k in rec for k in keys) for _, keys in TENOR_ORDER)

        if rec_date and has_any:
            rec["_date"] = rec_date
            rows.append(rec)

    if not rows:
        return pd.DataFrame()

    df = pd.DataFrame(rows)
    df["Date"] = pd.to_datetime(df["_date"], errors="coerce")
    df = df.dropna(subset=["Date"]).sort_values("Date")

    out = pd.DataFrame({"Date": df["Date"]})
    for tenor, keys in TENOR_ORDER:
        col = next((k for k in keys if k in df.columns), None)
        out[tenor] = pd.to_numeric(df[col], errors="coerce") if col else pd.NA

    return out.dropna(subset=["Date"]).reset_index(drop=True)

@st.cache_data(ttl=1800)
def load_month(mm: str) -> pd.DataFrame:
    xml_text = fetch_xml(build_url(mm))
    return parse_month_history(xml_text)

def pick_curve_on_or_before(month_df: pd.DataFrame, target: date):
    if month_df.empty:
        return None

    target_ts = pd.to_datetime(target)
    df = month_df[month_df["Date"] <= target_ts]
    if df.empty:
        return None

    row = df.iloc[-1]
    picked_date = row["Date"]

    curve = {}
    for tenor, _ in TENOR_ORDER:
        v = row.get(tenor)
        curve[tenor] = None if (v is None or pd.isna(v)) else float(v)

    return picked_date, curve

def get_curve_for_target_date(target: date):
    for mstart in month_starts_to_try_for_target(target):
        mm = yyyymm(mstart)
        try:
            month_df = load_month(mm)
            picked = pick_curve_on_or_before(month_df, target)
            if picked is not None:
                return picked
        except Exception:
            pass
    return None

def compute_nice_y_range(series_list):
    all_vals = []
    for s in series_list:
        for v in s:
            if v is not None and not pd.isna(v):
                all_vals.append(float(v))

    if not all_vals:
        raise ValueError("No valid values for y-axis scaling.")

    # If decimals (0.04), convert to percent (4.0)
    if max(all_vals) <= 1.0:
        all_vals = [v * 100 for v in all_vals]

    y_min = min(all_vals)
    y_max = max(all_vals)

    rng = y_max - y_min
    if rng < MIN_VISIBLE_RANGE:
        rng = MIN_VISIBLE_RANGE

    pad = rng * PADDING_RATIO
    y0 = y_min - pad
    y1 = y_max + pad

    y0 = math.floor(y0 / ROUND_STEP) * ROUND_STEP
    y1 = math.ceil(y1 / ROUND_STEP) * ROUND_STEP

    return y0, y1

def curve_to_xy(curve: dict):
    x, y = [], []
    for tenor, _ in TENOR_ORDER:
        v = curve.get(tenor)
        if v is None or pd.isna(v):
            # keep gaps out
            continue
        x.append(tenor)
        y.append(float(v))
    return x, y

# ============================================================
# App
# ============================================================
st.title("US Treasury Yield Curve")

# --- Today curve (latest available observation) ---
today = date.today()
latest_picked = None

for mstart in month_starts_to_try_for_target(today):
    mm = yyyymm(mstart)
    try:
        month_df = load_month(mm)
        if not month_df.empty:
            row = month_df.iloc[-1]
            latest_date_ts = row["Date"]
            latest_curve = {
                tenor: (None if pd.isna(row.get(tenor)) else float(row.get(tenor)))
                for tenor, _ in TENOR_ORDER
            }
            latest_picked = (latest_date_ts, latest_curve)
            break
    except Exception:
        pass

if latest_picked is None:
    st.error("Treasury XML data could not be loaded.")
    st.stop()

today_date_ts, today_curve = latest_picked
today_date = today_date_ts.date()

# --- 1 Month Ago curve ---
one_month_target = today_date - timedelta(days=30)
m1_picked = get_curve_for_target_date(one_month_target)
if m1_picked is None:
    # If month boundary causes empty, try 45 days as fallback (still “about 1 month”)
    m1_picked = get_curve_for_target_date(today_date - timedelta(days=45))

if m1_picked is None:
    st.warning("Could not find 1 Month Ago in XML.")
    m1_date_ts, m1_curve = None, {}
else:
    m1_date_ts, m1_curve = m1_picked

# --- 2025-01-02 curve ---
ref_picked = get_curve_for_target_date(REF_DATE)
if ref_picked is None:
    ref_date_ts = pd.to_datetime(REF_DATE)
    ref_curve = REF_CURVE_FALLBACK.copy()
else:
    ref_date_ts, ref_curve = ref_picked

# ============================================================
# Build traces (NO UI controls, always show)
# ============================================================
traces = []
all_y_for_scaling = []

# Today
x_t, y_t = curve_to_xy(today_curve)
traces.append(("TODAY", x_t, y_t, f"Today ({today_date})", "solid"))
all_y_for_scaling.append(y_t)

# 1 Month Ago
if m1_curve:
    x_m1, y_m1 = curve_to_xy(m1_curve)
    traces.append(("M1", x_m1, y_m1, f"1 Month Ago ({m1_date_ts.date()})", "dot"))
    all_y_for_scaling.append(y_m1)

# 2025-01-02
x_ref, y_ref = curve_to_xy(ref_curve)
traces.append(("REF", x_ref, y_ref, "2025-01-02", "dash"))
all_y_for_scaling.append(y_ref)

# Y-axis range
y0, y1 = compute_nice_y_range(all_y_for_scaling)

# ============================================================
# Plot (kibar / clean style)
# ============================================================
fig = go.Figure()

for _key, x, y, name, dash_style in traces:
    fig.add_trace(
        go.Scatter(
            x=x,
            y=y,
            mode="lines+markers",
            name=name,
            line=dict(width=2, dash=dash_style),
            marker=dict(size=5),
            hovertemplate="<b>%{x}</b><br>Yield: %{y:.2f}%<extra></extra>",
        )
    )

fig.update_layout(
    title=dict(
        text="Yield Curve",
        x=0.0,
        xanchor="left",
        font=dict(size=24),
    ),
    template="plotly_white",
    height=560,
    margin=dict(l=55, r=35, t=85, b=65),
    legend=dict(
        orientation="h",
        yanchor="bottom",
        y=1.02,
        xanchor="left",
        x=0.0,
        bgcolor="rgba(0,0,0,0)",
        font=dict(size=16),
    ),
    hovermode="x unified",
    paper_bgcolor="white",
    plot_bgcolor="white",
)

fig.update_xaxes(
    title_text="",
    tickfont=dict(size=16),
    showgrid=True,
    gridcolor="rgba(230,236,245,1)",
    zeroline=False,
)

fig.update_yaxes(
    title_text="",
    range=[y0, y1],
    tickformat=".1f",
    ticksuffix="%",
    tickfont=dict(size=16),
    showgrid=True,
    gridcolor="rgba(230,236,245,1)",
    zeroline=False,
    dtick=DTICK,
    ticks="outside",
)

# Subtle frame
fig.update_layout(
    shapes=[
        dict(
            type="rect",
            xref="paper",
            yref="paper",
            x0=0,
            y0=0,
            x1=1,
            y1=1,
            line=dict(width=1, color="rgba(0,0,0,0.18)"),
            fillcolor="rgba(0,0,0,0)",
            layer="below",
        )
    ]
)

st.plotly_chart(fig, use_container_width=True)


# ============================================================
# 10Y - 3M Spread (3M Bond-Equivalent Basis) — Last 1 Year only
# Paste UNDER your existing code
# ============================================================

import plotly.graph_objects as go
from datetime import date
from dateutil.relativedelta import relativedelta
import numpy as np

st.subheader("10Y – 3M Spread (Bond-Equivalent 3M) • Last 12 Months")

# 3M Discount Yield -> Bond Equivalent Yield (BEY)
# BEY = (365 * BDY) / (360 - BDY * t), BDY in decimal, t ~ 91 days
def bdy_to_bey(bdy_percent: float, t_days: int = 91) -> float:
    if bdy_percent is None or pd.isna(bdy_percent):
        return np.nan
    bdy = float(bdy_percent) / 100.0
    denom = (360.0 - bdy * t_days)
    if denom <= 0:
        return np.nan
    bey = (365.0 * bdy) / denom
    return bey * 100.0

def month_starts_between(start: date, end: date):
    cur = date(start.year, start.month, 1)
    last = date(end.year, end.month, 1)
    out = []
    while cur <= last:
        out.append(cur)
        cur = (cur + relativedelta(months=1))
    return out

@st.cache_data(ttl=1800)
def load_last_year_10y_3m(start: date, end: date) -> pd.DataFrame:
    parts = []
    for mstart in month_starts_between(start, end):
        mm = yyyymm(mstart)
        try:
            dfm = load_month(mm)  # uses your existing XML loader/parser
            if dfm.empty:
                continue
            # Need only Date, 3M, 10Y
            cols = ["Date"] + [c for c in ["3M", "10Y"] if c in dfm.columns]
            parts.append(dfm[cols].copy())
        except Exception:
            continue

    if not parts:
        return pd.DataFrame(columns=["Date", "10Y", "3M", "3M_BEY", "SPREAD"])

    df = pd.concat(parts, ignore_index=True)
    df = df.dropna(subset=["Date"]).sort_values("Date")
    df = df[(df["Date"].dt.date >= start) & (df["Date"].dt.date <= end)].copy()

    df["3M"] = pd.to_numeric(df.get("3M"), errors="coerce")
    df["10Y"] = pd.to_numeric(df.get("10Y"), errors="coerce")

    df["3M_BEY"] = df["3M"].apply(lambda v: bdy_to_bey(v, t_days=91))
    df["SPREAD"] = df["10Y"] - df["3M_BEY"]

    return df.dropna(subset=["SPREAD"]).reset_index(drop=True)

# ---- build last-12-month window
end_d = date.today()
start_d = end_d - relativedelta(years=1)

df_sp = load_last_year_10y_3m(start_d, end_d)

if df_sp.empty:
    st.info("No spread data found for the last 12 months.")
else:
    # y-range: nice padding
    vals = df_sp["SPREAD"].values.astype(float)
    y_min, y_max = float(np.nanmin(vals)), float(np.nanmax(vals))
    rng = y_max - y_min
    if rng < 0.30:
        rng = 0.30
    pad = rng * 0.12
    y0 = math.floor((y_min - pad) / 0.1) * 0.1
    y1 = math.ceil((y_max + pad) / 0.1) * 0.1

    fig_sp = go.Figure()
    fig_sp.add_trace(
        go.Scatter(
            x=df_sp["Date"],
            y=df_sp["SPREAD"],
            mode="lines",
            line=dict(width=2),
            name="10Y - 3M (BEY)",
            hovertemplate="<b>%{x|%Y-%m-%d}</b><br>Spread: %{y:.2f} pp<extra></extra>",
        )
    )

    # zero line
    fig_sp.add_hline(y=0, line_width=1, line_dash="dot", opacity=0.5)

    fig_sp.update_layout(
        template="plotly_white",
        height=420,
        margin=dict(l=55, r=25, t=50, b=45),
        title=dict(text="10Y – 3M Spread (Last 12 Months)", x=0.0, xanchor="left"),
        hovermode="x unified",
    )

    fig_sp.update_xaxes(showgrid=True, gridcolor="rgba(230,236,245,1)")
    fig_sp.update_yaxes(range=[y0, y1], title_text="Spread (percentage points)", showgrid=True, gridcolor="rgba(230,236,245,1)")

    st.plotly_chart(fig_sp, use_container_width=True)



# ============================================================
# CHECK: 10Y - 3M Spread (Last 3 Months) — PRINT ONLY
# ============================================================

from datetime import date
from dateutil.relativedelta import relativedelta

end_d = date.today()
start_d = end_d - relativedelta(months=3)

rows = []

for mstart in month_starts_between(start_d, end_d):
    mm = yyyymm(mstart)
    try:
        dfm = load_month(mm)   # MEVCUT loader
        if dfm.empty:
            continue

        dfm = dfm[(dfm["Date"].dt.date >= start_d) & (dfm["Date"].dt.date <= end_d)]
        if "3M" not in dfm.columns or "10Y" not in dfm.columns:
            continue

        for _, r in dfm.iterrows():
            if pd.notna(r["3M"]) and pd.notna(r["10Y"]):
                spread = float(r["10Y"]) - float(r["3M"])  # IMPORTANT: 3M zaten BEY
                rows.append({
                    "Date": r["Date"].date(),
                    "10Y": round(float(r["10Y"]), 2),
                    "3M (BEY)": round(float(r["3M"]), 2),
                    "Spread": round(spread, 2)
                })
    except Exception:
        pass

if not rows:
    st.warning("Son 3 ay için spread bulunamadı.")
else:
    df_check = pd.DataFrame(rows).sort_values("Date")
    st.subheader("10Y – 3M Spread (Last 3 Months)")
    st.dataframe(df_check, use_container_width=True)

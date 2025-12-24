# ============================================================
# Streamlit: US Treasury Yield Curve (XML)
# Curves: Today (latest), 1 Month Ago, 2025-01-02
# Tenors order: 1M -> 3M -> 6M -> 1Y -> 2Y -> 3Y -> 5Y -> 7Y -> 10Y
# Controls (buttons) under the chart
# ============================================================

import streamlit as st
import requests
import xml.etree.ElementTree as ET
import pandas as pd
import plotly.graph_objects as go
import math
from datetime import date, timedelta

# ----------------------------
# Settings
# ----------------------------
BASE = "https://home.treasury.gov/resource-center/data-chart-center/interest-rates/pages/xmlview"
DATASET = "daily_treasury_yield_curve"

# Requested tenor order
TENOR_ORDER = [
    ("1M",  ["BC_1MONTH", "bc_1month", "BC_1MO", "bc_1mo"]),
    ("3M",  ["BC_3MONTH", "bc_3month", "BC_3MO", "bc_3mo"]),
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

# Fixed reference date (your “2025 first day” example)
REF_DATE = date(2025, 1, 2)

# Your provided reference yields for 2025-01-02 (fallback if XML lookup fails)
REF_CURVE_FALLBACK = {
    "1M": 4.45,
    "3M": 4.36,
    "6M": 4.25,
    "1Y": 4.17,
    "2Y": 4.25,
    "3Y": 4.29,
    "5Y": 4.38,
    "7Y": 4.47,
    "10Y": 4.57,
}

# ----------------------------
# Helpers: date and url
# ----------------------------
def yyyymm(d: date) -> str:
    return f"{d.year}{d.month:02d}"

def month_starts_to_try_for_target(d: date):
    """
    For a target date, we try that month first; if not found,
    try previous month as a fallback (in case of missing early-month data).
    """
    first = date(d.year, d.month, 1)
    prev = (date(d.year - 1, 12, 1) if d.month == 1 else date(d.year, d.month - 1, 1))
    return [first, prev]

def build_url(mm: str) -> str:
    return f"{BASE}?data={DATASET}&field_tdr_date_value_month={mm}"

# ----------------------------
# Helpers: XML parsing
# ----------------------------
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
    """
    Parse an XML month into a DataFrame with:
    Date, and tenor columns (as floats).
    """
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

        # Must have a date and at least one tenor field
        has_any = False
        for _, keys in TENOR_ORDER:
            if any(k in rec for k in keys):
                has_any = True
                break

        if rec_date and has_any:
            rec["_date"] = rec_date
            rows.append(rec)

    if not rows:
        return pd.DataFrame()

    df = pd.DataFrame(rows)
    df["Date"] = pd.to_datetime(df["_date"], errors="coerce")
    df = df.dropna(subset=["Date"]).sort_values("Date")

    # Build clean tenor columns
    out = pd.DataFrame({"Date": df["Date"]})

    for tenor, keys in TENOR_ORDER:
        col = None
        for k in keys:
            if k in df.columns:
                col = k
                break
        if col:
            out[tenor] = pd.to_numeric(df[col], errors="coerce")
        else:
            out[tenor] = pd.NA

    out = out.dropna(subset=["Date"]).reset_index(drop=True)
    return out

@st.cache_data(ttl=1800)
def load_month(mm: str) -> pd.DataFrame:
    xml_text = fetch_xml(build_url(mm))
    return parse_month_history(xml_text)

def pick_curve_on_or_before(month_df: pd.DataFrame, target: date):
    """
    From month df, pick the latest row with Date <= target.
    Returns (picked_date, curve_dict) or None.
    """
    if month_df.empty:
        return None

    target_ts = pd.to_datetime(target)
    df = month_df[month_df["Date"] <= target_ts].copy()
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
    """
    Try to fetch the curve for a specific target date by loading the XML month(s),
    then selecting the nearest on-or-before row.
    """
    for mstart in month_starts_to_try_for_target(target):
        mm = yyyymm(mstart)
        try:
            month_df = load_month(mm)
            picked = pick_curve_on_or_before(month_df, target)
            if picked is not None:
                return picked  # (picked_date, curve)
        except Exception:
            pass
    return None

def compute_nice_y_range(series_list):
    """
    series_list: list of lists (each is y values in %)
    Returns y0, y1 for axis.
    """
    all_vals = []
    for s in series_list:
        for v in s:
            if v is not None and not pd.isna(v):
                all_vals.append(float(v))

    if not all_vals:
        raise ValueError("No valid values for y-axis scaling.")

    # Decimal vs percent sanity (if somehow <=1)
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
    x = []
    y = []
    for tenor, _ in TENOR_ORDER:
        v = curve.get(tenor)
        if v is None or pd.isna(v):
            # keep gaps out; alternatively you could append None to show breaks
            continue
        x.append(tenor)
        y.append(float(v))
    return x, y

# ============================================================
# App
# ============================================================
st.title("US Treasury Yield Curve (XML)")

# --- Fetch curves ---
# Today = latest available observation (from this month, else previous month)
today = date.today()

# 1) Latest “today” curve: get latest row from the newest month we can load
latest_picked = None
for mstart in month_starts_to_try_for_target(today):
    mm = yyyymm(mstart)
    try:
        month_df = load_month(mm)
        if not month_df.empty:
            row = month_df.iloc[-1]
            latest_date = row["Date"]
            latest_curve = {tenor: (None if pd.isna(row.get(tenor)) else float(row.get(tenor))) for tenor, _ in TENOR_ORDER}
            latest_picked = (latest_date, latest_curve)
            break
    except Exception:
        pass

if latest_picked is None:
    st.error("Treasury XML data could not be loaded.")
    st.stop()

today_date_ts, today_curve = latest_picked
today_date = today_date_ts.date()

# 2) 1 Month Ago curve (relative to latest observation date)
one_month_target = today_date - timedelta(days=30)
m1_picked = get_curve_for_target_date(one_month_target)
if m1_picked is None:
    st.warning("Could not find 1 Month Ago in XML. (This can happen around month boundaries.)")
    m1_date_ts, m1_curve = None, {}
else:
    m1_date_ts, m1_curve = m1_picked

# 3) Fixed 2025-01-02 curve
ref_picked = get_curve_for_target_date(REF_DATE)
if ref_picked is None:
    # fallback to your provided values
    ref_date_ts = pd.to_datetime(REF_DATE)
    ref_curve = REF_CURVE_FALLBACK.copy()
else:
    ref_date_ts, ref_curve = ref_picked

# --- Placeholders to keep buttons UNDER the chart but still control it ---
chart_slot = st.empty()
controls_slot = st.container()

# Default selected curves
if "selected_curves" not in st.session_state:
    st.session_state.selected_curves = ["Today", "1 Month Ago", "2025-01-02"]

with controls_slot:
    st.caption("Select which curves to show (controls are below the chart):")
    selected = st.multiselect(
        label="Curves",
        options=["Today", "1 Month Ago", "2025-01-02"],
        default=st.session_state.selected_curves,
        key="selected_curves",
    )

# --- Build traces based on selection ---
traces = []
all_y_for_scaling = []

if "Today" in selected:
    x, y = curve_to_xy(today_curve)
    traces.append(("Today", x, y, f"Today ({today_date})", "solid"))
    all_y_for_scaling.append(y)

if "1 Month Ago" in selected and m1_curve:
    x, y = curve_to_xy(m1_curve)
    traces.append(("1M", x, y, f"1 Month Ago ({m1_date_ts.date()})", "dot"))
    all_y_for_scaling.append(y)

if "2025-01-02" in selected:
    x, y = curve_to_xy(ref_curve)
    traces.append(("REF", x, y, "2025-01-02", "dash"))
    all_y_for_scaling.append(y)

if not traces:
    chart_slot.info("Select at least one curve below to display the chart.")
    st.stop()

# Nice y-axis range from selected curves
y0, y1 = compute_nice_y_range(all_y_for_scaling)

# ----------------------------
# Plot (kibar / clean style) — replace ONLY this block
# ----------------------------
fig = go.Figure()

# traces listende zaten: (key, x, y, name, dash_style)
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
)

# Axes styling
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
)

# Soft background like “card”
fig.update_layout(
    paper_bgcolor="white",
    plot_bgcolor="white",
)

# Optional: subtle frame
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

chart_slot.plotly_chart(fig, use_container_width=True)

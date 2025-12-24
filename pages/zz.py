# ============================================================
# Streamlit: US Treasury Yield Curve (XML) 6M -> 10Y
# - Auto month fallback (this month, then previous)
# - Single curve (latest observation)
# - Nice-looking y-axis scaling (min-based, not forced from 0)
# ============================================================

import streamlit as st
import requests
import xml.etree.ElementTree as ET
import pandas as pd
import plotly.graph_objects as go
import math
from datetime import date

# ----------------------------
# Settings
# ----------------------------
BASE = "https://home.treasury.gov/resource-center/data-chart-center/interest-rates/pages/xmlview"
DATASET = "daily_treasury_yield_curve"

# X-axis order: 6M to 10Y (as you requested)
TENOR_ORDER = [
    ("6M",  ["BC_6MONTH", "bc_6month", "BC_6MO", "bc_6mo"]),
    ("1Y",  ["BC_1YEAR",  "bc_1year"]),
    ("2Y",  ["BC_2YEAR",  "bc_2year"]),
    ("3Y",  ["BC_3YEAR",  "bc_3year"]),
    ("5Y",  ["BC_5YEAR",  "bc_5year"]),
    ("7Y",  ["BC_7YEAR",  "bc_7year"]),
    ("10Y", ["BC_10YEAR", "bc_10year"]),
]

# Date fields can vary depending on XML structure
DATE_KEYS = ["NEW_DATE", "new_date", "DATE", "date", "record_date", "tdr_date"]

# Y-axis styling controls
USE_MIN_MINUS_ONE = False   # If True: y-axis starts at (min - 1.0)
ROUND_STEP = 0.1            # Round axis bounds to this step (0.1 looks good for yields)
MIN_VISIBLE_RANGE = 0.30    # If curve is too flat, enforce at least this range
PADDING_RATIO = 0.12        # Padding as a % of range
DTICK = 0.1                 # Tick step on y-axis (0.1 is clean)

# ----------------------------
# Helpers: date and url
# ----------------------------
def yyyymm(d: date) -> str:
    return f"{d.year}{d.month:02d}"

def prev_month_first(d: date) -> date:
    if d.month == 1:
        return date(d.year - 1, 12, 1)
    return date(d.year, d.month - 1, 1)

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

def parse_latest_curve_from_xml(xml_text: str):
    """
    Returns: (latest_date: pd.Timestamp, curve_dict: {tenor: float|None})
    """
    root = ET.fromstring(xml_text)

    # Collect record-like nodes
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

            # Tag text
            if child.text and child.text.strip():
                rec[tag] = child.text.strip()

            # Sometimes fields look like: <field name="BC_10YEAR">4.78</field>
            name_attr = child.attrib.get("name") or child.attrib.get("field") or child.attrib.get("id")
            if name_attr and child.text and child.text.strip():
                rec[name_attr] = child.text.strip()

        # Find date
        rec_date = None
        for dk in DATE_KEYS:
            if dk in rec:
                rec_date = rec[dk]
                break

        # Must have a date and at least one tenor field
        has_any = False
        for tenor, keys in TENOR_ORDER:
            for k in keys:
                if k in rec:
                    has_any = True
                    break
            if has_any:
                break

        if rec_date and has_any:
            rec["_date"] = rec_date
            rows.append(rec)

    if not rows:
        return None

    df = pd.DataFrame(rows)
    df["_date"] = pd.to_datetime(df["_date"], errors="coerce")
    df = df.dropna(subset=["_date"]).sort_values("_date")

    if df.empty:
        return None

    latest = df.iloc[-1]
    latest_date = latest["_date"]

    curve = {}
    for tenor, keys in TENOR_ORDER:
        val = None
        for k in keys:
            if k in latest and latest[k] not in ("", None):
                val = pd.to_numeric(latest[k], errors="coerce")
                break
        curve[tenor] = None if (val is None or pd.isna(val)) else float(val)

    return latest_date, curve

# ----------------------------
# Helpers: y-axis scaling
# ----------------------------
def compute_nice_y_range(y_values):
    """
    Rules:
    - First check if values look like decimals (<=1.0), convert to percent.
    - Determine y_min/y_max.
    - Add padding, enforce a minimum visible range.
    - Optionally y_min - 1.0 (USE_MIN_MINUS_ONE).
    - Round bounds to ROUND_STEP.
    """
    y = [float(v) for v in y_values if v is not None and not pd.isna(v)]
    if not y:
        raise ValueError("No valid yield values found.")

    # Decimal vs percent sanity: if max <= 1.0, likely 0.04 -> 4.0
    if max(y) <= 1.0:
        y = [v * 100 for v in y]

    y_min = min(y)
    y_max = max(y)

    rng = y_max - y_min
    if rng < MIN_VISIBLE_RANGE:
        rng = MIN_VISIBLE_RANGE

    pad = rng * PADDING_RATIO

    if USE_MIN_MINUS_ONE:
        y0 = y_min - 1.0
    else:
        y0 = y_min - pad

    y1 = y_max + pad

    # Round bounds nicely
    step = ROUND_STEP
    y0 = math.floor(y0 / step) * step
    y1 = math.ceil(y1 / step) * step

    return y0, y1, y  # y returned maybe converted to percent

# ----------------------------
# Load curve with month fallback
# ----------------------------
@st.cache_data(ttl=600)
def load_latest_curve_with_fallback():
    today = date.today()
    m0 = date(today.year, today.month, 1)
    months_to_try = [yyyymm(m0), yyyymm(prev_month_first(m0))]

    last_error = None
    for mm in months_to_try:
        url = build_url(mm)
        try:
            xml_text = fetch_xml(url)
            parsed = parse_latest_curve_from_xml(xml_text)
            if parsed is not None:
                obs_date, curve = parsed
                return obs_date, curve, mm
        except Exception as e:
            last_error = str(e)

    raise RuntimeError(f"No usable Treasury XML data. Last error: {last_error}")

# ============================================================
# Streamlit App
# ============================================================
st.title("US Treasury Yield Curve (6M → 10Y)")

obs_date, curve, month_param = load_latest_curve_with_fallback()

# Build ordered series
x = []
y_raw = []
for tenor, _keys in TENOR_ORDER:
    val = curve.get(tenor)
    if val is not None and not pd.isna(val):
        x.append(tenor)
        y_raw.append(float(val))

# Compute nice range and also handle decimal->percent conversion
y0, y1, y_scaled = compute_nice_y_range(y_raw)

# If compute_nice_y_range converted y to percent, we must use that for plotting
# It returns y_scaled in the same order as y_raw
y = y_scaled

# Plot
fig = go.Figure()
fig.add_trace(
    go.Scatter(
        x=x,
        y=y,
        mode="lines+markers",
        line=dict(width=3),
        marker=dict(size=7),
        name="Current",
    )
)

fig.update_layout(
    title=f"Latest observation: {obs_date.date()} | month filter: {month_param}",
    xaxis_title="Maturity",
    yaxis_title="Yield (%)",
    yaxis=dict(range=[y0, y1]),
    template="plotly_white",
    height=480,
    margin=dict(l=40, r=20, t=60, b=50),
)

fig.update_yaxes(
    dtick=DTICK,
    ticks="outside",
    showgrid=True,
)

st.plotly_chart(fig, use_container_width=True)

import streamlit as st
import requests
import xml.etree.ElementTree as ET
import pandas as pd
import plotly.graph_objects as go
from datetime import date

# ---------------- CONFIG ----------------
BASE = "https://home.treasury.gov/resource-center/data-chart-center/interest-rates/pages/xmlview"
DATASET = "daily_treasury_yield_curve"

TENOR_ORDER = [
    ("6M",  ["BC_6MONTH", "bc_6month", "BC_6MO"]),
    ("1Y",  ["BC_1YEAR",  "bc_1year"]),
    ("2Y",  ["BC_2YEAR",  "bc_2year"]),
    ("3Y",  ["BC_3YEAR",  "bc_3year"]),
    ("5Y",  ["BC_5YEAR",  "bc_5year"]),
    ("7Y",  ["BC_7YEAR",  "bc_7year"]),
    ("10Y", ["BC_10YEAR", "bc_10year"]),
]

DATE_KEYS = ["NEW_DATE", "new_date", "DATE", "date", "record_date"]

# --------------- HELPERS ----------------
def yyyymm(d):
    return f"{d.year}{d.month:02d}"

def prev_month(d):
    return date(d.year - 1, 12, 1) if d.month == 1 else date(d.year, d.month - 1, 1)

def build_url(mm):
    return f"{BASE}?data={DATASET}&field_tdr_date_value_month={mm}"

def fetch_xml(mm):
    headers = {"User-Agent": "Mozilla/5.0"}
    r = requests.get(build_url(mm), headers=headers, timeout=30)
    r.raise_for_status()
    return r.text

def strip_ns(tag):
    return tag.split("}", 1)[-1]

def parse_latest_curve(xml_text):
    root = ET.fromstring(xml_text)
    records = []

    for node in root.iter():
        if strip_ns(node.tag).lower() in ("row", "record", "entry"):
            rec = {}
            for c in node.iter():
                tag = strip_ns(c.tag)
                if c.text and c.text.strip():
                    rec[tag] = c.text.strip()
                name = c.attrib.get("name")
                if name and c.text and c.text.strip():
                    rec[name] = c.text.strip()
            records.append(rec)

    df = pd.DataFrame(records)
    if df.empty:
        return None

    # date
    date_col = next((k for k in DATE_KEYS if k in df.columns), None)
    if not date_col:
        return None

    df["Date"] = pd.to_datetime(df[date_col], errors="coerce")
    df = df.dropna(subset=["Date"]).sort_values("Date")

    latest = df.iloc[-1]

    curve = {}
    for tenor, keys in TENOR_ORDER:
        val = None
        for k in keys:
            if k in latest and latest[k] not in ("", None):
                val = pd.to_numeric(latest[k], errors="coerce")
                break
        curve[tenor] = val

    return latest["Date"], curve

@st.cache_data(ttl=600)
def load_curve():
    today = date.today()
    for d in [date(today.year, today.month, 1), prev_month(today)]:
        try:
            xml = fetch_xml(yyyymm(d))
            parsed = parse_latest_curve(xml)
            if parsed:
                return parsed
        except:
            pass
    raise RuntimeError("No usable Treasury XML data")

# --------------- STREAMLIT ----------------
st.title("US Treasury Yield Curve")

obs_date, curve = load_curve()

# Order + clean
x = []
y = []
for tenor, _ in TENOR_ORDER:
    if curve.get(tenor) is not None:
        x.append(tenor)
        y.append(float(curve[tenor]))

# Y-axis logic
y_min = min(y)
yaxis_range = [0, max(y) * 1.05] if y_min >= 0 else None

fig = go.Figure()
fig.add_trace(go.Scatter(
    x=x,
    y=y,
    mode="lines+markers",
    line=dict(width=3),
    marker=dict(size=7),
    name="Current"
))

fig.update_layout(
    title=f"Yield Curve (Last obs: {obs_date.date()})",
    xaxis_title="Maturity",
    yaxis_title="Yield (%)",
    yaxis=dict(range=yaxis_range),
    template="plotly_white",
    height=450
)

st.plotly_chart(fig, use_container_width=True)

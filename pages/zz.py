import streamlit as st
import pandas as pd
import requests
import xml.etree.ElementTree as ET
from datetime import date

BASE = "https://home.treasury.gov/resource-center/data-chart-center/interest-rates/pages/xmlview"
DATASET = "daily_treasury_yield_curve"

TENOR_MAP = {
    "6M":  ["BC_6MONTH", "bc_6month", "BC_6MO", "bc_6mo"],
    "1Y":  ["BC_1YEAR",  "bc_1year"],
    "2Y":  ["BC_2YEAR",  "bc_2year"],
    "3Y":  ["BC_3YEAR",  "bc_3year"],
    "5Y":  ["BC_5YEAR",  "bc_5year"],
    "7Y":  ["BC_7YEAR",  "bc_7year"],
    "10Y": ["BC_10YEAR", "bc_10year"],
    "20Y": ["BC_20YEAR", "bc_20year"],
    "30Y": ["BC_30YEAR", "bc_30year"],
}

DATE_KEYS = ["NEW_DATE", "new_date", "DATE", "date", "record_date", "tdr_date"]

def yyyymm(d: date) -> str:
    return f"{d.year}{d.month:02d}"

def prev_month(d: date) -> date:
    y, m = d.year, d.month
    if m == 1:
        return date(y - 1, 12, 1)
    return date(y, m - 1, 1)

def build_url(month_yyyymm: str) -> str:
    # field_tdr_date_value_month=YYYYMM
    return f"{BASE}?data={DATASET}&field_tdr_date_value_month={month_yyyymm}"

def fetch_xml(url: str) -> str:
    headers = {
        "User-Agent": "Mozilla/5.0",
        "Accept": "application/xml,text/xml,*/*;q=0.9",
        "Accept-Language": "en-US,en;q=0.9",
    }
    r = requests.get(url, headers=headers, timeout=30)
    r.raise_for_status()
    return r.text

def try_get_attr(elem, names):
    # <field name="BC_10YEAR"> style OR <BC_10YEAR> style
    # 1) attributes
    for n in names:
        if n in elem.attrib:
            return elem.attrib.get(n)
    return None

def normalize_tag(tag: str) -> str:
    # remove namespace: {ns}tag
    if "}" in tag:
        return tag.split("}", 1)[1]
    return tag

def parse_treasury_xml(xml_text: str) -> pd.DataFrame:
    root = ET.fromstring(xml_text)

    rows = []

    # Pattern A: <row>...</row>
    # Pattern B: Atom feed <entry><content>... fields ...
    # We'll collect "record-like" nodes heuristically.
    candidates = []
    for node in root.iter():
        t = normalize_tag(node.tag).lower()
        if t in ("row", "record", "item", "entry"):
            candidates.append(node)

    # If no obvious candidates, fall back: treat direct children as candidates
    if not candidates:
        candidates = list(root)

    for node in candidates:
        record = {}

        # collect child tags as key/value
        for child in list(node.iter()):
            tag = normalize_tag(child.tag)
            if child.text and child.text.strip():
                record[tag] = child.text.strip()

            # also handle <field name="BC_10YEAR">4.78</field>
            name_attr = child.attrib.get("name") or child.attrib.get("field") or child.attrib.get("id")
            if name_attr and child.text and child.text.strip():
                record[name_attr] = child.text.strip()

        # find date
        rec_date = None
        for dk in DATE_KEYS:
            if dk in record:
                rec_date = record[dk]
                break

        # keep only records that have at least one tenor
        has_any = False
        for tenor, keys in TENOR_MAP.items():
            for k in keys:
                if k in record:
                    has_any = True
                    break
            if has_any:
                break

        if rec_date and has_any:
            record["_date"] = rec_date
            rows.append(record)

    if not rows:
        return pd.DataFrame()

    df = pd.DataFrame(rows)

    # Parse date safely
    df["_date"] = pd.to_datetime(df["_date"], errors="coerce")
    df = df.dropna(subset=["_date"]).sort_values("_date")

    # Build clean curve columns
    out = pd.DataFrame({"Date": df["_date"]})

    for tenor, keys in TENOR_MAP.items():
        col = None
        for k in keys:
            if k in df.columns:
                col = k
                break
        if col:
            out[tenor] = pd.to_numeric(df[col], errors="coerce")
        else:
            out[tenor] = pd.NA

    return out.dropna(subset=["Date"])

@st.cache_data(ttl=600)
def load_latest_curve():
    today = date.today()
    m0 = date(today.year, today.month, 1)
    months_to_try = [yyyymm(m0), yyyymm(prev_month(m0))]  # this month, then previous

    last_err = None
    for mm in months_to_try:
        url = build_url(mm)
        try:
            xml_text = fetch_xml(url)
            df = parse_treasury_xml(xml_text)
            if not df.empty:
                latest = df.iloc[-1]
                curve = latest.drop(labels=["Date"]).to_dict()
                return {
                    "month_param": mm,
                    "url": url,
                    "date": latest["Date"],
                    "curve": curve,
                    "history_df": df,
                }
        except Exception as e:
            last_err = str(e)

    raise RuntimeError(f"XML fetched but no usable data. Last error: {last_err}")

st.title("US Daily Treasury Yield Curve (XML)")

try:
    data = load_latest_curve()
    st.caption(f"Source month param: {data['month_param']}")
    st.caption(f"Latest observation date: {data['date'].date()}")

    curve_df = pd.DataFrame(
        {"Tenor": list(data["curve"].keys()), "Yield": list(data["curve"].values())}
    )
    st.dataframe(curve_df, use_container_width=True)

    # Yield curve chart
    chart_df = curve_df.set_index("Tenor")
    st.line_chart(chart_df)

    with st.expander("Raw month history (for debugging)"):
        st.dataframe(data["history_df"], use_container_width=True)

except Exception as e:
    st.error(f"Failed: {e}")

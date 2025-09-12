# streamlit_app.py
# NY Fed Reference Rates (EFFR, OBFR, SOFR, BGCR, TGCR)
# Run:  pip install streamlit pandas requests altair python-dateutil
#       streamlit run streamlit_app.py

import io
import requests
import pandas as pd
import altair as alt
import streamlit as st
from datetime import date, timedelta

st.set_page_config(page_title="NY Fed Reference Rates", layout="wide")

API_BASE = "https://markets.newyorkfed.org/api/rates"
SPECS = {
    "EFFR": {"group": "unsecured", "code": "effr"},
    "OBFR": {"group": "unsecured", "code": "obfr"},
    "SOFR": {"group": "secured",   "code": "sofr"},
    "BGCR": {"group": "secured",   "code": "bgcr"},
    "TGCR": {"group": "secured",   "code": "tgcr"},
}

# -------------------------
# Download ONLY date + rate
# -------------------------
def fetch_rates(rate_name: str, last_n: int = 500) -> pd.DataFrame:
    spec = SPECS[rate_name]
    url = f"{API_BASE}/{spec['group']}/{spec['code']}/last/{last_n}.csv"
    r = requests.get(url, timeout=20)
    r.raise_for_status()
    raw = pd.read_csv(io.StringIO(r.text))
    if "Effective Date" in raw.columns and "Rate (%)" in raw.columns:
        df = raw[["Effective Date", "Rate (%)"]].copy()
        df.columns = ["date", "rate"]
    else:
        raise ValueError(f"{rate_name} columns not found. Got: {list(raw.columns)}")
    df["date"] = pd.to_datetime(df["date"]).dt.date
    df["series"] = rate_name
    return df.sort_values("date")

def value_on_yoy(df: pd.DataFrame, window_days: int = 7):
    last_date = df["date"].max()
    target = last_date - timedelta(days=365)
    exact = df[df["date"] == target]
    if not exact.empty:
        return float(exact.iloc[0]["rate"])
    tmp = df.copy()
    tmp["diff"] = tmp["date"].apply(lambda d: abs((d - target).days))
    closest = tmp.sort_values(["diff", "date"]).iloc[0]
    if closest["diff"] <= window_days:
        return float(closest["rate"])
    past = df[df["date"] < target]
    return float(past.iloc[-1]["rate"]) if not past.empty else None

def value_on_or_after_anchor(df: pd.DataFrame, anchor: date = date(2025, 1, 1)):
    sub = df[df["date"] >= anchor]
    return float(sub.iloc[0]["rate"]) if not sub.empty else None

def dynamic_y_domain(levels_df: pd.DataFrame, pad_pp: float = 0.05):
    """Return (ymin, ymax) based on selected series; pad in percentage points."""
    if levels_df.empty:
        return None
    lo = float(levels_df["rate"].min())
    hi = float(levels_df["rate"].max())
    if pd.isna(lo) or pd.isna(hi):
        return None
    return (lo - pad_pp, hi + pad_pp)

st.markdown("### 🏦 NY Fed Reference Rates — EFFR · OBFR · SOFR · BGCR · TGCR")

# -------------------------
# Fetch data
# -------------------------
with st.spinner("Fetching rates..."):
    frames, errors = [], []
    for k in SPECS.keys():
        try:
            frames.append(fetch_rates(k, last_n=500))
        except Exception as e:
            errors.append(f"{k}: {e}")
    if errors:
        st.warning("Some series failed:\n\n- " + "\n- ".join(errors))
    data = pd.concat(frames, ignore_index=True) if frames else pd.DataFrame(columns=["date","rate","series"])

if data.empty:
    st.stop()

# -------------------------
# Summary table (values)
# -------------------------
rows = []
anchor_2025 = date(2025, 1, 1)
for s in SPECS.keys():
    ds = data[data["series"] == s].sort_values("date")
    last_date = ds["date"].max()
    last_rate = float(ds.loc[ds["date"] == last_date, "rate"].iloc[0])
    yoy_val   = value_on_yoy(ds)
    a2025_val = value_on_or_after_anchor(ds, anchor_2025)
    rows.append({
        "Series": s,
        "Last Day": last_date.strftime("%Y-%m-%d"),
        "Last Rate (%)": round(last_rate, 4),
        "YoY Value (%)": None if yoy_val is None else round(yoy_val, 4),
        "01-01-2025 Value (%)": None if a2025_val is None else round(a2025_val, 4),
    })
summary_df = pd.DataFrame(rows)

st.markdown("#### 📌 Summary — Last Day • YoY (value) • 01-01-2025 (value)")
st.dataframe(
    summary_df.style.format({
        "Last Rate (%)": "{:.4f}",
        "YoY Value (%)": lambda v: "—" if v is None else f"{v:.4f}",
        "01-01-2025 Value (%)": lambda v: "—" if v is None else f"{v:.4f}",
    }),
    use_container_width=True,
    hide_index=True,
)

# -------------------------
# Prepare LEVELS (long)
# -------------------------
pivot = data.pivot(index="date", columns="series", values="rate").sort_index()
levels_long = pivot.reset_index().melt(id_vars="date", var_name="series", value_name="rate").dropna()
levels_long["date"] = pd.to_datetime(levels_long["date"])

# Line styles (legend hidden for dash)
style_map = {"EFFR":[1,0], "OBFR":[6,3], "SOFR":[1,0], "BGCR":[2,2], "TGCR":[2,2]}
levels_long["dash"] = levels_long["series"].map(style_map)

all_series = ["EFFR", "OBFR", "SOFR", "BGCR", "TGCR"]

# =========================================================
# CHART 1 — Last 7 Days — Levels (default: only EFFR)
# =========================================================
st.markdown("### ⏱️ Last 7 Days — Levels")
last_all = levels_long["date"].max()
mask_7 = levels_long["date"] >= (last_all - timedelta(days=7))

default_sel_7 = ["EFFR"]  # only EFFR by default
user_sel_7 = st.multiselect(
    "Select rates to display:",
    options=all_series,
    default=default_sel_7,
    key="sel_levels_7d",
)

lvl7 = levels_long[mask_7 & levels_long["series"].isin(user_sel_7)]
domain7 = dynamic_y_domain(lvl7)

chart7 = alt.Chart(lvl7).mark_line().encode(
    x=alt.X("date:T", title="Date"),
    y=alt.Y("rate:Q", title="Rate (%)", scale=alt.Scale(domain=domain7)),
    color=alt.Color("series:N", title="Series"),
    strokeDash=alt.StrokeDash("dash", legend=None),
    tooltip=["date:T","series:N",alt.Tooltip("rate:Q", title="Rate (%)", format=".4f")],
).properties(height=340)

st.altair_chart(chart7, use_container_width=True)

# =========================================================
# CHART 2 — Since 01-01-2025 — Levels (default: only EFFR)
# =========================================================
st.markdown("### 📅 Since 01-01-2025 — Levels")
mask_ytd = levels_long["date"] >= pd.to_datetime(date(2025,1,1))

default_sel_ytd = ["EFFR"]  # only EFFR by default
user_sel_ytd = st.multiselect(
    "Select rates to display:",
    options=all_series,
    default=default_sel_ytd,
    key="sel_levels_ytd",
)

lvl_ytd = levels_long[mask_ytd & levels_long["series"].isin(user_sel_ytd)]
domain_ytd = dynamic_y_domain(lvl_ytd)

chart_ytd = alt.Chart(lvl_ytd).mark_line().encode(
    x=alt.X("date:T", title="Date"),
    y=alt.Y("rate:Q", title="Rate (%)", scale=alt.Scale(domain=domain_ytd)),
    color=alt.Color("series:N", title="Series"),
    strokeDash=alt.StrokeDash("dash", legend=None),
    tooltip=["date:T","series:N",alt.Tooltip("rate:Q", title="Rate (%)", format=".4f")],
).properties(height=340)

st.altair_chart(chart_ytd, use_container_width=True)

with st.expander("Notes"):
    st.markdown(
        """
- Only `Effective Date` and `Rate (%)` are retrieved from the NY Fed API.
- Summary shows values on those dates.
- Charts are **levels**; the y-axis is **dynamic** based on the selected series (no zero baseline).
- Defaults show **only EFFR**; use the checkboxes to add **OBFR, SOFR, BGCR, TGCR**.
- Line styles: **EFFR solid**, **OBFR dashed**, **SOFR solid**, **BGCR/TGCR dotted** (dash legend hidden).
        """
    )

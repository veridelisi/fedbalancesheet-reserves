# streamlit_app.py
# NY Fed Reference Rates (EFFR, OBFR, SOFR, BGCR, TGCR)
# pip install streamlit pandas requests altair python-dateutil

import io
import requests
import pandas as pd
import altair as alt
import streamlit as st
from datetime import date, timedelta, datetime

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
        raise ValueError(
            f"{rate_name} columns not found. Got: {list(raw.columns)}"
        )
    df["date"] = pd.to_datetime(df["date"]).dt.date
    df["series"] = rate_name
    return df.sort_values("date")

def value_on_yoy(df: pd.DataFrame, window_days: int = 7):
    """Return the rate on ~365 days earlier (closest within ±window_days)."""
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
    """Return the rate on 01-01-2025 or the first available day after."""
    sub = df[df["date"] >= anchor]
    return float(sub.iloc[0]["rate"]) if not sub.empty else None

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
    use_container_width=True
)

# -------------------------
# One chart: Spreads to SOFR (bps)
# -------------------------
pivot = data.pivot(index="date", columns="series", values="rate").sort_index()
if "SOFR" not in pivot.columns:
    st.info("SOFR not available; cannot build 'SOFR-centered' chart.")
    st.stop()

# compute spreads in basis points (other series minus SOFR) * 100
spreads = pivot.apply(lambda col: (col - pivot["SOFR"]) * 100)

# we will plot only EFFR, OBFR, BGCR, TGCR (SOFR is baseline rule at 0)
plot_cols = [c for c in spreads.columns if c != "SOFR"]
spread_long = spreads[plot_cols].reset_index().melt(
    id_vars="date", var_name="series", value_name="bps"
).dropna()
spread_long["date"] = pd.to_datetime(spread_long["date"])

# style: EFFR solid, OBFR dashed, others default
stroke_dash = alt.Condition(
    alt.datum.series == "OBFR",
    alt.value([6,3]),  # dashed for OBFR
    alt.Condition(
        alt.datum.series == "EFFR",
        alt.value([1,0]),  # solid for EFFR
        alt.value([2,2])   # dotted-ish for others
    )
)

last_sofr = float(pivot["SOFR"].dropna().iloc[-1])

st.markdown(f"### 📈 Spreads to SOFR (bps) — **SOFR (last): {last_sofr:.4f}%**")
base = alt.Chart(spread_long).properties(height=360)

lines = base.mark_line().encode(
    x=alt.X("date:T", title="Date"),
    y=alt.Y("bps:Q", title="Spread to SOFR (bps)"),
    color=alt.Color("series:N", title="Series"),
    strokeDash=stroke_dash,
    tooltip=[
        alt.Tooltip("date:T", title="Date"),
        alt.Tooltip("series:N", title="Series"),
        alt.Tooltip("bps:Q", title="Spread (bps)", format=".2f"),
    ],
)

# zero baseline labeled as SOFR
zero_rule = alt.Chart(pd.DataFrame({"y":[0]})).mark_rule().encode(y="y:Q").properties()
zero_text = alt.Chart(pd.DataFrame({"y":[0]})).mark_text(
    align="left", dx=5, dy=-8
).encode(
    y="y:Q",
    text=alt.value("SOFR baseline (0 bps)")
)

chart = (lines + zero_rule + zero_text)
st.altair_chart(chart, use_container_width=True)

# -------------------------
# 7-day and 365-day windows (still in spreads)
# -------------------------
last_date_all = spread_long["date"].max()
last7 = spread_long[spread_long["date"] >= (last_date_all - timedelta(days=7))]
last365 = spread_long[spread_long["date"] >= (last_date_all - timedelta(days=365))]

st.markdown("#### ⏱️ Last 7 Days — Spreads to SOFR (bps)")
st.altair_chart(
    alt.Chart(last7).mark_line().encode(
        x=alt.X("date:T", title="Date"),
        y=alt.Y("bps:Q", title="Spread to SOFR (bps)"),
        color="series:N",
        strokeDash=stroke_dash,
        tooltip=["date:T","series:N",alt.Tooltip("bps:Q", title="Spread (bps)", format=".2f")]
    ).properties(height=300),
    use_container_width=True
)

st.markdown("#### 📅 Last 365 Days — Spreads to SOFR (bps)")
st.altair_chart(
    alt.Chart(last365).mark_line().encode(
        x=alt.X("date:T", title="Date"),
        y=alt.Y("bps:Q", title="Spread to SOFR (bps)"),
        color="series:N",
        strokeDash=stroke_dash,
        tooltip=["date:T","series:N",alt.Tooltip("bps:Q", title="Spread (bps)", format=".2f")]
    ).properties(height=300),
    use_container_width=True
)

with st.expander("Notes"):
    st.markdown(
        """
- Data: Federal Reserve Bank of New York Markets Data API (Reference Rates).
- Only `Effective Date` and `Rate (%)` are used.
- Table columns show **values on those dates** (no differences).
- Charts show **spreads to SOFR in basis points** to make tiny gaps visible.
- Line styles: **EFFR solid**, **OBFR dashed**, others default.
        """
    )

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
# Summary table (values on dates)
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
    hide_index=True,  # no row numbers
)

# -------------------------
# Spreads to SOFR (bps)
# -------------------------
pivot = data.pivot(index="date", columns="series", values="rate").sort_index()
if "SOFR" not in pivot.columns:
    st.info("SOFR not available; cannot build SOFR-centered charts.")
    st.stop()

# compute spreads in basis points (other series minus SOFR) * 100
spreads = pivot.apply(lambda col: (col - pivot["SOFR"]) * 100)

# SOFR last value for header
last_sofr = float(pivot["SOFR"].dropna().iloc[-1])

# long format (exclude SOFR itself; it is the zero baseline)
plot_cols = [c for c in spreads.columns if c != "SOFR"]
spread_long = spreads[plot_cols].reset_index().melt(
    id_vars="date", var_name="series", value_name="bps"
).dropna()
spread_long["date"] = pd.to_datetime(spread_long["date"])

# per-series line style (no alt.condition)
style_map = {
    "EFFR": [1, 0],  # solid
    "OBFR": [6, 3],  # dashed
    "BGCR": [2, 2],  # dotted
    "TGCR": [2, 2],  # dotted
}
spread_long["dash"] = spread_long["series"].map(style_map)

opts = ["EFFR", "OBFR", "BGCR", "TGCR"]

def baseline_layers(label_text: str):
    zero_rule = alt.Chart(pd.DataFrame({"y":[0]})).mark_rule().encode(y="y:Q")
    zero_text = alt.Chart(pd.DataFrame({"y":[0]})).mark_text(
        align="left", dx=5, dy=-8
    ).encode(y="y:Q", text=alt.value(label_text))
    return zero_rule, zero_text

# ===== Chart 1: Last 7 Days — Spreads to SOFR (bps) =====
st.markdown("### ⏱️ Last 7 Days — Spreads to SOFR (bps)")
sel_7d = st.multiselect(
    "Add rates to the 7-day chart (SOFR baseline is shown by default):",
    options=opts,
    default=[],
    key="sel_last7",
)

last_date_all = spread_long["date"].max()
last7 = spread_long[spread_long["date"] >= (last_date_all - timedelta(days=7))]
last7 = last7[last7["series"].isin(sel_7d)] if sel_7d else last7.iloc[0:0]

base7 = alt.Chart(last7).properties(height=320)
lines7 = base7.mark_line().encode(
    x=alt.X("date:T", title="Date"),
    y=alt.Y("bps:Q", title="Spread to SOFR (bps)"),
    color=alt.Color("series:N", title="Series"),
    strokeDash="dash",
    tooltip=[
        alt.Tooltip("date:T", title="Date"),
        alt.Tooltip("series:N", title="Series"),
        alt.Tooltip("bps:Q", title="Spread (bps)", format=".2f"),
    ],
)
rule7, text7 = baseline_layers(f"SOFR baseline (0 bps) | SOFR last: {last_sofr:.4f}%")
st.altair_chart((lines7 + rule7 + text7), use_container_width=True)

# ===== Chart 2: Spreads to SOFR (bps) — full pulled window =====
st.markdown("### 📈 Spreads to SOFR (bps)")
sel_full = st.multiselect(
    "Add rates to this chart:",
    options=opts,
    default=[],
    key="sel_full",
)
full = spread_long[spread_long["series"].isin(sel_full)] if sel_full else spread_long.iloc[0:0]

base_full = alt.Chart(full).properties(height=320)
lines_full = base_full.mark_line().encode(
    x=alt.X("date:T", title="Date"),
    y=alt.Y("bps:Q", title="Spread to SOFR (bps)"),
    color=alt.Color("series:N", title="Series"),
    strokeDash="dash",
    tooltip=[
        alt.Tooltip("date:T", title="Date"),
        alt.Tooltip("series:N", title="Series"),
        alt.Tooltip("bps:Q", title="Spread (bps)", format=".2f"),
    ],
)
rule_full, text_full = baseline_layers("SOFR baseline (0 bps)")
st.altair_chart((lines_full + rule_full + text_full), use_container_width=True)

# ===== Chart 3: 01.01.2025 Spreads to SOFR (bps) — YTD =====
st.markdown("### 📅 01.01.2025 Spreads to SOFR (bps)")
ytd_mask = spread_long["date"] >= pd.to_datetime(date(2025, 1, 1))
ytd = spread_long[ytd_mask]

sel_ytd = st.multiselect(
    "Add rates to the 2025-YTD chart:",
    options=opts,
    default=[],
    key="sel_ytd",
)
ytd = ytd[ytd["series"].isin(sel_ytd)] if sel_ytd else ytd.iloc[0:0]

base_ytd = alt.Chart(ytd).properties(height=320)
lines_ytd = base_ytd.mark_line().encode(
    x=alt.X("date:T", title="Date"),
    y=alt.Y("bps:Q", title="Spread to SOFR (bps)"),
    color=alt.Color("series:N", title="Series"),
    strokeDash="dash",
    tooltip=[
        alt.Tooltip("date:T", title="Date"),
        alt.Tooltip("series:N", title="Series"),
        alt.Tooltip("bps:Q", title="Spread (bps)", format=".2f"),
    ],
)
rule_ytd, text_ytd = baseline_layers("SOFR baseline (0 bps)")
st.altair_chart((lines_ytd + rule_ytd + text_ytd), use_container_width=True)

with st.expander("Notes"):
    st.markdown(
        """
- Data: Federal Reserve Bank of New York Markets Data API (Reference Rates).
- Only `Effective Date` and `Rate (%)` are used.
- The table shows **values on those dates** (no differences).
- All charts are **spreads to SOFR (bps)** for readability.
- Line styles: **EFFR solid**, **OBFR dashed**, **BGCR/TGCR dotted**.
        """
    )

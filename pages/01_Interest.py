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
# Prepare LEVELS (rates) and SPREADS (bps to SOFR)
# -------------------------
pivot = data.pivot(index="date", columns="series", values="rate").sort_index()
if "SOFR" not in pivot.columns:
    st.info("SOFR not available; cannot build SOFR-centered charts.")
    st.stop()

last_sofr = float(pivot["SOFR"].dropna().iloc[-1])

# levels (long form)
levels_long = pivot.reset_index().melt(id_vars="date", var_name="series", value_name="rate").dropna()
levels_long["date"] = pd.to_datetime(levels_long["date"])

# spreads (other - SOFR) * 100 in bps, exclude SOFR (baseline)
spreads = pivot.apply(lambda col: (col - pivot["SOFR"]) * 100)
spread_long = spreads.reset_index().melt(id_vars="date", var_name="series", value_name="bps").dropna()
spread_long["date"] = pd.to_datetime(spread_long["date"])
spread_long = spread_long[spread_long["series"] != "SOFR"]

# per-series line style (used in all charts)
style_map = {
    "EFFR": [1, 0],  # solid
    "OBFR": [6, 3],  # dashed
    "BGCR": [2, 2],  # dotted
    "TGCR": [2, 2],  # dotted
}
levels_long["dash"] = levels_long["series"].map(style_map)
spread_long["dash"] = spread_long["series"].map(style_map)

# Helper: zero baseline layers for spreads
def baseline_layers(label_text: str):
    zero_rule = alt.Chart(pd.DataFrame({"y":[0]})).mark_rule().encode(y="y:Q")
    zero_text = alt.Chart(pd.DataFrame({"y":[0]})).mark_text(align="left", dx=5, dy=-8)\
                    .encode(y="y:Q", text=alt.value(label_text))
    return zero_rule, zero_text

# Helper: legend selection (click to add)
def legend_selection():
    return alt.selection_point(fields=["series"], bind="legend", name="Select")

# =========================================================
# CHART 1 — Last 7 Days (LEVELS): SOFR auto + click-to-add
# =========================================================
st.markdown("### ⏱️ Last 7 Days — Levels")
last_all = levels_long["date"].max()
mask_7 = levels_long["date"] >= (last_all - timedelta(days=7))
lvl7 = levels_long[mask_7]

# always show SOFR
sofr7 = lvl7[lvl7["series"] == "SOFR"]
base_sofr7 = alt.Chart(sofr7).mark_line().encode(
    x=alt.X("date:T", title="Date"),
    y=alt.Y("rate:Q", title="Rate (%)"),
    color=alt.value("#555555"),
    strokeDash=alt.value([1,0]),
    tooltip=[alt.Tooltip("date:T", title="Date"), alt.Tooltip("rate:Q", title="SOFR (%)", format=".4f")],
).properties(height=320)

# others layer (click legend to add)
others7 = lvl7[lvl7["series"].isin(["EFFR","OBFR","BGCR","TGCR"])]
sel7 = legend_selection()
others7_layer = alt.Chart(others7).mark_line().encode(
    x=alt.X("date:T", title="Date"),
    y=alt.Y("rate:Q", title="Rate (%)"),
    color=alt.Color("series:N", title="Series"),
    strokeDash="dash",
    opacity=alt.condition(sel7, alt.value(1), alt.value(0)),
    tooltip=["date:T","series:N",alt.Tooltip("rate:Q", title="Rate (%)", format=".4f")],
).add_params(sel7)

st.altair_chart(base_sofr7 + others7_layer, use_container_width=True)

# =========================================================
# CHART 2 — Last 7 Days (SPREADS): click-to-add
# =========================================================
st.markdown("### ⏱️ Last 7 Days — Spreads to SOFR (bps)")
spr7 = spread_long[spread_long["date"] >= (last_all - timedelta(days=7))]
sel_spr7 = legend_selection()
lines_spr7 = alt.Chart(spr7).mark_line().encode(
    x=alt.X("date:T", title="Date"),
    y=alt.Y("bps:Q", title="Spread to SOFR (bps)"),
    color=alt.Color("series:N", title="Series"),
    strokeDash="dash",
    opacity=alt.condition(sel_spr7, alt.value(1), alt.value(0)),
    tooltip=["date:T","series:N",alt.Tooltip("bps:Q", title="Spread (bps)", format=".2f")],
).add_params(sel_spr7).properties(height=320)

rule7, text7 = baseline_layers(f"SOFR baseline (0 bps) | SOFR last: {last_sofr:.4f}%")
st.altair_chart(lines_spr7 + rule7 + text7, use_container_width=True)

# =========================================================
# CHART 3 — Since 01-01-2025 (LEVELS): SOFR auto + click-to-add
# =========================================================
st.markdown("### 📅 Since 01-01-2025 — Levels")
mask_ytd = levels_long["date"] >= pd.to_datetime(date(2025,1,1))
lvl_ytd = levels_long[mask_ytd]

sofr_ytd = lvl_ytd[lvl_ytd["series"] == "SOFR"]
base_sofr_ytd = alt.Chart(sofr_ytd).mark_line().encode(
    x=alt.X("date:T", title="Date"),
    y=alt.Y("rate:Q", title="Rate (%)"),
    color=alt.value("#555555"),
    strokeDash=alt.value([1,0]),
    tooltip=[alt.Tooltip("date:T", title="Date"), alt.Tooltip("rate:Q", title="SOFR (%)", format=".4f")],
).properties(height=320)

others_ytd = lvl_ytd[lvl_ytd["series"].isin(["EFFR","OBFR","BGCR","TGCR"])]
sel_ytd_lvl = legend_selection()
others_ytd_layer = alt.Chart(others_ytd).mark_line().encode(
    x=alt.X("date:T", title="Date"),
    y=alt.Y("rate:Q", title="Rate (%)"),
    color=alt.Color("series:N", title="Series"),
    strokeDash="dash",
    opacity=alt.condition(sel_ytd_lvl, alt.value(1), alt.value(0)),
    tooltip=["date:T","series:N",alt.Tooltip("rate:Q", title="Rate (%)", format=".4f")],
).add_params(sel_ytd_lvl)

st.altair_chart(base_sofr_ytd + others_ytd_layer, use_container_width=True)

# =========================================================
# CHART 4 — Since 01-01-2025 (SPREADS): click-to-add
# =========================================================
st.markdown("### 📅 Since 01-01-2025 — Spreads to SOFR (bps)")
spr_ytd = spread_long[spread_long["date"] >= pd.to_datetime(date(2025,1,1))]
sel_spr_ytd = legend_selection()
lines_spr_ytd = alt.Chart(spr_ytd).mark_line().encode(
    x=alt.X("date:T", title="Date"),
    y=alt.Y("bps:Q", title="Spread to SOFR (bps)"),
    color=alt.Color("series:N", title="Series"),
    strokeDash="dash",
    opacity=alt.condition(sel_spr_ytd, alt.value(1), alt.value(0)),
    tooltip=["date:T","series:N",alt.Tooltip("bps:Q", title="Spread (bps)", format=".2f")],
).add_params(sel_spr_ytd).properties(height=320)

rule_ytd, text_ytd = baseline_layers("SOFR baseline (0 bps)")
st.altair_chart(lines_spr_ytd + rule_ytd + text_ytd, use_container_width=True)

with st.expander("Notes"):
    st.markdown(
        """
- Data: Federal Reserve Bank of New York Markets Data API (Reference Rates).
- Only `Effective Date` and `Rate (%)` are used.
- Table shows **values on those dates** (no differences).
- Levels charts: **SOFR line is always drawn automatically**; click legend to add others.
- Spreads charts: **SOFR appears as 0 bps baseline**; click legend to add lines.
- Line styles: **EFFR solid**, **OBFR dashed**, **BGCR/TGCR dotted**.
        """
    )

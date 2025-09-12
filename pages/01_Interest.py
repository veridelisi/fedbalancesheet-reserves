# streamlit_app.py
# NY Fed Reference Rates (EFFR, OBFR, SOFR, BGCR, TGCR)
# Run: pip install streamlit pandas requests altair python-dateutil

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

# small helper: dynamic y-scale around SOFR range (levels charts)
def levels_yscale(df_levels: pd.DataFrame, pad_pp: float = 0.05):
    """Return (ymin, ymax) around SOFR range; pad in percentage points."""
    sofr_only = df_levels[df_levels["series"] == "SOFR"]
    lo = sofr_only["rate"].min()
    hi = sofr_only["rate"].max()
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
# Prepare LEVELS & SPREADS
# -------------------------
pivot = data.pivot(index="date", columns="series", values="rate").sort_index()
if "SOFR" not in pivot.columns:
    st.info("SOFR not available; cannot build SOFR-centered charts.")
    st.stop()

last_sofr = float(pivot["SOFR"].dropna().iloc[-1])

# long (levels)
levels_long = pivot.reset_index().melt(id_vars="date", var_name="series", value_name="rate").dropna()
levels_long["date"] = pd.to_datetime(levels_long["date"])

# spreads (bps to SOFR), excluding SOFR itself
spreads = pivot.apply(lambda col: (col - pivot["SOFR"]) * 100)
spread_long = spreads.reset_index().melt(id_vars="date", var_name="series", value_name="bps").dropna()
spread_long["date"] = pd.to_datetime(spread_long["date"])
spread_long = spread_long[spread_long["series"] != "SOFR"]

# line styles (no legend for dash)
style_map = {"EFFR":[1,0], "OBFR":[6,3], "BGCR":[2,2], "TGCR":[2,2]}
levels_long["dash"] = levels_long["series"].map(style_map)
spread_long["dash"]  = spread_long["series"].map(style_map)

opts = ["EFFR", "OBFR", "BGCR", "TGCR"]

def baseline_layers(label_text: str):
    zero_rule = alt.Chart(pd.DataFrame({"y":[0]})).mark_rule().encode(y="y:Q")
    zero_text = alt.Chart(pd.DataFrame({"y":[0]})).mark_text(
        align="left", dx=5, dy=-8
    ).encode(y="y:Q", text=alt.value(label_text))
    return zero_rule, zero_text

# =========================================================
# CHART 1 — Last 7 Days — Levels (SOFR auto; small box to add others)
# =========================================================
st.markdown("### ⏱️ Last 7 Days — Levels")
last_all = levels_long["date"].max()
mask_7 = levels_long["date"] >= (last_all - timedelta(days=7))
lvl7 = levels_long[mask_7]

# y-scale around SOFR range
ymin, ymax = levels_yscale(lvl7) or (None, None)

# small box to add lines
sel_add_7 = st.multiselect(
    "Add rates:",
    options=opts,
    default=[],
    key="add_lvl7",
)

# SOFR (always)
sofr7 = lvl7[lvl7["series"] == "SOFR"]
sofr_layer7 = alt.Chart(sofr7).mark_line().encode(
    x=alt.X("date:T", title="Date"),
    y=alt.Y("rate:Q", title="Rate (%)", scale=alt.Scale(domain=(ymin, ymax))),
    color=alt.value("#555555"),
    strokeDash=alt.value([1,0]),
    tooltip=[alt.Tooltip("date:T", title="Date"), alt.Tooltip("rate:Q", title="SOFR (%)", format=".4f")],
).properties(height=320)

# Others (added via multiselect)
others7 = lvl7[lvl7["series"].isin(sel_add_7)] if sel_add_7 else lvl7.iloc[0:0]
others_layer7 = alt.Chart(others7).mark_line().encode(
    x=alt.X("date:T", title="Date"),
    y=alt.Y("rate:Q", title="Rate (%)", scale=alt.Scale(domain=(ymin, ymax))),
    color=alt.Color("series:N", title="Series"),
    strokeDash=alt.StrokeDash("dash", legend=None),  # hide dash legend
    tooltip=["date:T","series:N",alt.Tooltip("rate:Q", title="Rate (%)", format=".4f")],
)

st.altair_chart(sofr_layer7 + others_layer7, use_container_width=True)

# =========================================================
# CHART 2 — Last 7 Days — Spreads to SOFR (bps)
# =========================================================
st.markdown("### ⏱️ Last 7 Days — Spreads to SOFR (bps)")
spr7 = spread_long[spread_long["date"] >= (last_all - timedelta(days=7))]
sel_spr_7 = st.multiselect(
    "Add spreads:",
    options=opts,
    default=[],
    key="add_spr7",
)
spr7 = spr7[spr7["series"].isin(sel_spr_7)] if sel_spr_7 else spr7.iloc[0:0]

lines_spr7 = alt.Chart(spr7).mark_line().encode(
    x=alt.X("date:T", title="Date"),
    y=alt.Y("bps:Q", title="Spread to SOFR (bps)"),
    color=alt.Color("series:N", title="Series"),
    strokeDash=alt.StrokeDash("dash", legend=None),
    tooltip=["date:T","series:N",alt.Tooltip("bps:Q", title="Spread (bps)", format=".2f")],
).properties(height=320)

rule7, text7 = baseline_layers(f"SOFR baseline (0 bps) | SOFR last: {last_sofr:.4f}%")
st.altair_chart(lines_spr7 + rule7 + text7, use_container_width=True)

# =========================================================
# CHART 3 — Since 01-01-2025 — Levels (SOFR auto; small box to add others)
# =========================================================
st.markdown("### 📅 Since 01-01-2025 — Levels")
mask_ytd = levels_long["date"] >= pd.to_datetime(date(2025,1,1))
lvl_ytd = levels_long[mask_ytd]

ymin_ytd, ymax_ytd = levels_yscale(lvl_ytd) or (None, None)

sel_add_ytd = st.multiselect(
    "Add rates:",
    options=opts,
    default=[],
    key="add_lvlytd",
)

sofr_ytd = lvl_ytd[lvl_ytd["series"] == "SOFR"]
sofr_layer_ytd = alt.Chart(sofr_ytd).mark_line().encode(
    x=alt.X("date:T", title="Date"),
    y=alt.Y("rate:Q", title="Rate (%)", scale=alt.Scale(domain=(ymin_ytd, ymax_ytd))),
    color=alt.value("#555555"),
    strokeDash=alt.value([1,0]),
    tooltip=[alt.Tooltip("date:T", title="Date"), alt.Tooltip("rate:Q", title="SOFR (%)", format=".4f")],
).properties(height=320)

others_ytd = lvl_ytd[lvl_ytd["series"].isin(sel_add_ytd)] if sel_add_ytd else lvl_ytd.iloc[0:0]
others_layer_ytd = alt.Chart(others_ytd).mark_line().encode(
    x=alt.X("date:T", title="Date"),
    y=alt.Y("rate:Q", title="Rate (%)", scale=alt.Scale(domain=(ymin_ytd, ymax_ytd))),
    color=alt.Color("series:N", title="Series"),
    strokeDash=alt.StrokeDash("dash", legend=None),
    tooltip=["date:T","series:N",alt.Tooltip("rate:Q", title="Rate (%)", format=".4f")],
)

st.altair_chart(sofr_layer_ytd + others_layer_ytd, use_container_width=True)

# =========================================================
# CHART 4 — Since 01-01-2025 — Spreads to SOFR (bps)
# =========================================================
st.markdown("### 📅 Since 01-01-2025 — Spreads to SOFR (bps)")
spr_ytd = spread_long[spread_long["date"] >= pd.to_datetime(date(2025,1,1))]
sel_spr_ytd = st.multiselect(
    "Add spreads:",
    options=opts,
    default=[],
    key="add_sprytd",
)
spr_ytd = spr_ytd[spr_ytd["series"].isin(sel_spr_ytd)] if sel_spr_ytd else spr_ytd.iloc[0:0]

lines_spr_ytd = alt.Chart(spr_ytd).mark_line().encode(
    x=alt.X("date:T", title="Date"),
    y=alt.Y("bps:Q", title="Spread to SOFR (bps)"),
    color=alt.Color("series:N", title="Series"),
    strokeDash=alt.StrokeDash("dash", legend=None),
    tooltip=["date:T","series:N",alt.Tooltip("bps:Q", title="Spread (bps)", format=".2f")],
).properties(height=320)

rule_ytd, text_ytd = baseline_layers("SOFR baseline (0 bps)")
st.altair_chart(lines_spr_ytd + rule_ytd + text_ytd, use_container_width=True)

with st.expander("Notes"):
    st.markdown(
        """
- Only `Effective Date` and `Rate (%)` are retrieved from the NY Fed API.
- Table shows values on those dates (no differences).
- Levels charts: **SOFR auto**; y-axis dynamically centers around SOFR range (no zero baseline).
- Spreads charts: **0 bps baseline** at SOFR.
- Line styles: **EFFR solid**, **OBFR dashed**, **BGCR/TGCR dotted**; dash legend is hidden.
        """
    )

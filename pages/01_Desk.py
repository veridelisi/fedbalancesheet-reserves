# pages/Desk_Operations_Lite.py
# NY Fed Desk Operations — Repo & Reverse Repo (amounts only)
import requests
import pandas as pd
import altair as alt
import streamlit as st
from datetime import date

st.set_page_config(page_title="Desk Operations — Repo & Reverse Repo", layout="wide")

API = "https://markets.newyorkfed.org/api/rp/results/search.json"
YTD_START = date(2025, 1, 1)

# ------------------------------- helpers --------------------------------
def _to_float(x):
    try:
        return float(x)
    except Exception:
        try:
            return float(str(x).replace(",", ""))
        except Exception:
            return None

def fetch_ops(from_d=YTD_START, to_d=None):
    """Pull operations (Repo & Reverse Repo) between dates."""
    if to_d is None:
        to_d = date.today()
    r = requests.get(API, params={"fromDate": from_d.strftime("%Y-%m-%d"),
                                  "toDate":   to_d.strftime("%Y-%m-%d")},
                     timeout=30)
    r.raise_for_status()
    js = r.json()
    return js.get("repo", {}).get("operations", [])

def amount_from_details(op):
    """Sum accepted amounts (USD) from details; fallback to top-level totals."""
    total = 0.0
    for d in (op.get("details") or []):
        a = _to_float(d.get("amtAccepted"))
        if a is not None:
            total += a
    if total == 0 and op.get("totalAmtAccepted") is not None:
        v = _to_float(op.get("totalAmtAccepted"))
        if v: total += v
    return total  # USD

def latest_amounts_by_type(ops):
    """Return last date totals per operationType (Repo / Reverse Repo) in $B."""
    if not ops:
        return pd.DataFrame(columns=["date","operationType","amount_bil"])
    df = pd.json_normalize(ops)
    df["operationDate"] = pd.to_datetime(df["operationDate"])
    last_day = df["operationDate"].max().date()

    buckets = {}
    for op in ops:
        if pd.to_datetime(op["operationDate"]).date() != last_day:
            continue
        t = op.get("operationType")  # 'Repo' | 'Reverse Repo'
        buckets.setdefault(t, 0.0)
        buckets[t] += amount_from_details(op)

    rows = []
    for t, usd in buckets.items():
        if usd > 0:
            rows.append({"date": last_day, "operationType": t, "amount_bil": usd / 1e9})
    return pd.DataFrame(rows).sort_values("operationType")

def ytd_amount_series(ops, op_filter):
    """Daily accepted amounts since 01.01.2025 for a given operationType."""
    daily = {}
    for op in ops:
        if op.get("operationType") != op_filter:
            continue
        d = pd.to_datetime(op.get("operationDate"), errors="coerce")
        if pd.isna(d) or d.date() < YTD_START:
            continue
        usd = amount_from_details(op)
        if usd <= 0:
            continue
        daily[d.date()] = daily.get(d.date(), 0.0) + usd

    if not daily:
        return pd.DataFrame(columns=["date","operationType","amount_bil"])
    out = (pd.DataFrame([{"date": k, "operationType": op_filter, "amount_bil": v/1e9}
                         for k, v in daily.items()])
             .sort_values("date"))
    return out

# ------------------------------- data -----------------------------------
with st.spinner("Loading NY Fed Desk Operations..."):
    ops = fetch_ops()

# =============================== ROW 1 ===================================
st.markdown("### Latest data — Accepted Amounts ($B)")

latest = latest_amounts_by_type(ops)
c1, c2 = st.columns(2)

def _metric_box(col, df, label):
    with col:
        with st.container(border=True):
            st.caption(label)
            if not df.empty:
                day = df["date"].iloc[0]
                # pick row if exists
                row = df[df["operationType"] == label]
                if not row.empty:
                    st.markdown(f"**{day.strftime('%b %d, %Y')}**")
                    st.metric("Amount ($B)", f"{row['amount_bil'].iloc[0]:,.3f}")
                else:
                    st.info("No amount.")
            else:
                st.info("No amount.")

_metric_box(c1, latest, "Repo")
_metric_box(c2, latest, "Reverse Repo")

st.divider()

# =============================== ROW 2 ===================================
st.markdown("### Since 01-01-2025 — Accepted Amounts ($B)")

left, right = st.columns([1, 1])
with left:
    repo_on = st.checkbox("Repo", value=True)
with right:
    rr_on   = st.checkbox("Reverse Repo", value=False)

series_frames = []
if repo_on:
    series_frames.append(ytd_amount_series(ops, "Repo"))
if rr_on:
    series_frames.append(ytd_amount_series(ops, "Reverse Repo"))
series = pd.concat(series_frames, ignore_index=True) if series_frames else pd.DataFrame(columns=["date","operationType","amount_bil"])

# friendly empty-state
if series.empty:
    st.info("No operations in the selected range.")
else:
    # nice compact bar chart like NY Fed: narrow bars, clean axes
    color_scale = alt.Scale(domain=["Repo","Reverse Repo"], range=["#1f77b4", "#d62728"])
    chart = (
        alt.Chart(series)
        .mark_bar(size=6)  # thin bars
        .encode(
            x=alt.X("date:T", title=None),
            y=alt.Y("amount_bil:Q", title="$Billions"),
            color=alt.Color("operationType:N", title=None, scale=color_scale),
            tooltip=[
                alt.Tooltip("date:T", title="Date"),
                alt.Tooltip("operationType:N", title="Type"),
                alt.Tooltip("amount_bil:Q", title="Amount ($B)", format=",.3f"),
            ],
        )
        .properties(height=320)
        .configure_axis(
            grid=False,
            labelFontSize=12,
            titleFontSize=12
        )
    )
    st.altair_chart(chart, use_container_width=True)

# desk_ops.py
# NY Fed Desk Operations — Repo & Reverse Repo (amounts only)
# pip install streamlit pandas requests altair
# streamlit run desk_ops.py

import requests
import pandas as pd
import altair as alt
import streamlit as st
from datetime import date

st.set_page_config(page_title="Desk Ops — Repo & RRP", layout="wide")
st.title("Desk Operations — Repo & Reverse Repo")
st.caption("Accepted amounts only • Latest snapshot and YTD bars (since 01-01-2025)")

API_SEARCH = "https://markets.newyorkfed.org/api/rp/results/search.json"
METHODS = ("treasury", "agency", "mortgagebacked")
YTD_START = date(2025, 1, 1)
TODAY = date.today()
COLOR = {"Repo": "#1f77b4", "Reverse Repo": "#d62728"}

def _to_float(x):
    try: return float(x)
    except Exception:
        try: return float(str(x).replace(",", ""))
        except Exception: return None

def _extract_ops(js: dict):
    if not isinstance(js, dict): return []
    if "repo" in js and isinstance(js["repo"], dict):
        ops = js["repo"].get("operations")
        if isinstance(ops, list): return ops
    if "operations" in js and isinstance(js["operations"], list):
        return js["operations"]
    for v in js.values():
        if isinstance(v, dict) and isinstance(v.get("operations"), list):
            return v["operations"]
    return []

def _accepted_usd(op: dict) -> float:
    total = 0.0
    for d in (op.get("details") or []):
        a = _to_float(d.get("amtAccepted"))
        if a: total += a
    if total == 0 and op.get("totalAmtAccepted") is not None:
        v = _to_float(op.get("totalAmtAccepted"))
        if v: total += v
    return total

@st.cache_data(ttl=15*60, show_spinner=False)
def fetch_ops(operation_type_param: str, start: date, end: date):
    """operation_type_param: 'repo' or 'reverserepo'"""
    all_ops = []
    for m in METHODS:
        params = {
            "operationType": operation_type_param,
            "method": m,
            "fromDate": start.strftime("%Y-%m-%d"),
            "toDate":   end.strftime("%Y-%m-%d"),
            # !!! don't send 'status' here; it narrows results unexpectedly
        }
        try:
            r = requests.get(API_SEARCH, params=params, timeout=30)
            if r.status_code != 200: continue
            ops = _extract_ops(r.json())
            if ops: all_ops.extend(ops)
        except Exception:
            continue
    return all_ops

def latest_cards_df() -> pd.DataFrame:
    ops = fetch_ops("repo", YTD_START, TODAY) + fetch_ops("reverserepo", YTD_START, TODAY)
    if not ops: return pd.DataFrame(columns=["date","operationType","amount_bil"])
    df = pd.json_normalize(ops)
    df["operationDate"] = pd.to_datetime(df["operationDate"], errors="coerce")
    last_day = df["operationDate"].max().date()

    sums = {}
    for op in ops:
        d = pd.to_datetime(op.get("operationDate"), errors="coerce")
        if pd.isna(d) or d.date()!=last_day: continue
        t = op.get("operationType")
        sums.setdefault(t, 0.0)
        sums[t] += _accepted_usd(op)

    rows = [{"date": last_day, "operationType": t, "amount_bil": usd/1e9}
            for t, usd in sums.items() if usd>0]
    return pd.DataFrame(rows).sort_values("operationType")

def ytd_series(op_label: str) -> pd.DataFrame:
    op_param = "repo" if op_label=="Repo" else "reverserepo"
    ops = fetch_ops(op_param, YTD_START, TODAY)
    daily = {}
    for op in ops:
        if op.get("operationType") != op_label: continue
        d = pd.to_datetime(op.get("operationDate"), errors="coerce")
        if pd.isna(d): continue
        dd = d.date()
        if dd < YTD_START or dd > TODAY: continue
        usd = _accepted_usd(op)
        if usd <= 0: continue
        daily[dd] = daily.get(dd, 0.0) + usd
    if not daily:
        return pd.DataFrame(columns=["date","operationType","amount_bil"])
    return (pd.DataFrame([{"date": k, "operationType": op_label, "amount_bil": v/1e9}
                          for k,v in daily.items()])
            .sort_values("date"))

# ---------------- Row 1: Latest ----------------
st.markdown("### Latest data — Accepted Amounts ($B)")
latest = latest_cards_df()
c1, c2 = st.columns(2)

def show_card(col, df, label):
    with col:
        with st.container(border=True):
            st.caption(label)
            row = df[df["operationType"]==label]
            if row.empty:
                st.info("No amount.")
            else:
                d = row["date"].iloc[0]
                v = row["amount_bil"].iloc[0]
                st.markdown(f"**{d:%b %d, %Y}**")
                st.metric("Amount ($B)", f"{v:,.3f}")

show_card(c1, latest, "Repo")
show_card(c2, latest, "Reverse Repo")

st.divider()

# ---------------- Row 2: YTD grouped bars ----------------
st.markdown("### Since 01-01-2025 — Accepted Amounts ($B)")
cl, cr = st.columns([1,1])
with cl: repo_on = st.checkbox("Repo", value=True)
with cr: rr_on   = st.checkbox("Reverse Repo", value=False)

parts = []
if repo_on: parts.append(ytd_series("Repo"))
if rr_on:   parts.append(ytd_series("Reverse Repo"))
ser = pd.concat(parts, ignore_index=True) if parts else pd.DataFrame(columns=["date","operationType","amount_bil"])

if ser.empty:
    st.info("No operations found in the selected period.")
else:
    color_scale = alt.Scale(domain=list(COLOR.keys()), range=[COLOR[k] for k in COLOR])
    # GROUPED bars (side-by-side): use xOffset by series key
    chart = (
        alt.Chart(ser)
        .mark_bar(size=8)
        .encode(
            x=alt.X("date:T", title=None),
            xOffset=alt.XOffset("operationType:N"),
            y=alt.Y("amount_bil:Q", title="$Billions"),
            color=alt.Color("operationType:N", title=None, scale=color_scale),
            tooltip=[
                alt.Tooltip("date:T", title="Date"),
                alt.Tooltip("operationType:N", title="Type"),
                alt.Tooltip("amount_bil:Q", title="Amount ($B)", format=",.3f"),
            ],
        )
        .properties(height=340)
        .configure_axis(grid=False, labelFontSize=12, titleFontSize=12)
    )
    st.altair_chart(chart, use_container_width=True)

with st.expander("Notes"):
    st.markdown("""
- Source: **NY Fed RP results search API** (`/api/rp/results/search.json`).
- We query **treasury, agency, mortgage-backed** per side and aggregate by day.
- Only **accepted amounts** are shown (converted to **$ billions**). 
- Bars are **grouped** when both sides are selected.
""")

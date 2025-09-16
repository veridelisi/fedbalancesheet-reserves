# desk_ops.py
# NY Fed Desk Operations — Repo & Reverse Repo (amounts only)
# pip install streamlit pandas requests altair
# streamlit run desk_ops.py

import requests
import pandas as pd
import altair as alt
import streamlit as st
from datetime import date, timedelta

st.set_page_config(page_title="Desk Ops — Repo & RRP", layout="wide")
st.title("Desk Operations — Repo & Reverse Repo")
st.caption("Accepted amounts only • Latest snapshot and data since 01-01-2025")

API_SEARCH = "https://markets.newyorkfed.org/api/rp/results/search.json"
METHODS = ("treasury", "agency", "mortgagebacked")
START_DATE = date(2025, 1, 1)  # Fixed start date
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
            "toDate": end.strftime("%Y-%m-%d"),
        }
        try:
            r = requests.get(API_SEARCH, params=params, timeout=30)
            if r.status_code != 200: 
                st.warning(f"API call failed for {operation_type_param} {m}: {r.status_code}")
                continue
            data = r.json()
            ops = _extract_ops(data)
            if ops: 
                all_ops.extend(ops)
                st.write(f"✓ Fetched {len(ops)} operations for {operation_type_param} {m}")
        except Exception as e:
            st.error(f"Error fetching {operation_type_param} {m}: {str(e)}")
            continue
    return all_ops

def latest_cards_df() -> pd.DataFrame:
    """Get the latest day's data"""
    with st.spinner("Fetching latest data..."):
        repo_ops = fetch_ops("repo", START_DATE, TODAY)
        rr_ops = fetch_ops("reverserepo", START_DATE, TODAY)
        
    st.write(f"Total repo operations: {len(repo_ops)}")
    st.write(f"Total reverse repo operations: {len(rr_ops)}")
    
    all_ops = repo_ops + rr_ops
    if not all_ops: 
        return pd.DataFrame(columns=["date","operationType","amount_bil"])
    
    # Find the latest date with operations
    dates = []
    for op in all_ops:
        d = pd.to_datetime(op.get("operationDate"), errors="coerce")
        if not pd.isna(d):
            dates.append(d.date())
    
    if not dates:
        return pd.DataFrame(columns=["date","operationType","amount_bil"])
        
    last_day = max(dates)
    st.write(f"Latest operation date: {last_day}")

    # Sum amounts by operation type for the latest day
    sums = {}
    for op in all_ops:
        d = pd.to_datetime(op.get("operationDate"), errors="coerce")
        if pd.isna(d) or d.date() != last_day: 
            continue
        
        t = op.get("operationType", "").strip()
        if not t:
            continue
            
        amount = _accepted_usd(op)
        if amount > 0:
            sums.setdefault(t, 0.0)
            sums[t] += amount
            st.write(f"Added {amount/1e9:.3f}B for {t} on {d.date()}")

    st.write(f"Latest day sums: {sums}")
    
    rows = [{"date": last_day, "operationType": t, "amount_bil": usd/1e9}
            for t, usd in sums.items()]
    return pd.DataFrame(rows).sort_values("operationType") if rows else pd.DataFrame(columns=["date","operationType","amount_bil"])

def get_historical_series(op_label: str) -> pd.DataFrame:
    """Get historical data series from START_DATE to TODAY"""
    op_param = "repo" if op_label == "Repo" else "reverserepo"
    
    with st.spinner(f"Fetching {op_label} historical data..."):
        ops = fetch_ops(op_param, START_DATE, TODAY)
    
    daily = {}
    for op in ops:
        # Check operation type matches
        op_type = op.get("operationType", "").strip()
        if op_type != op_label:
            continue
            
        d = pd.to_datetime(op.get("operationDate"), errors="coerce")
        if pd.isna(d): 
            continue
            
        dd = d.date()
        if dd < START_DATE or dd > TODAY: 
            continue
            
        usd = _accepted_usd(op)
        if usd <= 0: 
            continue
            
        daily[dd] = daily.get(dd, 0.0) + usd
    
    if not daily:
        st.warning(f"No {op_label} data found")
        return pd.DataFrame(columns=["date","operationType","amount_bil"])
    
    st.write(f"Found {len(daily)} days of {op_label} data")
    return (pd.DataFrame([{"date": k, "operationType": op_label, "amount_bil": v/1e9}
                          for k,v in daily.items()])
            .sort_values("date"))

# ---------------- Row 1: Latest ----------------
st.markdown("### Latest data — Accepted Amounts ($B)")

# Add debug toggle
debug_mode = st.sidebar.checkbox("Debug Mode", value=True)

latest = latest_cards_df()
c1, c2 = st.columns(2)

def show_card(col, df, label):
    with col:
        with st.container(border=True):
            st.caption(label)
            if df.empty:
                st.info("No data available.")
                return
                
            row = df[df["operationType"] == label]
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

# ---------------- Row 2: Historical Data ----------------
st.markdown(f"### Since {START_DATE:%m-%d-%Y} — Accepted Amounts ($B)")
cl, cr = st.columns([1,1])
with cl: repo_on = st.checkbox("Repo", value=True)
with cr: rr_on = st.checkbox("Reverse Repo", value=False)

parts = []
if repo_on: 
    repo_data = get_historical_series("Repo")
    if not repo_data.empty:
        parts.append(repo_data)

if rr_on:   
    rr_data = get_historical_series("Reverse Repo")
    if not rr_data.empty:
        parts.append(rr_data)

ser = pd.concat(parts, ignore_index=True) if parts else pd.DataFrame(columns=["date","operationType","amount_bil"])

if ser.empty:
    st.info("No operations found in the selected period.")
else:
    # Summary statistics
    st.markdown("#### Summary Statistics")
    if not ser.empty:
        summary_cols = st.columns(len(ser["operationType"].unique()))
        
        for i, op_type in enumerate(ser["operationType"].unique()):
            op_data = ser[ser["operationType"] == op_type]["amount_bil"]
            with summary_cols[i]:
                st.metric(
                    f"{op_type} - Total", 
                    f"${op_data.sum():,.1f}B",
                    help=f"Average: ${op_data.mean():,.1f}B | Count: {len(op_data)} days"
                )
    
    # Chart
    color_scale = alt.Scale(domain=list(COLOR.keys()), range=[COLOR[k] for k in COLOR])
    
    chart = (
        alt.Chart(ser)
        .mark_bar(size=8)
        .encode(
            x=alt.X("date:T", title="Date"),
            xOffset=alt.XOffset("operationType:N") if len(ser["operationType"].unique()) > 1 else alt.value(0),
            y=alt.Y("amount_bil:Q", title="$Billions"),
            color=alt.Color("operationType:N", title=None, scale=color_scale),
            tooltip=[
                alt.Tooltip("date:T", title="Date"),
                alt.Tooltip("operationType:N", title="Type"),
                alt.Tooltip("amount_bil:Q", title="Amount ($B)", format=",.3f"),
            ],
        )
        .properties(height=400)
        .configure_axis(grid=False, labelFontSize=12, titleFontSize=12)
    )
    
    st.altair_chart(chart, use_container_width=True)
    
    # Data table for verification
    if debug_mode:
        st.markdown("#### Data Table (Debug)")
        st.dataframe(ser.sort_values("date", ascending=False))

with st.expander("Notes"):
    st.markdown(f"""
- Source: **NY Fed RP results search API** (`/api/rp/results/search.json`).
- Data period: **{START_DATE:%m-%d-%Y}** to **{TODAY:%m-%d-%Y}**.
- We query **treasury, agency, mortgage-backed** per side and aggregate by day.
- Only **accepted amounts** are shown (converted to **$ billions**). 
- Bars are **grouped** when both sides are selected.
- Latest cards show the most recent day with operations.
""")
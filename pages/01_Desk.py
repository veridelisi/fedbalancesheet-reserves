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
st.caption("Accepted amounts only • Historical data analysis")

API_SEARCH = "https://markets.newyorkfed.org/api/rp/results/search.json"
METHODS = ("treasury", "agency", "mortgagebacked")
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
        }
        try:
            r = requests.get(API_SEARCH, params=params, timeout=30)
            if r.status_code != 200: continue
            ops = _extract_ops(r.json())
            if ops: all_ops.extend(ops)
        except Exception:
            continue
    return all_ops

def latest_cards_df(start_date: date, end_date: date) -> pd.DataFrame:
    ops = fetch_ops("repo", start_date, end_date) + fetch_ops("reverserepo", start_date, end_date)
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

def get_historical_series(op_label: str, start_date: date, end_date: date, 
                         aggregation: str = "daily") -> pd.DataFrame:
    """
    Get historical data series with different aggregation options
    aggregation: 'daily', 'weekly', 'monthly'
    """
    op_param = "repo" if op_label=="Repo" else "reverserepo"
    ops = fetch_ops(op_param, start_date, end_date)
    daily = {}
    
    for op in ops:
        if op.get("operationType") != op_label: continue
        d = pd.to_datetime(op.get("operationDate"), errors="coerce")
        if pd.isna(d): continue
        dd = d.date()
        if dd < start_date or dd > end_date: continue
        usd = _accepted_usd(op)
        if usd <= 0: continue
        daily[dd] = daily.get(dd, 0.0) + usd
    
    if not daily:
        return pd.DataFrame(columns=["date","operationType","amount_bil"])
    
    # Convert to DataFrame
    df = pd.DataFrame([{"date": k, "operationType": op_label, "amount_bil": v/1e9}
                      for k,v in daily.items()])
    df["date"] = pd.to_datetime(df["date"])
    df = df.sort_values("date")
    
    # Apply aggregation
    if aggregation == "weekly":
        df = df.set_index("date").resample("W").agg({
            "amount_bil": "sum",
            "operationType": "first"
        }).reset_index()
    elif aggregation == "monthly":
        df = df.set_index("date").resample("M").agg({
            "amount_bil": "sum", 
            "operationType": "first"
        }).reset_index()
    
    return df

# Sidebar for date range selection
st.sidebar.header("Date Range Selection")

# Predefined time periods
time_periods = {
    "Last 7 days": (TODAY - timedelta(days=7), TODAY),
    "Last 30 days": (TODAY - timedelta(days=30), TODAY), 
    "Last 90 days": (TODAY - timedelta(days=90), TODAY),
    "YTD 2025": (date(2025, 1, 1), TODAY),
    "2024": (date(2024, 1, 1), date(2024, 12, 31)),
    "2023": (date(2023, 1, 1), date(2023, 12, 31)),
    "Custom": None
}

selected_period = st.sidebar.selectbox("Select Time Period", list(time_periods.keys()))

if selected_period == "Custom":
    col1, col2 = st.sidebar.columns(2)
    with col1:
        start_date = st.date_input("Start Date", value=TODAY - timedelta(days=90))
    with col2:
        end_date = st.date_input("End Date", value=TODAY)
else:
    start_date, end_date = time_periods[selected_period]

# Aggregation selection
aggregation = st.sidebar.selectbox("Data Aggregation", ["daily", "weekly", "monthly"])

# ---------------- Row 1: Latest ----------------
st.markdown("### Latest data — Accepted Amounts ($B)")
latest = latest_cards_df(start_date, end_date)
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

# ---------------- Row 2: Historical Data ----------------
st.markdown(f"### {selected_period} — Accepted Amounts ($B)")
cl, cr = st.columns([1,1])
with cl: repo_on = st.checkbox("Repo", value=True)
with cr: rr_on   = st.checkbox("Reverse Repo", value=False)

# Show progress bar for data loading
if repo_on or rr_on:
    with st.spinner("Loading historical data..."):
        parts = []
        if repo_on: 
            parts.append(get_historical_series("Repo", start_date, end_date, aggregation))
        if rr_on:   
            parts.append(get_historical_series("Reverse Repo", start_date, end_date, aggregation))
        
        ser = pd.concat(parts, ignore_index=True) if parts else pd.DataFrame(columns=["date","operationType","amount_bil"])

    if ser.empty:
        st.info("No operations found in the selected period.")
    else:
        # Summary statistics
        st.markdown("#### Summary Statistics")
        summary_cols = st.columns(len(ser["operationType"].unique()) if not ser.empty else 1)
        
        for i, op_type in enumerate(ser["operationType"].unique()):
            op_data = ser[ser["operationType"] == op_type]["amount_bil"]
            with summary_cols[i]:
                st.metric(
                    f"{op_type} - Total", 
                    f"${op_data.sum():,.1f}B",
                    help=f"Average: ${op_data.mean():,.1f}B"
                )
        
        # Chart
        color_scale = alt.Scale(domain=list(COLOR.keys()), range=[COLOR[k] for k in COLOR])
        
        # Choose chart type based on aggregation
        if aggregation == "daily" and len(ser) > 50:
            # Line chart for many daily data points
            chart = (
                alt.Chart(ser)
                .mark_line(point=True, strokeWidth=2)
                .encode(
                    x=alt.X("date:T", title="Date"),
                    y=alt.Y("amount_bil:Q", title="$Billions"),
                    color=alt.Color("operationType:N", title=None, scale=color_scale),
                    tooltip=[
                        alt.Tooltip("date:T", title="Date"),
                        alt.Tooltip("operationType:N", title="Type"),
                        alt.Tooltip("amount_bil:Q", title="Amount ($B)", format=",.3f"),
                    ],
                )
            )
        else:
            # Bar chart for weekly/monthly or fewer daily points
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
            )
        
        chart = chart.properties(height=400).configure_axis(grid=False, labelFontSize=12, titleFontSize=12)
        st.altair_chart(chart, use_container_width=True)
        
        # Data download
        st.markdown("#### Download Data")
        csv = ser.to_csv(index=False)
        st.download_button(
            "Download CSV",
            csv,
            f"fed_desk_ops_{start_date}_{end_date}.csv",
            "text/csv"
        )

with st.expander("Notes"):
    st.markdown("""
- Source: **NY Fed RP results search API** (`/api/rp/results/search.json`).
- We query **treasury, agency, mortgage-backed** per side and aggregate by day.
- Only **accepted amounts** are shown (converted to **$ billions**). 
- Historical data can be viewed with different time periods and aggregations.
- Data is cached for 15 minutes to improve performance.
- Use the sidebar to select different time periods and aggregation levels.
""")
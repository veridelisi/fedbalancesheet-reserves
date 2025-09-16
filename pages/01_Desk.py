# desk_ops.py
# NY Fed Desk Operations — Repo & Reverse Repo (amounts only)
# - Row 1: latest accepted amounts ($B) for Repo & Reverse Repo
# - Row 2: YTD (since 01-01-2025) daily bar chart of accepted amounts ($B)
# Run:  pip install streamlit pandas requests altair
#       streamlit run desk_ops.py

import requests
import pandas as pd
import altair as alt
import streamlit as st
from datetime import date

# ----------------------------- Page setup ------------------------------
st.set_page_config(page_title="Desk Operations — Repo & Reverse Repo", layout="wide")
st.title("Desk Operations — Repo & Reverse Repo")
st.caption("Amounts only • Latest snapshot and YTD bars (since 01-01-2025)")

# ----------------------------- Constants -------------------------------
API_SEARCH = "https://markets.newyorkfed.org/api/rp/results/search.json"
METHODS = ("treasury", "agency", "mortgagebacked")
YTD_START = date(2025, 1, 1)
TODAY = date.today()

COLOR_MAP = {"Repo": "#1f77b4", "Reverse Repo": "#d62728"}

# ----------------------------- Helpers ---------------------------------
def _to_float(x):
    try:
        return float(x)
    except Exception:
        try:
            return float(str(x).replace(",", ""))
        except Exception:
            return None


def _extract_operations(js: dict):
    """
    Be tolerant to container shape.
    Typical shape is {'repo': {'operations': [ ... ]}}
    but we probe other obvious spots too.
    """
    if not isinstance(js, dict):
        return []
    # 1) canonical
    if "repo" in js and isinstance(js["repo"], dict):
        ops = js["repo"].get("operations")
        if isinstance(ops, list):
            return ops
    # 2) direct 'operations'
    if "operations" in js and isinstance(js["operations"], list):
        return js["operations"]
    # 3) hunt one level down
    for v in js.values():
        if isinstance(v, dict) and isinstance(v.get("operations"), list):
            return v["operations"]
    return []


def _amount_from_details(op: dict) -> float:
    """
    Sum accepted amounts from details (USD). Fallback to top-level totals.
    """
    total = 0.0
    for d in (op.get("details") or []):
        a = _to_float(d.get("amtAccepted"))
        if a is not None:
            total += a
    if total == 0 and op.get("totalAmtAccepted") is not None:
        v = _to_float(op.get("totalAmtAccepted"))
        if v:
            total += v
    return total  # USD


@st.cache_data(ttl=60 * 15, show_spinner=False)
def fetch_ops_history(operation_type_param: str, start: date, end: date):
    """
    Pull operations for a given operationType ('repo' or 'reverserepo'),
    looping over all METHODS to capture all days. Returns a list of ops.
    """
    all_ops = []
    for m in METHODS:
        params = {
            "operationType": operation_type_param,  # 'repo' | 'reverserepo'
            "method": m,
            "status": "results",
            "fromDate": start.strftime("%Y-%m-%d"),
            "toDate": end.strftime("%Y-%m-%d"),
        }
        try:
            r = requests.get(API_SEARCH, params=params, timeout=30)
            if r.status_code != 200:
                continue
            js = r.json()
            ops = _extract_operations(js)
            if ops:
                all_ops.extend(ops)
        except Exception:
            # be robust to intermittent issues
            continue
    return all_ops


def ytd_amount_series(op_label: str) -> pd.DataFrame:
    """
    Build daily accepted-amount series since YTD_START for a given operation type label:
      op_label ∈ {'Repo', 'Reverse Repo'}
    """
    op_param = "repo" if op_label == "Repo" else "reverserepo"
    ops = fetch_ops_history(op_param, YTD_START, TODAY)

    daily_usd = {}
    for op in ops:
        # Make sure we only aggregate the desired label (server returns a 'operationType' field)
        if op.get("operationType") != op_label:
            continue
        d = pd.to_datetime(op.get("operationDate"), errors="coerce")
        if pd.isna(d):
            continue
        if d.date() < YTD_START or d.date() > TODAY:
            continue
        usd = _amount_from_details(op)
        if usd <= 0:
            continue
        daily_usd[d.date()] = daily_usd.get(d.date(), 0.0) + usd

    if not daily_usd:
        return pd.DataFrame(columns=["date", "operationType", "amount_bil"])

    df = pd.DataFrame(
        [{"date": k, "operationType": op_label, "amount_bil": v / 1e9} for k, v in daily_usd.items()]
    ).sort_values("date")
    return df


def latest_amounts_cards() -> pd.DataFrame:
    """
    Compute the latest date across both types and show amounts for that date.
    Returns a tidy DF with columns: date, operationType, amount_bil
    """
    repo_ops = fetch_ops_history("repo", YTD_START, TODAY)
    rr_ops = fetch_ops_history("reverserepo", YTD_START, TODAY)
    all_ops = repo_ops + rr_ops
    if not all_ops:
        return pd.DataFrame(columns=["date", "operationType", "amount_bil"])

    # Identify latest day present
    df = pd.json_normalize(all_ops)
    df["operationDate"] = pd.to_datetime(df["operationDate"], errors="coerce")
    latest_day = df["operationDate"].max().date()

    # Sum by operationType for that day
    buckets = {}
    for op in all_ops:
        d = pd.to_datetime(op.get("operationDate"), errors="coerce")
        if pd.isna(d) or d.date() != latest_day:
            continue
        t = op.get("operationType")  # 'Repo' or 'Reverse Repo'
        buckets.setdefault(t, 0.0)
        buckets[t] += _amount_from_details(op)

    rows = []
    for t, usd in buckets.items():
        if usd and usd > 0:
            rows.append({"date": latest_day, "operationType": t, "amount_bil": usd / 1e9})
    return pd.DataFrame(rows).sort_values("operationType")


# ----------------------------- Row 1: Latest ---------------------------
st.markdown("### Latest data — Accepted Amounts ($B)")

latest_df = latest_amounts_cards()
colL, colR = st.columns(2)


def _latest_card(col, df, label):
    with col:
        with st.container(border=True):
            st.caption(label)
            row = df[df["operationType"] == label]
            if row.empty:
                st.info("No amount.")
            else:
                d = row["date"].iloc[0]
                v = row["amount_bil"].iloc[0]
                st.markdown(f"**{d.strftime('%b %d, %Y')}**")
                st.metric("Amount ($B)", f"{v:,.3f}")


_latest_card(colL, latest_df, "Repo")
_latest_card(colR, latest_df, "Reverse Repo")

st.divider()

# ----------------------------- Row 2: YTD bars -------------------------
st.markdown("### Since 01-01-2025 — Accepted Amounts ($B)")

cbox1, cbox2 = st.columns([1, 1])
with cbox1:
    repo_on = st.checkbox("Repo", value=True)
with cbox2:
    rr_on = st.checkbox("Reverse Repo", value=False)

series_parts = []
if repo_on:
    series_parts.append(ytd_amount_series("Repo"))
if rr_on:
    series_parts.append(ytd_amount_series("Reverse Repo"))

series_df = (
    pd.concat(series_parts, ignore_index=True)
    if series_parts
    else pd.DataFrame(columns=["date", "operationType", "amount_bil"])
)

if series_df.empty:
    st.info("No operations found in the selected period.")
else:
    color = alt.Scale(domain=list(COLOR_MAP.keys()), range=[COLOR_MAP[k] for k in COLOR_MAP])
    chart = (
        alt.Chart(series_df)
        .mark_bar(size=6)
        .encode(
            x=alt.X("date:T", title=None),
            y=alt.Y("amount_bil:Q", title="$Billions"),
            color=alt.Color("operationType:N", title=None, scale=color),
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

# ----------------------------- Notes -----------------------------------
with st.expander("Notes"):
    st.markdown(
        """
- Source: NY Fed **Repo & Reverse Repo operations** (`/api/rp/results/search.json`).
- We query **treasury, agency, mortgage-backed** methods per side to ensure complete history.
- Amounts are the **accepted** dollars aggregated per day and shown in **$ billions**.
- Only amounts are displayed; **no rates** here.
        """
    )

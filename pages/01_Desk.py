# pages/02_DeskOperations.py
# Desk Operations — Repo / Reverse Repo / Securities Lending (NY Fed)
# Run via your Streamlit app navigation

import streamlit as st
import pandas as pd
import requests
from datetime import datetime, date
import altair as alt

st.set_page_config(page_title="Desk Operations — Repo / RR / SLO", layout="wide")

# -------------------- UI header --------------------
st.markdown("## 🏛️ Desk Operations")
st.caption("Latest operations from the New York Fed Desk — Repo, Reverse Repo, and Securities Lending")

# -------------------- API base & helpers --------------------
BASE = "https://markets.newyorkfed.org"
SESSION = requests.Session()
TIMEOUT = 25

# Operation labels
OPS = {
    "repo": "Repo",
    "reverserepo": "Reverse Repo",
    "slo": "Securities Lending",
}

# Methods under /api/rp — collateral buckets we’ll try
RP_METHODS = ["treasury", "agency", "mortgagebacked"]  # we will attempt all; API returns what exists

def _get_json(url, params=None):
    try:
        r = SESSION.get(url, params=params, timeout=TIMEOUT)
        r.raise_for_status()
        return r.json()
    except Exception:
        return None

def _try_rp_latest(operationType: str):
    """
    Try a cascade of endpoints to obtain the most recent RESULTS for a given RP opType.
    Returns a DataFrame with columns: date, operationType, method, accepted_bil, wa_rate
    """
    rows = []

    # priority 1: latest.json for each method
    for m in RP_METHODS:
        url = f"{BASE}/api/rp/{operationType}/{m}/results/latest.json"
        js = _get_json(url)
        if js and isinstance(js, dict):
            payload = js.get("results") or js.get("data") or js
            # normalize to list
            items = payload if isinstance(payload, list) else [payload]
            for it in items:
                # fields are brittle across endpoints; try common names
                acc = it.get("accepted") or it.get("acceptedAmount") or it.get("acceptedAmountBillion") or it.get("acceptedAmountInBillions")
                wa  = it.get("weightedAverage") or it.get("weightedAvgRate") or it.get("weightedAverageRate")
                d   = it.get("operationDate") or it.get("date") or it.get("asOfDate")
                if acc is not None and wa is not None and d:
                    try:
                        acc = float(str(acc).replace(",", ""))
                        wa  = float(str(wa))
                        dt  = pd.to_datetime(d).date()
                        rows.append({"date": dt, "operationType": operationType, "method": m,
                                     "accepted_bil": acc, "wa_rate": wa})
                    except Exception:
                        pass

    if rows:
        df = pd.DataFrame(rows)
        # if multiple methods same date, keep the latest date
        latest_d = df["date"].max()
        return df[df["date"] == latest_d].reset_index(drop=True)

    # priority 2: lastTwoWeeks.json then take the latest
    rows = []
    for m in RP_METHODS:
        url = f"{BASE}/api/rp/{operationType}/{m}/results/lastTwoWeeks.json"
        js = _get_json(url)
        if js and isinstance(js, dict):
            items = js.get("results") or js.get("data") or js
            items = items if isinstance(items, list) else [items]
            for it in items:
                acc = it.get("accepted") or it.get("acceptedAmount") or it.get("acceptedAmountBillion") or it.get("acceptedAmountInBillions")
                wa  = it.get("weightedAverage") or it.get("weightedAvgRate") or it.get("weightedAverageRate")
                d   = it.get("operationDate") or it.get("date") or it.get("asOfDate")
                if acc is not None and wa is not None and d:
                    try:
                        acc = float(str(acc).replace(",", ""))
                        wa  = float(str(wa))
                        dt  = pd.to_datetime(d).date()
                        rows.append({"date": dt, "operationType": operationType, "method": m,
                                     "accepted_bil": acc, "wa_rate": wa})
                    except Exception:
                        pass
    if rows:
        df = pd.DataFrame(rows)
        latest_d = df["date"].max()
        return df[df["date"] == latest_d].reset_index(drop=True)

    return pd.DataFrame(columns=["date","operationType","method","accepted_bil","wa_rate"])

def _try_rp_since(operationType: str, start: date):
    """
    Time series since 'start' for a given RP operationType (repo or reverserepo).
    Query generic search endpoint; aggregate across methods by date.
    Returns df with columns date, op, accepted_bil, wa_rate (weighted by accepted).
    """
    url = f"{BASE}/api/rp/results/search.json"
    params = {
        "operationType": operationType,   # let server filter op type
        "fromDate": start.strftime("%Y-%m-%d"),
        "toDate": date.today().strftime("%Y-%m-%d"),
    }
    js = _get_json(url, params=params)
    if not js:
        return pd.DataFrame(columns=["date","op","accepted_bil","wa_rate"])

    items = js.get("results") or js.get("data") or js
    if not isinstance(items, list):
        items = [items]

    rows = []
    for it in items:
        d   = it.get("operationDate") or it.get("date") or it.get("asOfDate")
        acc = it.get("accepted") or it.get("acceptedAmount") or it.get("acceptedAmountBillion") or it.get("acceptedAmountInBillions")
        wa  = it.get("weightedAverage") or it.get("weightedAvgRate") or it.get("weightedAverageRate")
        if d:
            try:
                dt = pd.to_datetime(d).date()
            except Exception:
                continue
            acc_f = None if acc is None else float(str(acc).replace(",", ""))
            wa_f  = None if wa  is None else float(str(wa))
            rows.append({"date": dt, "accepted_bil": acc_f, "wa_rate": wa_f})
    if not rows:
        return pd.DataFrame(columns=["date","op","accepted_bil","wa_rate"])
    df = pd.DataFrame(rows)

    # aggregate by date across methods (sum accepted; weighted average of rate by accepted)
    def _agg(g):
        acc_sum = pd.to_numeric(g["accepted_bil"], errors="coerce").fillna(0).sum()
        if acc_sum > 0:
            wa = (pd.to_numeric(g["wa_rate"], errors="coerce").fillna(0) * pd.to_numeric(g["accepted_bil"], errors="coerce").fillna(0)).sum() / acc_sum
        else:
            wa = None
        return pd.Series({"accepted_bil": acc_sum if acc_sum > 0 else None, "wa_rate": wa})
    out = df.groupby("date", as_index=False).apply(_agg)
    out["op"] = OPS.get(operationType, operationType)
    return out.dropna(subset=["accepted_bil","wa_rate"], how="all").sort_values("date")

# --- Securities Lending (desk securities lending operations) ---
def _try_slo_latest():
    # try a few plausible endpoints
    cand = [
        f"{BASE}/api/slo/results/latest.json",
        f"{BASE}/api/slo/latest.json",
        f"{BASE}/api/slo/search.json",  # might return nothing without params—handled below
    ]
    for url in cand:
        js = _get_json(url)
        if js and isinstance(js, dict):
            items = js.get("results") or js.get("data") or js
            items = items if isinstance(items, list) else [items]
            rows = []
            for it in items:
                d   = it.get("operationDate") or it.get("date") or it.get("asOfDate")
                acc = it.get("accepted") or it.get("acceptedAmountBillion") or it.get("acceptedAmountInBillions") or it.get("acceptedAmount")
                wa  = it.get("weightedAverage") or it.get("weightedAverageRate") or it.get("weightedAvgRate")
                if d:
                    try:
                        dt = pd.to_datetime(d).date()
                        if acc is not None and wa is not None:
                            rows.append({"date": dt, "accepted_bil": float(str(acc).replace(",", "")), "wa_rate": float(str(wa))})
                    except Exception:
                        pass
            if rows:
                df = pd.DataFrame(rows).sort_values("date")
                return df[df["date"] == df["date"].max()].reset_index(drop=True)
    return pd.DataFrame(columns=["date","accepted_bil","wa_rate"])

def _try_slo_since(start: date):
    cand = [
        (f"{BASE}/api/slo/results/search.json", {"fromDate": start.strftime("%Y-%m-%d"), "toDate": date.today().strftime("%Y-%m-%d")}),
        (f"{BASE}/api/slo/search.json", {"fromDate": start.strftime("%Y-%m-%d"), "toDate": date.today().strftime("%Y-%m-%d")}),
    ]
    for url, params in cand:
        js = _get_json(url, params=params)
        if js and isinstance(js, dict):
            items = js.get("results") or js.get("data") or js
            items = items if isinstance(items, list) else [items]
            rows = []
            for it in items:
                d   = it.get("operationDate") or it.get("date") or it.get("asOfDate")
                acc = it.get("accepted") or it.get("acceptedAmountBillion") or it.get("acceptedAmountInBillions") or it.get("acceptedAmount")
                wa  = it.get("weightedAverage") or it.get("weightedAverageRate") or it.get("weightedAvgRate")
                if d:
                    try:
                        dt = pd.to_datetime(d).date()
                        acc_f = None if acc is None else float(str(acc).replace(",", ""))
                        wa_f  = None if wa  is None else float(str(wa))
                        rows.append({"date": dt, "accepted_bil": acc_f, "wa_rate": wa_f})
                    except Exception:
                        pass
            if rows:
                df = pd.DataFrame(rows).dropna(subset=["wa_rate","accepted_bil"], how="all").sort_values("date")
                df["op"] = "Securities Lending"
                return df
    return pd.DataFrame(columns=["date","op","accepted_bil","wa_rate"])

# -------------------- 1) Latest cards --------------------
st.markdown("### Latest — if operations occurred today")
latest_cols = st.columns(3)

# Repo latest (aggregate across methods)
repo_latest = _try_rp_latest("repo")
if not repo_latest.empty:
    d0 = repo_latest["date"].max()
    # Accepted-weighted average across methods
    acc_sum = repo_latest["accepted_bil"].sum()
    wa = (repo_latest["wa_rate"] * repo_latest["accepted_bil"]).sum() / acc_sum if acc_sum > 0 else None
    with latest_cols[0]:
        with st.container(border=True):
            st.caption(f"Repo — {d0.strftime('%b %d, %Y')}")
            if acc_sum and wa is not None:
                st.markdown(f"**Accepted ($B):** {acc_sum:,.3f}")
                st.markdown(f"**Weighted Avg Rate (%):** {wa:,.2f}")
            else:
                st.info("No accepted amount today.")
else:
    with latest_cols[0]:
        with st.container(border=True):
            st.caption("Repo")
            st.info("No operation today.")

# Reverse Repo latest
rr_latest = _try_rp_latest("reverserepo")
if not rr_latest.empty:
    d1 = rr_latest["date"].max()
    acc_sum = rr_latest["accepted_bil"].sum()
    wa = (rr_latest["wa_rate"] * rr_latest["accepted_bil"]).sum() / acc_sum if acc_sum > 0 else None
    with latest_cols[1]:
        with st.container(border=True):
            st.caption(f"Reverse Repo — {d1.strftime('%b %d, %Y')}")
            if acc_sum and wa is not None:
                st.markdown(f"**Accepted ($B):** {acc_sum:,.3f}")
                st.markdown(f"**Weighted Avg Rate (%):** {wa:,.2f}")
            else:
                st.info("No accepted amount today.")
else:
    with latest_cols[1]:
        with st.container(border=True):
            st.caption("Reverse Repo")
            st.info("No operation today.")

# Securities Lending latest
slo_latest = _try_slo_latest()
if not slo_latest.empty:
    d2 = slo_latest["date"].max()
    acc_sum = slo_latest["accepted_bil"].sum()
    wa = (slo_latest["wa_rate"] * slo_latest["accepted_bil"]).sum() / acc_sum if acc_sum > 0 else None
    with latest_cols[2]:
        with st.container(border=True):
            st.caption(f"Securities Lending — {d2.strftime('%b %d, %Y')}")
            if acc_sum and wa is not None:
                st.markdown(f"**Accepted ($B):** {acc_sum:,.3f}")
                st.markdown(f"**Weighted Avg Rate (%):** {wa:,.2f}")
            else:
                st.info("No accepted amount today.")
else:
    with latest_cols[2]:
        with st.container(border=True):
            st.caption("Securities Lending")
            st.info("No operation today.")

st.divider()

# -------------------- 2) Since 01-01-2025 — WA Rate --------------------
st.markdown("### Since 01-01-2025 — Weighted Average Rate (%)")
sel_cols = st.columns(3)
with sel_cols[0]:
    show_repo = st.checkbox("Repo", value=True)
with sel_cols[1]:
    show_rr   = st.checkbox("Reverse Repo", value=False)
with sel_cols[2]:
    show_slo  = st.checkbox("Securities Lending", value=False)

START = date(2025, 1, 1)
series_list = []

if show_repo:
    ts_repo = _try_rp_since("repo", START)
    if not ts_repo.empty:
        series_list.append(ts_repo.assign(op="Repo"))
if show_rr:
    ts_rr = _try_rp_since("reverserepo", START)
    if not ts_rr.empty:
        series_list.append(ts_rr.assign(op="Reverse Repo"))
if show_slo:
    ts_slo = _try_slo_since(START)
    if not ts_slo.empty:
        series_list.append(ts_slo.assign(op="Securities Lending"))

ts_rate = pd.concat(series_list, ignore_index=True) if series_list else pd.DataFrame(columns=["date","op","wa_rate"])
ts_rate = ts_rate.dropna(subset=["wa_rate"])

rate_chart = alt.Chart(ts_rate).mark_line().encode(
    x=alt.X("date:T", title="Date"),
    y=alt.Y("wa_rate:Q", title="Weighted Average Rate (%)"),
    color=alt.Color("op:N", title="Series"),
    tooltip=["date:T","op:N", alt.Tooltip("wa_rate:Q", format=".2f")]
).properties(height=320)

st.altair_chart(rate_chart, use_container_width=True)

st.divider()

# -------------------- 3) Since 01-01-2025 — Accepted Amount --------------------
st.markdown("### Since 01-01-2025 — Accepted Amount ($ Billions)")
series_list = []

if show_repo:
    ts_repo = _try_rp_since("repo", START)
    if not ts_repo.empty:
        series_list.append(ts_repo.assign(op="Repo"))
if show_rr:
    ts_rr = _try_rp_since("reverserepo", START)
    if not ts_rr.empty:
        series_list.append(ts_rr.assign(op="Reverse Repo"))
if show_slo:
    ts_slo = _try_slo_since(START)
    if not ts_slo.empty:
        series_list.append(ts_slo.assign(op="Securities Lending"))

ts_amt = pd.concat(series_list, ignore_index=True) if series_list else pd.DataFrame(columns=["date","op","accepted_bil"])
ts_amt = ts_amt.dropna(subset=["accepted_bil"])

amt_chart = alt.Chart(ts_amt).mark_line().encode(
    x=alt.X("date:T", title="Date"),
    y=alt.Y("accepted_bil:Q", title="Accepted ($ Billions)"),
    color=alt.Color("op:N", title="Series"),
    tooltip=["date:T","op:N", alt.Tooltip("accepted_bil:Q", format=",.3f")]
).properties(height=320)

st.altair_chart(amt_chart, use_container_width=True)

st.divider()

# -------------------- 4) Notes --------------------
with st.expander("Notes"):
    st.markdown("""
- **Source**: New York Fed Desk Operations APIs:
  - Repo/Reverse Repo: `/api/rp/...`
  - Securities Lending Operations: `/api/slo/...` (exact path may vary; code tries several standard variants).
- **Latest cards** aggregate across collateral methods (Treasury/Agency/MBS) using **Accepted** amounts as weights for the rate.
- If **Accepted** is empty for the day, the card is hidden (or shown with “No operation today.”).
- Time series start at **01-01-2025**. Only days with accepted amounts and valid weighted-average rates are plotted.
- Endpoints can differ slightly; this page includes fallbacks and will gracefully skip unavailable series.
""")

# -------------------- 5) Footer --------------------
st.markdown(
    "<div style='text-align:center; opacity:0.85; padding-top:6px;'>"
    "Engin Yılmaz · Desk Operations"
    "</div>",
    unsafe_allow_html=True,
)

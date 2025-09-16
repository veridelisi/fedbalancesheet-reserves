# pages/Desk_Table.py
# Bugünden geriye Repo & Reverse Repo günlük accepted tutarları ($B) — TABLO
# pip install streamlit pandas requests
# streamlit run pages/Desk_Table.py

import requests
import pandas as pd
import streamlit as st
from datetime import date

st.set_page_config(page_title="Repo & RRP — Daily Amounts (Table)", layout="wide")
st.title("Repo & Reverse Repo — Daily Accepted Amounts ($B)")

API_SEARCH = "https://markets.newyorkfed.org/api/rp/results/search.json"

def _to_float(x):
    try:
        return float(x)
    except Exception:
        try:
            return float(str(x).replace(",", ""))
        except Exception:
            return None

def _extract_ops(js: dict):
    if not isinstance(js, dict):
        return []
    if "repo" in js and isinstance(js["repo"], dict):
        ops = js["repo"].get("operations")
        if isinstance(ops, list):
            return ops
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
        if a:
            total += a
    if total == 0 and op.get("totalAmtAccepted") is not None:
        v = _to_float(op.get("totalAmtAccepted"))
        if v:
            total += v
    return total

@st.cache_data(ttl=15*60, show_spinner=False)
def fetch_ops(operation_type_param: str, start: str, end: str):
    """
    operation_type_param: 'repo' or 'reverserepo'
    Sadece search.json; method paramı yok, sayfalama denenir, operationId ile dedupe.
    """
    all_ops, seen = [], set()

    def _pull(params):
        try:
            r = requests.get(API_SEARCH, params=params, timeout=30)
            if r.status_code != 200:
                return []
            return _extract_ops(r.json())
        except Exception:
            return []

    pulled = False
    for page_key in ("pageNumber", "page"):
        page = 1
        while True:
            params = {
                "operationType": operation_type_param,
                "fromDate": start,
                "toDate": end,
                page_key: page,
                "pageSize": 200,
            }
            ops = _pull(params)
            if not ops:
                break
            pulled = True
            for op in ops:
                oid = op.get("operationId")
                if oid and oid in seen:
                    continue
                if oid:
                    seen.add(oid)
                all_ops.append(op)
            if len(ops) < 200:
                break
            page += 1
        if pulled:
            break

    if not pulled:
        params = {"operationType": operation_type_param, "fromDate": start, "toDate": end}
        ops = _pull(params)
        for op in ops:
            oid = op.get("operationId")
            if oid and oid in seen:
                continue
            if oid:
                seen.add(oid)
            all_ops.append(op)

    return all_ops

def build_table(from_date: str, to_date: str) -> pd.DataFrame:
    repo_ops = fetch_ops("repo", from_date, to_date)
    rrp_ops  = fetch_ops("reverserepo", from_date, to_date)

    def daily(op_list, label):
        rows = {}
        for op in op_list:
            d = pd.to_datetime(op.get("operationDate"), errors="coerce")
            if pd.isna(d):
                continue
            usd = _accepted_usd(op)
            if usd <= 0:
                continue
            k = d.date()
            rows[k] = rows.get(k, 0.0) + usd
        if not rows:
            return pd.DataFrame(columns=["date", label])
        return pd.DataFrame(
            [{"date": k, label: v/1e9} for k, v in rows.items()]
        )

    df_repo = daily(repo_ops, "Repo ($B)")
    df_rrp  = daily(rrp_ops,  "Reverse Repo ($B)")

    out = pd.merge(df_repo, df_rrp, on="date", how="outer").sort_values("date", ascending=False)
    out["date"] = out["date"].astype(str)
    return out

# --- UI: tarih aralığı (default: 2025-01-01 → bugün) ---
col1, col2 = st.columns(2)
with col1:
    start_str = st.text_input("From (YYYY-MM-DD)", "2025-01-01")
with col2:
    end_str   = st.text_input("To (YYYY-MM-DD)", date.today().strftime("%Y-%m-%d"))

with st.spinner("Loading..."):
    table = build_table(start_str, end_str)

st.dataframe(
    table.rename(columns={"date": "Date"}),
    use_container_width=True,
    hide_index=True
)

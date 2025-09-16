# desk_ops.py
# NY Fed Desk Operations — Repo & Reverse Repo (ACCEPTED AMOUNTS ONLY)
# Row 1: Latest snapshot ($B)
# Row 2: YTD grouped bars (since 01-01-2025)
import requests
import pandas as pd
import altair as alt
import streamlit as st
from datetime import date

st.set_page_config(page_title="Desk Ops — Repo & RRP", layout="wide")
st.title("Desk Operations — Repo & Reverse Repo")
st.caption("Accepted amounts only • Latest snapshot and YTD bars (since 01-01-2025)")

API_SEARCH = "https://markets.newyorkfed.org/api/rp/results/search.json"
YTD_START = date(2025, 1, 1)
TODAY = date.today()
COLORS = {"Repo": "#1f77b4", "Reverse Repo": "#d62728"}

# ---------- utils ----------
def _to_float(x):
    try:
        return float(x)
    except Exception:
        try:
            return float(str(x).replace(",", ""))
        except Exception:
            return None

def _extract_ops(js: dict):
    """Alınan JSON içinden operations listesini bul (çeşitli şemalara dayanıklı)."""
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
    """details[].amtAccepted toplamı; yoksa top-level totalAmtAccepted (USD)."""
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

# ---------- data fetch (NO method loop, WITH pagination & dedupe) ----------
@st.cache_data(ttl=15 * 60, show_spinner=False)
def fetch_ops(operation_type_param: str, start: date, end: date):
    """
    operation_type_param: 'repo' or 'reverserepo'
    search.json için method KULLANMIYORUZ (yoksa duplicate).
    Bazı ortamlarda sayfalama var -> birkaç param varyantını dene.
    """
    all_ops = []
    seen_ids = set()

    def _pull(params):
        try:
            r = requests.get(API_SEARCH, params=params, timeout=30)
            if r.status_code != 200:
                return []
            return _extract_ops(r.json())
        except Exception:
            return []

    # 1) sayfalı dene: pageNumber/page + pageSize
    pulled_any = False
    for page_key in ("pageNumber", "page"):
        page = 1
        while True:
            params = {
                "operationType": operation_type_param,
                "fromDate": start.strftime("%Y-%m-%d"),
                "toDate": end.strftime("%Y-%m-%d"),
                page_key: page,
                "pageSize": 200,
            }
            ops = _pull(params)
            if not ops:
                break
            pulled_any = True
            for op in ops:
                oid = op.get("operationId")
                if oid and oid in seen_ids:
                    continue
                if oid:
                    seen_ids.add(oid)
                all_ops.append(op)
            if len(ops) < 200:
                break
            page += 1
        if pulled_any:
            break

    # 2) fallback: tek sayfa (pagination yoksa)
    if not pulled_any:
        params = {
            "operationType": operation_type_param,
            "fromDate": start.strftime("%Y-%m-%d"),
            "toDate": end.strftime("%Y-%m-%d"),
        }
        ops = _pull(params)
        for op in ops:
            oid = op.get("operationId")
            if oid and oid in seen_ids:
                continue
            if oid:
                seen_ids.add(oid)
            all_ops.append(op)

    return all_ops

def build_daily_series(op_label: str) -> pd.DataFrame:
    """01-01-2025'ten bugüne günlük accepted ($B)."""
    op_param = "repo" if op_label == "Repo" else "reverserepo"
    ops = fetch_ops(op_param, YTD_START, TODAY)

    daily = {}
    for op in ops:
        if op.get("operationType") != op_label:
            continue
        d = pd.to_datetime(op.get("operationDate"), errors="coerce")
        if pd.isna(d):
            continue
        dd = d.date()
        if dd < YTD_START or dd > TODAY:
            continue
        usd = _accepted_usd(op)
        if usd <= 0:
            continue
        daily[dd] = daily.get(dd, 0.0) + usd

    if not daily:
        return pd.DataFrame(columns=["date", "operationType", "amount_bil"])

    return (
        pd.DataFrame(
            [{"date": k, "operationType": op_label, "amount_bil": v / 1e9} for k, v in daily.items()]
        ).sort_values("date")
    )

def latest_cards_df() -> pd.DataFrame:
    ops = fetch_ops("repo", YTD_START, TODAY) + fetch_ops("reverserepo", YTD_START, TODAY)
    if not ops:
        return pd.DataFrame(columns=["date", "operationType", "amount_bil"])
    df = pd.json_normalize(ops)
    df["operationDate"] = pd.to_datetime(df["operationDate"], errors="coerce")
    last_day = df["operationDate"].max().date()

    sums = {}
    for op in ops:
        d = pd.to_datetime(op.get("operationDate"), errors="coerce")
        if pd.isna(d) or d.date() != last_day:
            continue
        t = op.get("operationType")  # 'Repo' / 'Reverse Repo'
        sums.setdefault(t, 0.0)
        sums[t] += _accepted_usd(op)

    rows = [{"date": last_day, "operationType": t, "amount_bil": usd / 1e9} for t, usd in sums.items() if usd > 0]
    return pd.DataFrame(rows).sort_values("operationType")

# ---------- Row 1: Latest ----------
st.markdown("### Latest data — Accepted Amounts ($B)")
latest = latest_cards_df()
lc1, lc2 = st.columns(2)

def _card(col, df, label):
    with col:
        with st.container(border=True):
            st.caption(label)
            row = df[df["operationType"] == label]
            if row.empty:
                st.info("No amount.")
            else:
                d = row["date"].iloc[0]
                v = row["amount_bil"].iloc[0]
                st.markdown(f"**{d:%b %d, %Y}**")
                st.metric("Amount ($B)", f"{v:,.3f}")

_card(lc1, latest, "Repo")
_card(lc2, latest, "Reverse Repo")

st.divider()

# ---------- Row 2: YTD grouped bars ----------
st.markdown("### Since 01-01-2025 — Accepted Amounts ($B)")
cb1, cb2 = st.columns(2)
with cb1:
    repo_on = st.checkbox("Repo", value=True)
with cb2:
    rr_on = st.checkbox("Reverse Repo", value=False)

parts = []
if repo_on:
    parts.append(build_daily_series("Repo"))
if rr_on:
    parts.append(build_daily_series("Reverse Repo"))
series = pd.concat(parts, ignore_index=True) if parts else pd.DataFrame(columns=["date","operationType","amount_bil"])

if series.empty:
    st.info("No operations found in the selected period.")
else:
    color_scale = alt.Scale(domain=list(COLORS.keys()), range=[COLORS[k] for k in COLORS])
    chart = (
        alt.Chart(series)
        .mark_bar(size=8)
        .encode(
            x=alt.X("date:T", title=None),
            xOffset=alt.XOffset("operationType:N"),   # grouped (side-by-side)
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
    st.markdown(
        """
- We use **/api/rp/results/search.json** (no `method` param) to avoid duplicates.
- Results are **de-duplicated by operationId** and aggregated by day.
- Pagination is handled by trying `pageNumber/page` + `pageSize`; if not present, it
  falls back to a single call.
- Only **accepted** amounts are shown, converted to **$ billions**.
- Bars are **grouped** when both sides are selected.
"""
    )

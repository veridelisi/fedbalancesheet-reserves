# ==============================================================
# Public Balance / TGA Cash – Daily Treasury Statement dashboard
# ==============================================================

import requests
import pandas as pd
import altair as alt
from datetime import date, timedelta
from dateutil.relativedelta import relativedelta
import streamlit as st
from textwrap import dedent


st.set_page_config(page_title="Public Balance (Taxes, Expenditures, New Debt, Debt Redemptions)", layout="wide")
# --- Gezinme Barı (Yatay Menü, Streamlit-native) ---
st.markdown("""
<div style="background:#f8f9fa;padding:10px 0 10px 0;margin-bottom:24px;border-radius:8px;display:flex;gap:32px;justify-content:center;">
""", unsafe_allow_html=True)

col1, col2, col3, col4, col5 = st.columns([1,1,1,1,1])
with col1:
    st.page_link("streamlit_app.py", label="🏠 Home")
with col2:
    st.page_link("pages/01_Reserves.py", label="📊 Reserves")
with col3:
    st.page_link("pages/01_Repo.py", label="🔄 Repo")
with col4:
    st.page_link("pages/01_TGA.py", label="🔄 TGA")
with col5:
    st.page_link("pages/01_PublicBalance.py", label="🔄 Public Balance")

# --- Sol menü sakla ---
st.markdown("""
    <style>
        [data-testid="stSidebarNav"] {display: none;}
        section[data-testid="stSidebar"][aria-expanded="true"]{display: none;}
    </style>
    """, unsafe_allow_html=True)

st.title("🏦 Public Balance (Taxes, Expenditures, New Debt, Debt Redemptions)")
st.caption("Latest snapshot • Annual compare (YoY or fixed 2025-01-01) • Daily Top-10 breakdowns")


# -------------------------- Helpers ----------------------------------

BASE = "https://api.fiscaldata.treasury.gov/services/api/fiscal_service"
ENDP = "/v1/accounting/dts/deposits_withdrawals_operating_cash"

def to_float(x):
    try:
        return float(str(x).replace(",", "").strip())
    except Exception:
        return 0.0

def bn(million_value):
    # millions -> billions
    try:
        return float(million_value) / 1000.0
    except Exception:
        return 0.0

def fmt_bn(x):
    # 1-decimal billions
    try:
        return f"{float(x):,.1f}"
    except Exception:
        return "0.0"

@st.cache_data(ttl=1800)
def fetch_latest_window(page_size: int = 500) -> pd.DataFrame:
    """Fetch recent DTS window sorted by date desc."""
    url = f"{BASE}{ENDP}?sort=-record_date&page[size]={page_size}"
    r = requests.get(url, timeout=40)
    r.raise_for_status()
    df = pd.DataFrame(r.json().get("data", []))

    # normalize
    for c in ("record_date", "transaction_type", "transaction_catg", "transaction_today_amt"):
        if c not in df.columns:
            df[c] = None

    df["record_date"] = pd.to_datetime(df["record_date"], errors="coerce").dt.date
    df = df.dropna(subset=["record_date"])
    df["transaction_today_amt"] = df["transaction_today_amt"].apply(to_float)
    return df

def day_slice(df: pd.DataFrame, d: date) -> pd.DataFrame:
    return df[df["record_date"] == d].copy()

def compute_components_for_day(df_day: pd.DataFrame) -> dict:
    """Return taxes, expenditures, newdebt, redemp (+ totals) for a single day."""
    dep = df_day[df_day["transaction_type"] == "Deposits"].copy()
    wdr = df_day[df_day["transaction_type"] == "Withdrawals"].copy()

    # --- Deposits ---
    # Total deposits (Table II)
    dep_total_row = dep[dep["transaction_catg"].str.contains("Total TGA Deposits", na=False)]
    dep_total = dep_total_row["transaction_today_amt"].sum() if not dep_total_row.empty \
                else (dep["transaction_today_amt"].iloc[-1] if len(dep) else 0.0)

    # Public Debt Cash Issues (Table IIIB)
    new_debt_row = dep[dep["transaction_catg"].str.contains("Public Debt Cash Issues", na=False)]
    new_debt = new_debt_row["transaction_today_amt"].sum() if not new_debt_row.empty \
               else (dep["transaction_today_amt"].iloc[-2] if len(dep) >= 2 else 0.0)

    taxes = dep_total - new_debt

    # --- Withdrawals ---
    # Total withdrawals (Table II)
    wdr_total_row = wdr[wdr["transaction_catg"].str.contains("Total TGA Withdrawals", na=False)]
    wdr_total = wdr_total_row["transaction_today_amt"].sum() if not wdr_total_row.empty \
                else (wdr["transaction_today_amt"].iloc[-1] if len(wdr) else 0.0)

    # Public Debt Cash Redemptions (Table IIIB)
    redemp_row = wdr[wdr["transaction_catg"].str.contains("Public Debt Cash Redemptions", na=False)]
    redemp = redemp_row["transaction_today_amt"].sum() if not redemp_row.empty \
             else (wdr["transaction_today_amt"].iloc[-2] if len(wdr) >= 2 else 0.0)

    expenditures = wdr_total - redemp

    return dict(
        taxes=taxes,
        expenditures=expenditures,
        newdebt=new_debt,
        redemp=redemp,
        deposits_total=dep_total,
        withdrawals_total=wdr_total,
    )

# -- Simple Top-10 (your “drop last two rows” logic; also remove null/total/debt names) --
def top10_deposits_simple(df_day: pd.DataFrame, taxes_m: float, n: int = 10) -> pd.DataFrame:
    d = df_day[df_day["transaction_type"] == "Deposits"].copy()
    if len(d) >= 2:
        d = d.iloc[:-2]  # drop (Issues + Total)
    d = d[d["transaction_catg"].notna()]
    d = d[~d["transaction_catg"].str.contains("Total|Public Debt Cash Issues", na=False)]
    d = d[["transaction_catg", "transaction_today_amt"]]
    out = (d.sort_values("transaction_today_amt", ascending=False)
             .head(n)
             .rename(columns={"transaction_catg": "Category", "transaction_today_amt": "Amount (m$)"}))
    out["Percentage in Taxes"] = (out["Amount (m$)"] / taxes_m * 100.0) if taxes_m else 0.0
    return out.reset_index(drop=True)

def top10_withdrawals_simple(df_day: pd.DataFrame, expend_m: float, n: int = 10) -> pd.DataFrame:
    w = df_day[df_day["transaction_type"] == "Withdrawals"].copy()
    if len(w) >= 2:
        w = w.iloc[:-2]  # drop (Redemptions + Total)
    w = w[w["transaction_catg"].notna()]
    w = w[~w["transaction_catg"].str.contains("Total|Public Debt Cash Redemptions", na=False)]
    w = w[["transaction_catg", "transaction_today_amt"]]
    out = (w.sort_values("transaction_today_amt", ascending=False)
             .head(n)
             .rename(columns={"transaction_catg": "Category", "transaction_today_amt": "Amount (m$)"}))
    out["Percentage in Expenditures"] = (out["Amount (m$)"] / expend_m * 100.0) if expend_m else 0.0
    return out.reset_index(drop=True)

# ------------------------- Fetch & compute (latest only) -------------------------

df_all = fetch_latest_window()
if df_all.empty:
    st.error("No data returned from Treasury API.")
    st.stop()

latest_date = df_all["record_date"].max()
df_latest = day_slice(df_all, latest_date)
latest = compute_components_for_day(df_latest)

# values in billions
tax_bn   = bn(latest["taxes"])
nd_bn    = bn(latest["newdebt"])
exp_bn   = bn(latest["expenditures"])
rd_bn    = bn(latest["redemp"])
res_bn   = tax_bn + nd_bn - exp_bn - rd_bn  # Daily Result

# --------------------------- Identity card (4 values + centered result) ---------------------------

identity_html = f"""
<style>
  .tga-card {{
    border:1px solid #e5e7eb; border-radius:12px; background:#fff;
    padding:16px 18px; width:100%;
  }}
  .tga-grid {{
    display:grid;
    grid-template-columns: 1fr auto 1fr auto 1fr auto 1fr;
    grid-template-rows: auto auto;
    column-gap:18px; row-gap:6px; align-items:center;
  }}
  .tga-lbl {{ color:#6b7280; font-weight:600; grid-row:1; }}
  .tga-pill {{
    grid-row:2; display:inline-block; padding:12px 16px;
    border-radius:14px; background:#f6f7f9; font-weight:800; font-size:1.35rem;
  }}
  .tga-blue {{ color:#2563eb; }}
  .tga-red  {{ color:#ef4444; }}
  .tga-op {{ grid-row:2; text-align:center; font-weight:800; font-size:1.6rem; color:#374151; }}

  .tga-result {{
    margin-top:12px; padding-top:12px; border-top:1px dashed #e5e7eb;
    text-align:center; color:#374151; font-size:1.05rem;
  }}
  .tga-result .val {{ font-weight:900; font-size:1.5rem; }}
  .tga-result .pos {{ color:#10b981; }}
  .tga-result .neg {{ color:#ef4444; }}

  @media (max-width: 900px) {{
    .tga-pill {{ font-size:1.1rem; padding:10px 12px; }}
    .tga-op   {{ font-size:1.3rem; }}
  }}
</style>

<div class="tga-card">
  <div class="tga-grid">
    <div class="tga-lbl" style="grid-column:1;">Taxes</div>
    <div class="tga-lbl" style="grid-column:3;">New Debt (IIIB)</div>
    <div class="tga-lbl" style="grid-column:5;">Expenditures</div>
    <div class="tga-lbl" style="grid-column:7;">Debt Redemp (IIIB)</div>

    <div class="tga-pill tga-blue" style="grid-column:1;">{fmt_bn(tax_bn)}</div>
    <div class="tga-op"              style="grid-column:2;">+</div>

    <div class="tga-pill tga-blue"  style="grid-column:3;">{fmt_bn(nd_bn)}</div>
    <div class="tga-op"              style="grid-column:4;">−</div>

    <div class="tga-pill tga-red"   style="grid-column:5;">{fmt_bn(exp_bn)}</div>
    <div class="tga-op"              style="grid-column:6;">−</div>

    <div class="tga-pill tga-red"   style="grid-column:7;">{fmt_bn(rd_bn)}</div>
  </div>

  <div class="tga-result">
    <div>
      Government daily result — {latest_date.strftime('%d.%m.%Y')}
      <span class="val {'pos' if res_bn >= 0 else 'neg'}">
        {'▲' if res_bn >= 0 else '▼'} {fmt_bn(res_bn)}
      </span>
      <span>
        TGA cash has {'increased' if res_bn >= 0 else 'decreased'} by {fmt_bn(abs(res_bn))}.
      </span>
    </div>
  </div>
</div>
"""
with st.container(border=True):
    st.subheader("Latest day identity (billions of $)")
    st.markdown(identity_html, unsafe_allow_html=True)

st.markdown("---")

# ----------------------- Daily Top-10 detail tables ----------------------

st.subheader("Daily Top-10 categories (latest day)")

taxes_total_m  = float(latest.get("taxes", 0.0)) or 0.0
expend_total_m = float(latest.get("expenditures", 0.0)) or 0.0

left, right = st.columns(2)
with left:
    st.markdown("**Taxes — top 10 categories (share of Taxes)**")
    taxes_top = top10_deposits_simple(df_latest, taxes_total_m, n=10)
    if not taxes_top.empty:
        taxes_top["Amount (m$)"] = taxes_top["Amount (m$)"].map(lambda v: f"{v:,.0f}")
        taxes_top["Percentage in Taxes"] = taxes_top["Percentage in Taxes"].round(1).map(lambda v: f"{v:.1f}%")
    st.dataframe(taxes_top, use_container_width=True)

with right:
    st.markdown("**Expenditures — top 10 categories (share of Expenditures)**")
    expend_top = top10_withdrawals_simple(df_latest, expend_total_m, n=10)
    if not expend_top.empty:
        expend_top["Amount (m$)"] = expend_top["Amount (m$)"].map(lambda v: f"{v:,.0f}")
        expend_top["Percentage in Expenditures"] = expend_top["Percentage in Expenditures"].round(1).map(lambda v: f"{v:.1f}%")
    st.dataframe(expend_top, use_container_width=True)

st.markdown("---")

# ---------------------------- Methodology -------------------------------

st.markdown("### Methodology")
st.markdown(
    """
- **Source:** U.S. Treasury – FiscalData `deposits_withdrawals_operating_cash`.
- **Taxes** = **Total TGA Deposits (Table II) − Public Debt Cash Issues (Table IIIB)**.
- **Expenditures** = **Total TGA Withdrawals (Table II) − Public Debt Cash Redemptions (Table IIIB)**.
- **Daily Result** = **Taxes + NewDebt − Expenditures − Redemp** (billions).
- Top-10 tablolarında **IIIB** ve **Total** satırları hariç tutulur; `null` kategoriler temizlenir.
"""
)

st.markdown(
    """
    <hr style="margin-top:20px;margin-bottom:8px;border:none;border-top:1px solid #e5e7eb;">
    <div style="text-align:center;color:#6b7280;font-size:.95rem;">
        <strong>Engin Yılmaz</strong> · Visiting Research Scholar · UMASS Amherst · September 2025
    </div>
    """,
    unsafe_allow_html=True
)
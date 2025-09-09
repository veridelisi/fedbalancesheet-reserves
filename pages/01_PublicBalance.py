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
    """Robust numeric parser (string -> float)."""
    try:
        return float(str(x).replace(",", "").strip())
    except Exception:
        return 0.0

def bn(million_value):
    """Millions -> Billions (float)."""
    try:
        return float(million_value) / 1000.0
    except Exception:
        return 0.0

def fmt_bn(x):
    """Nice 1-dec format for billions."""
    try:
        return f"{float(x):,.1f}"
    except Exception:
        return "0.0"

@st.cache_data(ttl=1800)
def fetch_latest_window(page_size: int = 500) -> pd.DataFrame:
    """
    Pulls a recent window sorted by date desc.
    We then compute per-day metrics from this frame.
    """
    url = f"{BASE}{ENDP}?sort=-record_date&page[size]={page_size}"
    r = requests.get(url, timeout=40)
    r.raise_for_status()
    df = pd.DataFrame(r.json().get("data", []))

    # Ensure expected columns exist
    for c in ("record_date","transaction_type","transaction_catg","transaction_today_amt"):
        if c not in df.columns:
            df[c] = None

    # Normalize
    df["record_date"] = pd.to_datetime(df["record_date"], errors="coerce").dt.date
    df = df.dropna(subset=["record_date"])
    df["transaction_today_amt"] = df["transaction_today_amt"].apply(to_float)
    return df

def nearest_on_or_before(dates: pd.Series, target: date) -> date | None:
    """Return the max(d) where d <= target; dates must be dtype 'date'."""
    if dates.empty:
        return None
    s = pd.Series(sorted(set(d for d in dates if isinstance(d, date))))
    s = s[s <= target]
    return None if s.empty else s.iloc[-1]

def day_slice(df: pd.DataFrame, d: date) -> pd.DataFrame:
    return df[df["record_date"] == d].copy()

# ---- Per-day metrics (Taxes, NewDebt, Expenditures, Redemp) ----
# Dataset düzeni: Gün içi Deposits / Withdrawals kalemleri, son kalem 'Total ...' oluyor.
# Ayrıca IIIB kalemleri: 'Public Debt Cash Issues (Table IIIB)', 'Public Debt Cash Redemptions (Table IIIB)'.

def compute_components_for_day(df_day: pd.DataFrame) -> dict:
    dep = df_day[df_day["transaction_type"] == "Deposits"].copy()
    wdr = df_day[df_day["transaction_type"] == "Withdrawals"].copy()

    # ---- Deposits side ----
    # Total
    dep_total_row = dep[dep["transaction_catg"].str.contains("Total TGA Deposits", na=False)]
    if not dep_total_row.empty:
        dep_total = dep_total_row["transaction_today_amt"].sum()
    else:
        dep_total = dep["transaction_today_amt"].iloc[-1] if len(dep) else 0.0

    # New Debt (IIIB)
    new_debt_row = dep[dep["transaction_catg"].str.contains("Public Debt Cash Issues", na=False)]
    if not new_debt_row.empty:
        new_debt = new_debt_row["transaction_today_amt"].sum()
    else:
        new_debt = dep["transaction_today_amt"].iloc[-2] if len(dep) >= 2 else 0.0

    # Taxes (residual)
    taxes = dep_total - new_debt

    # ---- Withdrawals side ----
    wdr_total_row = wdr[wdr["transaction_catg"].str.contains("Total TGA Withdrawals", na=False)]
    if not wdr_total_row.empty:
        wdr_total = wdr_total_row["transaction_today_amt"].sum()
    else:
        wdr_total = wdr["transaction_today_amt"].iloc[-1] if len(wdr) else 0.0

    redemp_row = wdr[wdr["transaction_catg"].str.contains("Public Debt Cash Redemptions", na=False)]
    if not redemp_row.empty:
        redemp = redemp_row["transaction_today_amt"].sum()
    else:
        redemp = wdr["transaction_today_amt"].iloc[-2] if len(wdr) >= 2 else 0.0

    expenditures = wdr_total - redemp

    return dict(
        taxes=taxes, expenditures=expenditures, newdebt=new_debt, redemp=redemp,
        deposits_total=dep_total, withdrawals_total=wdr_total
    )

def top_n_detail(df_day: pd.DataFrame, typ: str, n: int, base_total_m: float) -> pd.DataFrame:
    """Return top-N detail rows for Deposits or Withdrawals excluding IIIB & Total rows, with % share."""
    sub = df_day[df_day["transaction_type"] == typ].copy()
    if typ == "Deposits":
        # exclude totals & debt issues
        mask = ~sub["transaction_catg"].str.contains("Total TGA Deposits|Public Debt Cash Issues", na=False)
    else:
        mask = ~sub["transaction_catg"].str.contains("Total TGA Withdrawals|Public Debt Cash Redemptions", na=False)
    sub = sub[mask]

    sub = sub[["transaction_catg", "transaction_today_amt"]].copy()
    sub = sub.sort_values("transaction_today_amt", ascending=False).head(n)
    if base_total_m:
        sub["Percentage"] = (sub["transaction_today_amt"] / base_total_m) * 100.0
    else:
        sub["Percentage"] = 0.0
    sub.rename(columns={"transaction_catg":"Category", "transaction_today_amt":"Amount (m$)"}, inplace=True)
    return sub.reset_index(drop=True)

# ------------------------- UI: Title & baseline -------------------------



df_all = fetch_latest_window()
if df_all.empty:
    st.error("No data returned from Treasury API.")
    st.stop()

latest_date = df_all["record_date"].max()

c0, c1 = st.columns([1, 3])
with c0:
    st.markdown(
        f"""
        <div style="display:inline-block;padding:10px 14px;border:1px solid #e5e7eb;border-radius:10px;background:#fafafa;">
            <div style="font-size:0.95rem;color:#6b7280;margin-bottom:2px;">Latest business day</div>
            <div style="font-size:1.15rem;font-weight:600;letter-spacing:0.2px;">{latest_date.strftime('%d.%m.%Y')}</div>
        </div>
        """, unsafe_allow_html=True
    )
with c1:
    baseline_label = st.radio(
        "Annual baseline",
        ("YoY (t − 1 year)", "01.01.2025"),
        horizontal=True,
        index=0
    )

if baseline_label.startswith("YoY"):
    target_baseline = latest_date - relativedelta(years=1)
else:
    target_baseline = date(2025, 1, 1)

baseline_date = nearest_on_or_before(df_all["record_date"], target_baseline)

# ----------------------- Compute latest / baseline -----------------------

df_latest = day_slice(df_all, latest_date)
latest = compute_components_for_day(df_latest)

if baseline_date is not None:
    df_base = day_slice(df_all, baseline_date)
    base = compute_components_for_day(df_base)
else:
    base = None

# --------------------------- Identity big card ---------------------------

tax_bn   = bn(latest["taxes"])
exp_bn   = bn(latest["expenditures"])
nd_bn    = bn(latest["newdebt"])
rd_bn    = bn(latest["redemp"])
res_bn   = tax_bn + nd_bn - exp_bn - rd_bn

res_class = "pos" if res_bn >= 0 else "neg"
res_arrow = "▲" if res_bn >= 0 else "▼"
res_verb  = "increased" if res_bn >= 0 else "decreased"

# --------------------------- Identity (metrics + result line) ---------------------------
with st.container(border=True):
    st.subheader("Latest day identity (billions of $)")

    # 4 değer tek satır
    c1, c2, c3, c4 = st.columns(4)

    with c1:
        st.markdown("**Taxes**")
        st.metric(label="", value=fmt_bn(tax_bn))

    with c2:
        st.markdown("**New Debt (IIIB)**")
        st.metric(label="", value=fmt_bn(nd_bn))

    with c3:
        st.markdown("**Expenditures**")
        st.metric(label="", value=fmt_bn(exp_bn))

    with c4:
        st.markdown("**Debt Redemp (IIIB)**")
        st.metric(label="", value=fmt_bn(rd_bn))

    # Alt satır: günlük sonuç
    res_arrow = "▲" if res_bn >= 0 else "▼"
    res_color = "#10b981" if res_bn >= 0 else "#ef4444"
    res_verb  = "increased" if res_bn >= 0 else "decreased"

    st.markdown(
        f'''
        <div text-align:center;  style="margin-top:10px; padding-top:10px; border-top:1px dashed #e5e7eb;
                    color:#374151; font-size:1.05rem;">
            <span>Government daily result — {latest_date.strftime('%d.%m.%Y')}</span>
            <span style="font-weight:900; margin-left:10px; color:{res_color};">
                {res_arrow} {fmt_bn(res_bn)} 
            </span>
            <span style="margin-left:8px;">
                TGA cash has {res_verb} by {fmt_bn(abs(res_bn))}.
            </span>
        </div>
        ''',
        unsafe_allow_html=True
    )



# ----------------------- Daily Top-10 detail tables ----------------------

st.subheader("Daily Top-10 categories (latest day)")

# Taxes detail (Deposits excluding Issues & Total)
taxes_total_m = latest.get("taxes", 0.0) or 0.0
expend_total_m = latest.get("expenditures", 0.0) or 0.0

left, right = st.columns(2)

with left:
    st.markdown("**Taxes — top 10 categories (share of Taxes)**")
    taxes_top = top_n_detail(df_latest, typ="Deposits", n=10, base_total_m=taxes_total_m)
    if not taxes_top.empty:
        taxes_top["Amount (m$)"] = taxes_top["Amount (m$)"].map(lambda v: f"{v:,.0f}")
        taxes_top["Percentage"] = taxes_top["Percentage"].map(lambda v: f"{v:,.1f}%")
    st.dataframe(taxes_top, use_container_width=True)

with right:
    st.markdown("**Expenditures — top 10 categories (share of Expenditures)**")
    expend_top = top_n_detail(df_latest, typ="Withdrawals", n=10, base_total_m=expend_total_m)
    if not expend_top.empty:
        expend_top["Amount (m$)"] = expend_top["Amount (m$)"].map(lambda v: f"{v:,.0f}")
        expend_top["Percentage"] = expend_top["Percentage"].map(lambda v: f"{v:,.1f}%")
    st.dataframe(expend_top, use_container_width=True)

st.markdown("---")

# ---------------------------- Methodology -------------------------------

st.markdown("### Methodology")
st.markdown(
"""
- **Source:** U.S. Treasury – FiscalData `deposits_withdrawals_operating_cash`.
- **Latest day** = most recent `record_date` available in the API; **baseline** is either
  **YoY (t−1y)** or **fixed 2025-01-01**, using the nearest date **on/before** the target if needed.
- **Taxes** are computed as **Total TGA Deposits (Table II) − Public Debt Cash Issues (Table IIIB)**.
- **Expenditures** are computed as **Total TGA Withdrawals (Table II) − Public Debt Cash Redemptions (Table IIIB)**.
- **Daily Result** = **Taxes + NewDebt − Expenditures − Redemp** (displayed in billions).
- Top-10 tables exclude the **Total** lines and **IIIB** debt lines.
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
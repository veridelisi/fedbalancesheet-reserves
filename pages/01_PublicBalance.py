# ---------------------------------------------------------------
# TGA Flows (Taxes, Expenditures, New Debt, Debt Redemptions)
# Latest snapshot + Annual compare (YoY or fixed 01.01.2025)
# ---------------------------------------------------------------

import requests
import pandas as pd
import altair as alt
from datetime import date, timedelta
from dateutil.relativedelta import relativedelta
import streamlit as st

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


# -------------------------- Helpers --------------------------

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
    return float(million_value) / 1000.0

def fmt_bn(x):
    """Nice 1-dec format for billions."""
    return f"{x:,.1f}"

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
    df["record_date"] = pd.to_datetime(df["record_date"]).dt.date
    df["transaction_today_amt"] = df["transaction_today_amt"].apply(to_float)
    return df

def nearest_on_or_before(dates: pd.Series, target: date) -> date | None:
    """Return the max(d) where d <= target; dates must be dtype 'date'."""
    s = pd.Series(sorted(set(dates)))
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
    dep_total = dep_total_row["transaction_today_amt"].sum() if not dep_total_row.empty else (dep["transaction_today_amt"].iloc[-1] if len(dep) else 0.0)

    # New Debt (IIIB)
    new_debt_row = dep[dep["transaction_catg"].str.contains("Public Debt Cash Issues", na=False)]
    new_debt = new_debt_row["transaction_today_amt"].sum() if not new_debt_row.empty else (dep["transaction_today_amt"].iloc[-2] if len(dep) >= 2 else 0.0)

    # Taxes (residual)
    taxes = dep_total - new_debt

    # ---- Withdrawals side ----
    wdr_total_row = wdr[wdr["transaction_catg"].str.contains("Total TGA Withdrawals", na=False)]
    wdr_total = wdr_total_row["transaction_today_amt"].sum() if not wdr_total_row.empty else (wdr["transaction_today_amt"].iloc[-1] if len(wdr) else 0.0)

    redemp_row = wdr[wdr["transaction_catg"].str.contains("Public Debt Cash Redemptions", na=False)]
    redemp = redemp_row["transaction_today_amt"].sum() if not redemp_row.empty else (wdr["transaction_today_amt"].iloc[-2] if len(wdr) >= 2 else 0.0)

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
    sub["Percentage"] = (sub["transaction_today_amt"] / base_total_m * 100.0) if base_total_m else 0.0
    sub.rename(columns={"transaction_catg":"Category", "transaction_today_amt":"Amount (m$)"}, inplace=True)
    return sub.reset_index(drop=True)

# ------------------------- UI: Title & baseline -------------------------

st.title("Public Balance Position Statement")
st.caption("Daily Treasury Statement • Latest snapshot — taxes, expenditures, and debt cash flows")

df_all = fetch_latest_window()
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
    baseline_label = st.radio("Annual baseline", ("YoY (t − 1 year)", "01.01.2025"), horizontal=True, index=0)

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
    column-gap:16px; row-gap:6px; align-items:center;
  }}
  .tga-lbl {{ color:#6b7280; font-weight:600; grid-row:1; }}
  .tga-pill {{
    grid-row:2; display:inline-block; padding:12px 16px;
    border-radius:14px; background:#f6f7f9; font-weight:800; font-size:1.35rem;
  }}
  .tga-blue {{ color:#2563eb; }}
  .tga-red  {{ color:#ef4444; }}
  .tga-op {{
    grid-row:2; text-align:center; font-weight:800; font-size:1.6rem; color:#374151;
  }}

  .tga-result {{
    margin-top:12px; padding-top:10px; border-top:1px dashed #e5e7eb;
    display:flex; gap:12px; align-items:baseline; flex-wrap:wrap;
  }}
  .tga-result .dt {{ color:#6b7280; }}
  .tga-result .val {{ font-weight:900; font-size:1.5rem; }}
  .tga-result.pos .val {{ color:#10b981; }}
  .tga-result.neg .val {{ color:#ef4444; }}
  .tga-result .exp {{ color:#374151; }}

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

    <div class="tga-pill tga-blue" style="grid-column:3;">{fmt_bn(nd_bn)}</div>
    <div class="tga-op"              style="grid-column:4;">−</div>

    <div class="tga-pill tga-red"  style="grid-column:5;">{fmt_bn(exp_bn)}</div>
    <div class="tga-op"              style="grid-column:6;">−</div>

    <div class="tga-pill tga-red"  style="grid-column:7;">{fmt_bn(rd_bn)}</div>
  </div>

  <div class="tga-result {res_class}">
    <div class="dt">Government daily result — {latest_date.strftime('%d.%m.%Y')}</div>
    <div class="val">{res_arrow} {fmt_bn(res_bn)}</div>
    <div class="exp">TGA cash has {res_verb} by {fmt_bn(abs(res_bn))}.</div>
  </div>
</div>
"""
st.markdown(identity_html, unsafe_allow_html=True)

st.markdown("---")

# ----------------------- Baseline vs Latest charts -----------------------

st.subheader("Baseline vs Latest (per selection)")

def two_bar_chart(title: str, base_val_bn: float, latest_val_bn: float, color: str):
    dfc = pd.DataFrame({
        "Period": ["Baseline", "Latest"],
        "Billions of $": [base_val_bn, latest_val_bn]
    })
    ch = alt.Chart(dfc).mark_bar().encode(
        x=alt.X("Period:N", title=""),
        y=alt.Y("Billions of $:Q", title="Billions of $"),
        color=alt.value(color),
        tooltip=["Period", alt.Tooltip("Billions of $:Q", format=",.1f")]
    ).properties(height=220, title=title)
    st.altair_chart(ch, use_container_width=True)

colA, colB, colC = st.columns(3)

if base is None:
    st.info("Baseline date not available in the API window. Charts hidden.")
else:
    with colA:
        two_bar_chart("Taxes", bn(base["taxes"]), bn(latest["taxes"]), "#2563eb")
    with colB:
        two_bar_chart("Expenditures", bn(base["expenditures"]), bn(latest["expenditures"]), "#ef4444")
    with colC:
        base_net = bn(base["newdebt"] - base["redemp"])
        last_net = bn(latest["newdebt"] - latest["redemp"])
        two_bar_chart("Net debt cash (New − Redemp)", base_net, last_net, "#6b7280")

st.markdown("---")

# ----------------------- Daily Top-10 detail tables ----------------------

st.subheader("Daily Top-10 categories (latest day)")

# Taxes detail (Deposits excluding Issues & Total)
taxes_total_m = latest["taxes"]
expend_total_m = latest["expenditures"]

left, right = st.columns(2)

with left:
    st.markdown("**Taxes — top 10 categories (share of Taxes)**")
    taxes_top = top_n_detail(df_latest, typ="Deposits", n=10, base_total_m=taxes_total_m)
    taxes_top["Amount (m$)"] = taxes_top["Amount (m$)"].map(lambda v: f"{v:,.0f}")
    taxes_top["Percentage"] = taxes_top["Percentage"].map(lambda v: f"{v:,.1f}%")
    st.dataframe(taxes_top, use_container_width=True)

with right:
    st.markdown("**Expenditures — top 10 categories (share of Expenditures)**")
    expend_top = top_n_detail(df_latest, typ="Withdrawals", n=10, base_total_m=expend_total_m)
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
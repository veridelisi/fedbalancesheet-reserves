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
    try:
        return float(million_value) / 1000.0
    except Exception:
        return 0.0

def fmt_bn(x):
    try:
        return f"{float(x):,.1f}"
    except Exception:
        return "0.0"

@st.cache_data(ttl=1800)
def fetch_latest_window(page_size: int = 500) -> pd.DataFrame:
    """Fetch recent window (desc)."""
    url = f"{BASE}{ENDP}?sort=-record_date&page[size]={page_size}"
    r = requests.get(url, timeout=40)
    r.raise_for_status()
    df = pd.DataFrame(r.json().get("data", []))
    for c in ("record_date","transaction_type","transaction_catg","transaction_today_amt"):
        if c not in df.columns:
            df[c] = None
    df["record_date"] = pd.to_datetime(df["record_date"], errors="coerce").dt.date
    df = df.dropna(subset=["record_date"])
    df["transaction_today_amt"] = df["transaction_today_amt"].apply(to_float)
    return df

def day_slice(df: pd.DataFrame, d: date) -> pd.DataFrame:
    return df[df["record_date"] == d].copy()

def compute_components_for_day(df_day: pd.DataFrame) -> dict:
    dep = df_day[df_day["transaction_type"] == "Deposits"].copy()
    wdr = df_day[df_day["transaction_type"] == "Withdrawals"].copy()

    # Deposits side
    dep_total_row = dep[dep["transaction_catg"].str.contains("Total TGA Deposits", na=False)]
    dep_total = dep_total_row["transaction_today_amt"].sum() if not dep_total_row.empty else (dep["transaction_today_amt"].iloc[-1] if len(dep) else 0.0)

    new_debt_row = dep[dep["transaction_catg"].str.contains("Public Debt Cash Issues", na=False)]
    new_debt = new_debt_row["transaction_today_amt"].sum() if not new_debt_row.empty else (dep["transaction_today_amt"].iloc[-2] if len(dep) >= 2 else 0.0)

    taxes = dep_total - new_debt

    # Withdrawals side
    wdr_total_row = wdr[wdr["transaction_catg"].str.contains("Total TGA Withdrawals", na=False)]
    wdr_total = wdr_total_row["transaction_today_amt"].sum() if not wdr_total_row.empty else (wdr["transaction_today_amt"].iloc[-1] if len(wdr) else 0.0)

    redemp_row = wdr[wdr["transaction_catg"].str.contains("Public Debt Cash Redemptions", na=False)]
    redemp = redemp_row["transaction_today_amt"].sum() if not redemp_row.empty else (wdr["transaction_today_amt"].iloc[-2] if len(wdr) >= 2 else 0.0)

    expenditures = wdr_total - redemp

    return dict(
        taxes=taxes,
        expenditures=expenditures,
        newdebt=new_debt,
        redemp=redemp,
        deposits_total=dep_total,
        withdrawals_total=wdr_total
    )

def top_n_detail(df_day: pd.DataFrame, typ: str, n: int, base_total_m: float) -> pd.DataFrame:
    """
    Return top-N rows for Deposits/Withdrawals excluding:
      - null/blank categories
      - 'Total TGA Deposits/Withdrawals'
      - IIIB debt lines (Issues/Redemptions)
    Adds percentage vs base_total_m.
    """
    sub = df_day[df_day["transaction_type"] == typ].copy()

    # kategori sütunu
    cat = sub["transaction_catg"]

    # 1) null/boş kategorileri at
    keep = cat.notna() & (cat.str.strip() != "")

    # 2) toplam ve IIIB kalemlerini dışla
    if typ == "Deposits":
        keep &= ~cat.str.contains(r"(?:Total TGA Deposits|Public Debt Cash Issues)", na=False)
    else:  # Withdrawals
        keep &= ~cat.str.contains(r"(?:Total TGA Withdrawals|Public Debt Cash Redemptions)", na=False)

    sub = sub[keep]

    # 3) tabloyu hazırla
    sub = (sub[["transaction_catg", "transaction_today_amt"]]
           .sort_values("transaction_today_amt", ascending=False)
           .head(n)
           .rename(columns={"transaction_catg": "Category", "transaction_today_amt": "Amount (m$)"}))

    sub["Percentage"] = (sub["Amount (m$)"] / base_total_m * 100.0) if base_total_m else 0.0

    return sub.reset_index(drop=True)


# --------------------- Fetch & compute latest day ----------------------

df_all = fetch_latest_window()
if df_all.empty:
    st.error("No data returned from Treasury API.")
    st.stop()

latest_date = df_all["record_date"].max()
df_latest = day_slice(df_all, latest_date)
latest = compute_components_for_day(df_latest)

# KPI’leri (billions)
tax_bn   = bn(latest["taxes"])
nd_bn    = bn(latest["newdebt"])
exp_bn   = bn(latest["expenditures"])
rd_bn    = bn(latest["redemp"])
res_bn   = tax_bn + nd_bn - exp_bn - rd_bn

# ----------------------- Latest-day big card ---------------------------

with st.container(border=True):
    st.subheader("Latest day — components (billions of $)")

    # Tarih etiketi
    st.markdown(
        f"""
        <div style="display:inline-block;padding:6px 10px;border:1px solid #e5e7eb;
                    border-radius:10px;background:#fafafa;margin-bottom:10px;">
            <span style="color:#6b7280">Latest business day</span>
            <span style="font-weight:600;margin-left:8px;">{latest_date.strftime('%d.%m.%Y')}</span>
        </div>
        """,
        unsafe_allow_html=True
    )

    # 4 kalem: Taxes & New Debt = mavi, Expenditures & Redemp = kırmızı
    st.markdown(
        f"""
        <style>
          .kpi-grid {{
            display:grid; grid-template-columns:repeat(4,1fr); gap:24px; width:100%;
            margin-top:4px; margin-bottom:8px;
          }}
          .kpi-card .lbl {{ color:#6b7280; font-weight:600; margin:0 0 6px 0; }}
          .pill {{
            display:inline-block; width:100%;
            padding:16px 18px; border-radius:14px; background:#f6f7f9;
            font-weight:800; font-size:1.8rem; line-height:1; text-align:left;
          }}
          .blue {{ color:#2563eb; }}
          .red  {{ color:#ef4444; }}
          .result-line {{
            margin-top:14px; padding-top:12px; border-top:1px dashed #e5e7eb;
            text-align:center; color:#374151; font-size:1.08rem;
          }}
          .result-val.pos {{ color:#10b981; font-weight:900; }}
          .result-val.neg {{ color:#ef4444; font-weight:900; }}
        </style>

        <div class="kpi-grid">
          <div class="kpi-card">
            <div class="lbl">Taxes</div>
            <div class="pill blue">{fmt_bn(tax_bn)}</div>
          </div>
          <div class="kpi-card">
            <div class="lbl">New Debt (IIIB)</div>
            <div class="pill blue">{fmt_bn(nd_bn)}</div>
          </div>
          <div class="kpi-card">
            <div class="lbl">Expenditures</div>
            <div class="pill red">{fmt_bn(exp_bn)}</div>
          </div>
          <div class="kpi-card">
            <div class="lbl">Debt Redemp (IIIB)</div>
            <div class="pill red">{fmt_bn(rd_bn)}</div>
          </div>
        </div>
        """,
        unsafe_allow_html=True
    )

    # Ortalanmış günlük sonuç cümlesi
    arrow = "▲" if res_bn >= 0 else "▼"
    cls   = "pos" if res_bn >= 0 else "neg"
    verb  = "increased" if res_bn >= 0 else "decreased"

    st.markdown(
        f"""
        <div class="result-line">
            <span>Government daily result — {latest_date.strftime('%d.%m.%Y')}</span>
            <span class="result-val {cls}" style="margin-left:10px;">{arrow} {fmt_bn(res_bn)}</span>
            <span style="margin-left:8px;">TGA cash has {verb} by {fmt_bn(abs(res_bn))}.</span>
        </div>
        """,
        unsafe_allow_html=True
    )

# ----------------------- Daily Top-10 detail tables ----------------------

st.subheader("Daily Top-10 categories (latest day)")

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
- We show **latest business day only**.
- **Taxes** = **Total TGA Deposits (Table II)** − **Public Debt Cash Issues (Table IIIB)**.
- **Expenditures** = **Total TGA Withdrawals (Table II)** − **Public Debt Cash Redemptions (Table IIIB)**.
- **Daily Result** = **Taxes + NewDebt − Expenditures − Redemp** (billions).
- Top-10 tables **exclude** the **Total** lines and **IIIB** debt lines.
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
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
# --- Gezinme Barı (Yatay Menü, saf Streamlit) ---
cols = st.columns(8)

with cols[0]:
    st.page_link("streamlit_app.py", label="🏠 Home")
with cols[1]:
    st.page_link("pages/01_Reserves.py", label="🌍 Reserves")
with cols[2]:
    st.page_link("pages/01_Repo.py", label="♻️ Repo")
with cols[3]:
    st.page_link("pages/01_TGA.py", label="🌐 TGA")
with cols[4]:
    st.page_link("pages/01_PublicBalance.py", label="💹 Public Balance")
with cols[5]:
    st.page_link("pages/01_Interest.py", label="✈️ Reference Rates")
with cols[6]:
    st.page_link("pages/01_Desk.py", label="📡 Desk")
with cols[7]:
    st.page_link("pages/01_Eurodollar.py", label="💡 Eurodollar")



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

    # normalize  (FETCH_LATEST_WINDOW)
    for c in ("record_date", "transaction_type", "transaction_catg",
            "transaction_today_amt", "transaction_fytd_amt"):
        if c not in df.columns:
            df[c] = None

    df["record_date"] = pd.to_datetime(df["record_date"], errors="coerce").dt.date
    df = df.dropna(subset=["record_date"])
    df["transaction_today_amt"] = df["transaction_today_amt"].apply(to_float)
    df["transaction_fytd_amt"]  = df["transaction_fytd_amt"].apply(to_float)

    return df

@st.cache_data(ttl=1800)
def fetch_ytd_data(start_date: str, end_date: str) -> pd.DataFrame:
    """Fetch YTD data from start_date to end_date."""
    # Bu endpoint paginated olabilir, büyük date range için birden fazla call gerekebilir
    all_data = []
    page_size = 10000
    
    url = f"{BASE}{ENDP}"
    params = {
        "filter": f"record_date:gte:{start_date},record_date:lte:{end_date}",
        "sort": "record_date",
        "page[size]": page_size
    }
    
    try:
        r = requests.get(url, params=params, timeout=60)
        r.raise_for_status()
        data = r.json().get("data", [])
        all_data.extend(data)
    except Exception:
        return pd.DataFrame()
    
    if not all_data:
        return pd.DataFrame()
    
    df = pd.DataFrame(all_data)
    
    # normalize  (FETCH_YTD_DATA)
    for c in ("record_date", "transaction_type", "transaction_catg",
            "transaction_today_amt", "transaction_fytd_amt"):
        if c not in df.columns:
            df[c] = None

    df["record_date"] = pd.to_datetime(df["record_date"], errors="coerce").dt.date
    df = df.dropna(subset=["record_date"])
    df["transaction_today_amt"] = df["transaction_today_amt"].apply(to_float)
    df["transaction_fytd_amt"]  = df["transaction_fytd_amt"].apply(to_float)

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

# -- Simple Top-10 (your "drop last two rows" logic; also remove null/total/debt names) --
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

# YTD agregasyon fonksiyonları
def top10_ytd_deposits(df_ytd: pd.DataFrame, ytd_taxes_m: float, n: int = 10) -> pd.DataFrame:
    """YTD deposits aggregated by category - ONLY tax categories."""
    d = df_ytd[df_ytd["transaction_type"] == "Deposits"].copy()
    
    # Temiz kategori filtreleme
    d["transaction_catg"] = d["transaction_catg"].astype(str)
    d = d.dropna(subset=["transaction_catg"])
    d = d[d["transaction_catg"].str.strip() != ""]
    d = d[d["transaction_catg"] != "nan"]
    d = d[d["transaction_catg"] != "None"]
    
    # Debt ve total kategorilerini çıkar
    d = d[~d["transaction_catg"].str.contains("Total|Public Debt|Debt", na=False, case=False)]
    # null temizliği
    d = d[~d["transaction_catg"].str.lower().eq("null")]

    
    # Kategori bazında toplam
    agg = d.groupby("transaction_catg")["transaction_today_amt"].sum().reset_index()
    agg = agg[agg["transaction_today_amt"] > 0]  # Pozitif değerler
    agg = agg.sort_values("transaction_today_amt", ascending=False).head(n)
    agg = agg.rename(columns={"transaction_catg": "Category", "transaction_today_amt": "YTD Amount (m$)"})
    agg["Percentage in YTD Taxes"] = (agg["YTD Amount (m$)"] / ytd_taxes_m * 100.0) if ytd_taxes_m else 0.0
    return agg.reset_index(drop=True)

def top10_ytd_withdrawals(df_ytd: pd.DataFrame, ytd_expend_m: float, n: int = 10) -> pd.DataFrame:
    """YTD withdrawals aggregated by category - ONLY expenditure categories."""
    w = df_ytd[df_ytd["transaction_type"] == "Withdrawals"].copy()
    
    # Temiz kategori filtreleme
    w["transaction_catg"] = w["transaction_catg"].astype(str)
    w = w.dropna(subset=["transaction_catg"])
    w = w[w["transaction_catg"].str.strip() != ""]
    w = w[w["transaction_catg"] != "nan"]
    w = w[w["transaction_catg"] != "None"]
    
    # Debt ve total kategorilerini çıkar
    w = w[~w["transaction_catg"].str.contains("Total|Public Debt|Debt|Redemption", na=False, case=False)]
    # null temizliği
    w = w[~w["transaction_catg"].str.lower().eq("null")]

    # Kategori bazında toplam
    agg = w.groupby("transaction_catg")["transaction_today_amt"].sum().reset_index()
    agg = agg[agg["transaction_today_amt"] > 0]  # Pozitif değerler
    agg = agg.sort_values("transaction_today_amt", ascending=False).head(n)
    agg = agg.rename(columns={"transaction_catg": "Category", "transaction_today_amt": "YTD Amount (m$)"})
    agg["Percentage in YTD Expenditures"] = (agg["YTD Amount (m$)"] / ytd_expend_m * 100.0) if ytd_expend_m else 0.0
    return agg.reset_index(drop=True)

def compute_ytd_totals(df_ytd: pd.DataFrame) -> dict:
    """Compute YTD totals for all components."""
    # Her gün için compute edip topla
    dates = sorted(df_ytd["record_date"].unique())
    
    total_taxes = 0.0
    total_expenditures = 0.0
    total_newdebt = 0.0
    total_redemp = 0.0
    
    for d in dates:
        day_data = day_slice(df_ytd, d)
        if day_data.empty:
            continue
        components = compute_components_for_day(day_data)
        total_taxes += components.get("taxes", 0.0)
        total_expenditures += components.get("expenditures", 0.0)
        total_newdebt += components.get("newdebt", 0.0)
        total_redemp += components.get("redemp", 0.0)
    
    return {
        "ytd_taxes": total_taxes,
        "ytd_expenditures": total_expenditures,
        "ytd_newdebt": total_newdebt,
        "ytd_redemp": total_redemp
    }

def debt_bar_chart(new_debt_bn: float, redemp_bn: float, title: str = ""):
    """Modern bar chart for New Debt vs Redemptions."""
    df_debt = pd.DataFrame({
        "Type": ["New Debt", "Redemptions"],
        "Amount": [new_debt_bn, redemp_bn]
    })
    
    base = alt.Chart(df_debt).encode(
        x=alt.X("Type:N", title=None, sort=None,
                axis=alt.Axis(labelFontSize=14, labelPadding=15, labelFontWeight="bold")),
        y=alt.Y("Amount:Q",
                axis=alt.Axis(title="Billions of $", format=",.1f",
                             titleFontSize=14, labelFontSize=12,
                             grid=True, gridOpacity=0.3,
                             titleFontWeight="bold")),
        tooltip=[
            alt.Tooltip("Type:N", title="Type"),
            alt.Tooltip("Amount:Q", format=",.1f", title="Amount (bn $)")
        ]
    )
    
    # Bar colors: New Debt = blue, Redemptions = red
    bars = base.mark_bar(
        cornerRadius=12,
        opacity=0.9,
        stroke='white',
        strokeWidth=3,
        width={"band": 0.7}
    ).encode(
        color=alt.Color("Type:N", legend=None,
                       scale=alt.Scale(range=["#3b82f6", "#ef4444"]))
    )
    
    # Value labels on bars
    labels = base.mark_text(
        dy=-15,
        align="center",
        fontWeight="bold",
        fontSize=16,
        color="white"
    ).encode(
        text=alt.Text("Amount:Q", format=",.1f")
    )
    
    # Shadow effect
    shadow = base.mark_bar(
        cornerRadius=12,
        opacity=0.15,
        color='gray',
        width={"band": 0.7},
        dx=2, dy=2
    )
    
    return (shadow + bars + labels).properties(
        title=alt.TitleParams(
            text=title or "",
            fontSize=16,
            fontWeight="bold",
            anchor="start",
            color="#1e293b"
        ),
        height=320,
        padding={"top":40,"right":20,"left":20,"bottom":20}
    ).resolve_scale(color='independent')

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

# ----------------------- YTD Analysis (2025-01-01 to latest) ----------------------

st.markdown("---")
st.subheader(f"Year-to-Date Analysis (2025-01-01 to {latest_date.strftime('%Y-%m-%d')})")

# YTD data fetch
ytd_start = "2025-01-01"
ytd_end = latest_date.strftime("%Y-%m-%d")

with st.spinner("Fetching YTD data..."):
    df_ytd = fetch_ytd_data(ytd_start, ytd_end)

if df_ytd.empty:
    st.warning("No YTD data available.")
else:
    # Compute YTD totals
    ytd_totals = compute_ytd_totals(df_ytd)
    
    ytd_taxes_bn = bn(ytd_totals["ytd_taxes"])
    ytd_expend_bn = bn(ytd_totals["ytd_expenditures"])
    ytd_newdebt_bn = bn(ytd_totals["ytd_newdebt"])
    ytd_redemp_bn = bn(ytd_totals["ytd_redemp"])
    
    # YTD Top-10 Tables
    st.markdown("**YTD Top-10 Categories**")
    
    left_ytd, right_ytd = st.columns(2)
    
    with left_ytd:
        st.markdown("**YTD Taxes — top 10 categories (cumulative)**")
        ytd_taxes_top = top10_ytd_deposits(df_ytd, ytd_totals["ytd_taxes"], n=10)
        if not ytd_taxes_top.empty:
            ytd_taxes_top["YTD Amount (m$)"] = ytd_taxes_top["YTD Amount (m$)"].map(lambda v: f"{v:,.0f}")
            ytd_taxes_top["Percentage in YTD Taxes"] = ytd_taxes_top["Percentage in YTD Taxes"].round(1).map(lambda v: f"{v:.1f}%")
        st.dataframe(ytd_taxes_top, use_container_width=True)
    
    with right_ytd:
        st.markdown("**YTD Expenditures — top 10 categories (cumulative)**")
        ytd_expend_top = top10_ytd_withdrawals(df_ytd, ytd_totals["ytd_expenditures"], n=10)
        if not ytd_expend_top.empty:
            ytd_expend_top["YTD Amount (m$)"] = ytd_expend_top["YTD Amount (m$)"].map(lambda v: f"{v:,.0f}")
            ytd_expend_top["Percentage in YTD Expenditures"] = ytd_expend_top["Percentage in YTD Expenditures"].round(1).map(lambda v: f"{v:.1f}%")
        st.dataframe(ytd_expend_top, use_container_width=True)
    
    # YTD Debt Ops Bar Chart



 def compute_components_for_fytd(df_day: pd.DataFrame) -> dict:
    """Return FYTD totals (Taxes, Expenditures, NewDebt, Redemp) using transaction_fytd_amt."""
    dep = df_day[df_day["transaction_type"] == "Deposits"].copy()
    wdr = df_day[df_day["transaction_type"] == "Withdrawals"].copy()

    # --- Deposits ---
    dep_total_row = dep[dep["transaction_catg"].str.contains("Total TGA Deposits", na=False)]
    dep_total = dep_total_row["transaction_fytd_amt"].sum() if not dep_total_row.empty \
                else (dep["transaction_fytd_amt"].iloc[-1] if len(dep) else 0.0)

    new_debt_row = dep[dep["transaction_catg"].str.contains("Public Debt Cash Issues", na=False)]
    new_debt = new_debt_row["transaction_fytd_amt"].sum() if not new_debt_row.empty \
               else (dep["transaction_fytd_amt"].iloc[-2] if len(dep) >= 2 else 0.0)

    taxes = dep_total - new_debt

    # --- Withdrawals ---
    wdr_total_row = wdr[wdr["transaction_catg"].str.contains("Total TGA Withdrawals", na=False)]
    wdr_total = wdr_total_row["transaction_fytd_amt"].sum() if not wdr_total_row.empty \
                else (wdr["transaction_fytd_amt"].iloc[-1] if len(wdr) else 0.0)

    redemp_row = wdr[wdr["transaction_catg"].str.contains("Public Debt Cash Redemptions", na=False)]
    redemp = redemp_row["transaction_fytd_amt"].sum() if not redemp_row.empty \
             else (wdr["transaction_fytd_amt"].iloc[-2] if len(wdr) >= 2 else 0.0)

    expenditures = wdr_total - redemp

    return dict(
        taxes=taxes,
        expenditures=expenditures,
        newdebt=new_debt,
        redemp=redemp,
        deposits_total=dep_total,
        withdrawals_total=wdr_total,
    )



# ---------------------------- Methodology -------------------------------
st.markdown("### 📋 Methodology")
with st.expander("🔎 Click to expand methodology details", expanded=False):
    st.markdown(
        """
**What this page shows**  
- 🧾 Decomposition of the Federal public cash position into **Taxes**, **Expenditures**, and **Debt operations**.  
- 🧮 Two lenses: **daily result** and **year-to-date (YTD)** aggregates starting **2025-01-01**.

---

### 🧮 Calculation logic (daily)
- 💵 **Taxes** = **Total TGA Deposits (DTS Table II)** − **Public Debt Cash Issues (DTS Table IIIB)**  
- 🧾 **Expenditures** = **Total TGA Withdrawals (DTS Table II)** − **Public Debt Cash Redemptions (DTS Table IIIB)**  
- 🔗 **Debt operations** are shown separately as:
  - **New Debt (Issues)** = Public Debt Cash Issues (IIIB)  
  - **Redemptions** = Public Debt Cash Redemptions (IIIB)  
- 📊 **Daily Result (Δ cash)** = **Taxes + New Debt − Expenditures − Redemptions**  
- 🔁 **Business days only**; weekends/holidays excluded (no forward-fill on flows).

---

### 📅 YTD analysis
- 🧷 Period: **from 2025-01-01 to latest available date**.  
- ➕ Categories are summed across all business days.  
- 🧮 **Debt ops chart** compares **total Issues** vs **total Redemptions**.  
- 🧾 **YTD Net result** = cumulative **Daily Result** (gov’t cash position change).

---

### 🗂️ Data source
- 🇺🇸 **U.S. Treasury – Fiscal Data (Daily Treasury Statement)**  
  • Primary dataset: `deposits_withdrawals_operating_cash` (DTS Table II baseline)  
  • Debt ops mapping: **Public Debt Cash Issues/Redemptions** (DTS Table IIIB)  
  • ⏱️ **Update**: Daily on business days (publication lag and revisions may occur).

---

### ⚙️ Data processing
- 🔢 Units: API returns **millions of USD** → displayed as **USD billions** (÷1,000).  
- 🧹 Ranking tables (Top-10):  
  - Exclude **total/summary** rows and debt-related categories (handled separately).  
  - Filter out **null/empty** labels.  
  - Keep **positive** transaction amounts only for the Top-10 leaderboards.  

---

### 🚫 Categories excluded from Top-10 tables
- **Total TGA Deposits/Withdrawals** (summary rows)  
- **Public Debt Cash Issues/Redemptions** (shown in Debt ops section)  
- **Null/empty** category names  
- **Zero or negative** amounts for ranking views

---

### ⚠️ Caveats
- ⏳ **Timing effects** (settlement dates, tax peaks, coupon/redemption days) can cause large day-to-day swings.  
- 🔁 **Revisions**: DTS entries may be restated after initial publication.  
- 🕒 Values are **end-of-day**; intraday cash movements are not captured.

---

### 🗺️ Glossary
- **Taxes (proxy)**: Non-debt deposit inflows into TGA (after removing debt-issue proceeds).  
- **Expenditures (proxy)**: Non-debt outflows (after removing redemptions).  
- **Daily Result**: Net change in the government’s cash position for that day.
        """
    )

# --------------------------- Footer -------------------------------

st.markdown(
    """
    <div style="text-align:center;color:#64748b;font-size:0.95rem;padding:20px 0;">
        <a href="https://veridelisi.substack.com/">Veri Delisi</a>🚀 <br>
        <em>Engin Yılmaz • Amherst • September 2025 </em>
    </div>
    """,
    unsafe_allow_html=True
)
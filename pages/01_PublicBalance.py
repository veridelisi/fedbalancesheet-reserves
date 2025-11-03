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
import re

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
st.caption("Latest snapshot • Fiscal YTD (1 Oct) • Daily Top-10 breakdowns")

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

# --- FYTD row picker (esnek; CSV'deki isim değişse de regex ile yakalar) ---
def pick_amount(df_day: pd.DataFrame, tx_type: str, account_pat: str | None, catg_pat: str | None,
                which: str = "transaction_fytd_amt") -> float:
    """
    Tek gün datasından istenen satırın miktarını döndürür.
    - tx_type: 'Deposits' / 'Withdrawals'
    - account_pat: 'Treasury General Account' / 'Total Deposits' / 'Total Withdrawals' vb. (regex)
                   None ise filtre uygulanmaz.
    - catg_pat: 'Public Debt Cash Issues' / 'Public Debt Cash Redemp' vb. (regex)
                '__NULL__' => transaction_catg boş olanlar.
                None ise filtre uygulanmaz.
    - which: 'transaction_today_amt' / 'transaction_mtd_amt' / 'transaction_fytd_amt'
    """
    d = df_day[df_day["transaction_type"].str.lower().eq(tx_type.lower())].copy()

    if account_pat:
        if "account_type" in d.columns:
            d = d[d["account_type"].astype(str).str.contains(account_pat, case=False, na=False, regex=True)]
        else:
            # bazı eski dökümlerde "account_type" yoksa, tüm satırlarda aramayalım
            pass

    if catg_pat is not None:
        if catg_pat == "__NULL__":
            mask_null = d["transaction_catg"].isna() | d["transaction_catg"].astype(str).str.lower().isin(["", "null", "none", "nan"])
            d = d[mask_null]
        else:
            d = d[d["transaction_catg"].astype(str).str.contains(catg_pat, case=False, na=False, regex=True)]

    if d.empty:
        # fallback: doğrudan bilinen metinleri tarayalım
        if tx_type.lower() == "deposits" and catg_pat == "__NULL__":
            d = df_day[(df_day["transaction_type"]=="Deposits") &
                       (df_day["transaction_catg"].astype(str).str.contains("Total TGA Deposits|Total Deposits",
                                                                           case=False, na=False, regex=True))]
        elif tx_type.lower() == "withdrawals" and catg_pat == "__NULL__":
            d = df_day[(df_day["transaction_type"]=="Withdrawals") &
                       (df_day["transaction_catg"].astype(str).str.contains("Total TGA Withdrawals|Total Withdrawals",
                                                                           case=False, na=False, regex=True))]
        elif tx_type.lower() == "deposits" and catg_pat:
            d = df_day[(df_day["transaction_type"]=="Deposits") &
                       (df_day["transaction_catg"].astype(str).str.contains("Public Debt Cash Issues", case=False, na=False))]
        elif tx_type.lower() == "withdrawals" and catg_pat:
            d = df_day[(df_day["transaction_type"]=="Withdrawals") &
                       (df_day["transaction_catg"].astype(str).str.contains("Public Debt Cash Redemp", case=False, na=False))]

    if d.empty:
        return 0.0

    val = pd.to_numeric(d.get(which, 0.0), errors="coerce").fillna(0.0)
    # aynı başlık birden fazla alt satırda gelebilir; FYTD için en büyük/son değer genelde total'dir
    return float(val.max())

@st.cache_data(ttl=1800)
def fetch_latest_window(page_size: int = 500) -> pd.DataFrame:
    """Fetch recent DTS window sorted by date desc."""
    url = f"{BASE}{ENDP}?sort=-record_date&page[size]={page_size}"
    r = requests.get(url, timeout=40)
    r.raise_for_status()
    df = pd.DataFrame(r.json().get("data", []))

    # normalize  (FETCH_LATEST_WINDOW)
    for c in ("record_date", "transaction_type", "transaction_catg",
              "transaction_today_amt", "transaction_mtd_amt", "transaction_fytd_amt",
              "account_type"):
        if c not in df.columns:
            df[c] = None

    df["record_date"] = pd.to_datetime(df["record_date"], errors="coerce").dt.date
    df = df.dropna(subset=["record_date"])
    for c in ("transaction_today_amt","transaction_mtd_amt","transaction_fytd_amt"):
        df[c] = pd.to_numeric(df[c], errors="coerce").fillna(0.0)
    return df

@st.cache_data(ttl=1800)
def fetch_ytd_data(start_date: str, end_date: str) -> pd.DataFrame:
    """Fetch YTD data from start_date to end_date. (Gerekirse kullanılır; mevcut akış FYTD'yi tek günden alıyor.)"""
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
              "transaction_today_amt", "transaction_fytd_amt", "account_type"):
        if c not in df.columns:
            df[c] = None

    df["record_date"] = pd.to_datetime(df["record_date"], errors="coerce").dt.date
    df = df.dropna(subset=["record_date"])
    df["transaction_today_amt"] = pd.to_numeric(df["transaction_today_amt"], errors="coerce").fillna(0.0)
    df["transaction_fytd_amt"]  = pd.to_numeric(df["transaction_fytd_amt"],  errors="coerce").fillna(0.0)

    return df

def day_slice(df: pd.DataFrame, d: date) -> pd.DataFrame:
    return df[df["record_date"] == d].copy()

def compute_components_for_day(df_day: pd.DataFrame) -> dict:
    """Return taxes, expenditures, newdebt, redemp (+ totals) for a single day."""
    dep = df_day[df_day["transaction_type"] == "Deposits"].copy()
    wdr = df_day[df_day["transaction_type"] == "Withdrawals"].copy()

    # --- Deposits ---
    # Total deposits (Table II)
    dep_total_row = dep[dep["transaction_catg"].astype(str).str.contains("Total TGA Deposits|Total Deposits", na=False, case=False)]
    dep_total = dep_total_row["transaction_today_amt"].sum() if not dep_total_row.empty \
                else (dep["transaction_today_amt"].iloc[-1] if len(dep) else 0.0)

    # Public Debt Cash Issues (Table IIIB)
    new_debt_row = dep[dep["transaction_catg"].astype(str).str.contains("Public Debt Cash Issues", na=False, case=False)]
    new_debt = new_debt_row["transaction_today_amt"].sum() if not new_debt_row.empty \
               else (dep["transaction_today_amt"].iloc[-2] if len(dep) >= 2 else 0.0)

    taxes = dep_total - new_debt

    # --- Withdrawals ---
    # Total withdrawals (Table II)
    wdr_total_row = wdr[wdr["transaction_catg"].astype(str).str.contains("Total TGA Withdrawals|Total Withdrawals", na=False, case=False)]
    wdr_total = wdr_total_row["transaction_today_amt"].sum() if not wdr_total_row.empty \
                else (wdr["transaction_today_amt"].iloc[-1] if len(wdr) else 0.0)

    # Public Debt Cash Redemptions (Table IIIB)
    redemp_row = wdr[wdr["transaction_catg"].astype(str).str.contains("Public Debt Cash Redemp", na=False, case=False)]
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
    w = w[~w["transaction_catg"].str.contains("Total|Public Debt Cash Redemptions|Public Debt Cash Redemp", na=False)]
    w = w[["transaction_catg", "transaction_today_amt"]]
    out = (w.sort_values("transaction_today_amt", ascending=False)
             .head(n)
             .rename(columns={"transaction_catg": "Category", "transaction_today_amt": "Amount (m$)"}))
    out["Percentage in Expenditures"] = (out["Amount (m$)"] / expend_m * 100.0) if expend_m else 0.0
    return out.reset_index(drop=True)

# FYTD Top-10 (tek gün datasındaki FYTD sütununu kullanır)
def top10_fytd_deposits_day(df_day: pd.DataFrame, ytd_taxes_m: float, n: int = 10) -> pd.DataFrame:
    d = df_day[df_day["transaction_type"] == "Deposits"].copy()
    d["transaction_catg"] = d["transaction_catg"].astype(str)
    d = d.dropna(subset=["transaction_catg"])
    d = d[~d["transaction_catg"].str.contains("Total|Public Debt|Debt", case=False, na=False)]
    d = d[~d["transaction_catg"].str.lower().isin(["", "null", "none", "nan"])]

    agg = (d.groupby("transaction_catg", as_index=False)["transaction_fytd_amt"].sum()
             .rename(columns={"transaction_catg":"Category","transaction_fytd_amt":"YTD Amount (m$)"}))
    agg = agg[agg["YTD Amount (m$)"] > 0].sort_values("YTD Amount (m$)", ascending=False).head(n)
    agg["Percentage in YTD Taxes"] = (agg["YTD Amount (m$)"] / ytd_taxes_m * 100.0) if ytd_taxes_m else 0.0
    return agg.reset_index(drop=True)

def top10_fytd_withdrawals_day(df_day: pd.DataFrame, ytd_expend_m: float, n: int = 10) -> pd.DataFrame:
    w = df_day[df_day["transaction_type"] == "Withdrawals"].copy()
    w["transaction_catg"] = w["transaction_catg"].astype(str)
    w = w.dropna(subset=["transaction_catg"])
    w = w[~w["transaction_catg"].str.contains("Total|Public Debt|Debt|Redemp", case=False, na=False)]
    w = w[~w["transaction_catg"].str.lower().isin(["", "null", "none", "nan"])]

    agg = (w.groupby("transaction_catg", as_index=False)["transaction_fytd_amt"].sum()
             .rename(columns={"transaction_catg":"Category","transaction_fytd_amt":"YTD Amount (m$)"}))
    agg = agg[agg["YTD Amount (m$)"] > 0].sort_values("YTD Amount (m$)", ascending=False).head(n)
    agg["Percentage in YTD Expenditures"] = (agg["YTD Amount (m$)"] / ytd_expend_m * 100.0) if ytd_expend_m else 0.0
    return agg.reset_index(drop=True)

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
    
    labels = base.mark_text(
        dy=-15,
        align="center",
        fontWeight="bold",
        fontSize=16,
        color="white"
    ).encode(
        text=alt.Text("Amount:Q", format=",.1f")
    )
    
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

# ----------------------- FYTD Analysis (fiscal year, as of latest day) ----------------------
st.markdown("---")
st.subheader(f"Fiscal Year-to-Date (FYTD) — as of {latest_date.strftime('%Y-%m-%d')}")

# Tek gün datasından FYTD kolonlarını kullanarak 4 kalemi çıkart
# Taxes = Total Deposits - Public Debt Cash Issues (IIIB)
# Expenditures = Total Withdrawals - Public Debt Cash Redemp. (IIIB)

depTot_fytd = pick_amount(df_latest, "Deposits",
                          account_pat=r"Total Deposits", catg_pat="__NULL__",
                          which="transaction_fytd_amt")

issues_fytd = pick_amount(df_latest, "Deposits",
                          account_pat=r"Treasury General Account", catg_pat=r"Public Debt Cash Issues",
                          which="transaction_fytd_amt")

withTot_fytd = pick_amount(df_latest, "Withdrawals",
                           account_pat=r"Total Withdrawals", catg_pat="__NULL__",
                           which="transaction_fytd_amt")

redemp_fytd = pick_amount(df_latest, "Withdrawals",
                          account_pat=r"Treasury General Account", catg_pat=r"Public Debt Cash Redemp",
                          which="transaction_fytd_amt")

# Fallback: eğer total satırları account_type ile bulunamazsa, doğrudan transaction_catg metnine bak
if depTot_fytd == 0.0:
    depTot_fytd = pick_amount(df_latest, "Deposits", account_pat=None, catg_pat="Total TGA Deposits|Total Deposits", which="transaction_fytd_amt")
if withTot_fytd == 0.0:
    withTot_fytd = pick_amount(df_latest, "Withdrawals", account_pat=None, catg_pat="Total TGA Withdrawals|Total Withdrawals", which="transaction_fytd_amt")
if issues_fytd == 0.0:
    issues_fytd = pick_amount(df_latest, "Deposits", account_pat=None, catg_pat="Public Debt Cash Issues", which="transaction_fytd_amt")
if redemp_fytd == 0.0:
    redemp_fytd = pick_amount(df_latest, "Withdrawals", account_pat=None, catg_pat="Public Debt Cash Redemp", which="transaction_fytd_amt")

ytd_taxes_m   = depTot_fytd - issues_fytd
ytd_expend_m  = withTot_fytd - redemp_fytd
ytd_newdebt_m = issues_fytd
ytd_redemp_m  = redemp_fytd
ytd_net_m     = ytd_taxes_m + ytd_newdebt_m - ytd_expend_m - ytd_redemp_m

# Kartlar (bn$)
col1, col2, col3, col4, col5 = st.columns(5)
col1.metric("YTD Taxes",        f"${fmt_bn(bn(ytd_taxes_m))}B")
col2.metric("YTD Expenditures", f"${fmt_bn(bn(ytd_expend_m))}B")
col3.metric("YTD New Debt",     f"${fmt_bn(bn(ytd_newdebt_m))}B")
col4.metric("YTD Redemptions",  f"${fmt_bn(bn(ytd_redemp_m))}B")
col5.metric("YTD Net Result",   f"${fmt_bn(bn(ytd_net_m))}B",
            delta=("TGA Increased" if ytd_net_m >= 0 else "TGA Decreased"))

# FYTD Debt Ops Bar Chart
st.markdown("**YTD Debt Operations**")
debt_chart = debt_bar_chart(
    bn(ytd_newdebt_m),
    bn(ytd_redemp_m),
    title=f"FYTD New Debt vs Redemptions (since Oct 1)"
)
st.altair_chart(debt_chart, use_container_width=True, theme=None)

# FYTD Top-10 tabloları
left_ytd, right_ytd = st.columns(2)
with left_ytd:
    st.markdown("**YTD Taxes — top 10 categories (FYTD shares)**")
    ytd_taxes_top = top10_fytd_deposits_day(df_latest, ytd_taxes_m, n=10)
    if not ytd_taxes_top.empty:
        ytd_taxes_top["YTD Amount (m$)"] = ytd_taxes_top["YTD Amount (m$)"].map(lambda v: f"{v:,.0f}")
        ytd_taxes_top["Percentage in YTD Taxes"] = ytd_taxes_top["Percentage in YTD Taxes"].round(1).map(lambda v: f"{v:.1f}%")
    st.dataframe(ytd_taxes_top, use_container_width=True)

with right_ytd:
    st.markdown("**YTD Expenditures — top 10 categories (FYTD shares)**")
    ytd_expend_top = top10_fytd_withdrawals_day(df_latest, ytd_expend_m, n=10)
    if not ytd_expend_top.empty:
        ytd_expend_top["YTD Amount (m$)"] = ytd_expend_top["YTD Amount (m$)"].map(lambda v: f"{v:,.0f}")
        ytd_expend_top["Percentage in YTD Expenditures"] = ytd_expend_top["Percentage in YTD Expenditures"].round(1).map(lambda v: f"{v:.1f}%")
    st.dataframe(ytd_expend_top, use_container_width=True)

# ---------------------------- Methodology -------------------------------
st.markdown("### 📋 Methodology")
with st.expander("🔎 Click to expand methodology details", expanded=False):
    st.markdown(
        """
**What this page shows**  
- 🧾 Decomposition of the Federal public cash position into **Taxes**, **Expenditures**, and **Debt operations**.  
- 🧮 Two lenses: **daily result** and **fiscal year-to-date (FYTD)** aggregates starting **Oct 1**.

---

### 🧮 Calculation logic (daily)
- 💵 **Taxes** = **Total TGA Deposits (DTS Table II)** − **Public Debt Cash Issues (DTS Table IIIB)**  
- 🧾 **Expenditures** = **Total TGA Withdrawals (DTS Table II)** − **Public Debt Cash Redemptions (DTS Table IIIB)**  
- 🔗 **Debt operations** are shown separately as:
  - **New Debt (Issues)** = Public Debt Cash Issues (IIIB)  
  - **Redemptions** = Public Debt Cash Redemptions (IIIB)  
- 📊 **Daily Result (Δ cash)** = **Taxes + New Debt − Expenditures − Redemptions**  

---

### 📅 FYTD analysis
- 🧷 Period starts **Oct 1** (U.S. federal fiscal year).  
- ➕ FYTD values taken directly from `transaction_fytd_amt` (no manual summing).  
- 🧮 **YTD Net result** = **Taxes + Issues − Expenditures − Redemptions** (all FYTD).

---

### 🗂️ Data source
- 🇺🇸 **U.S. Treasury – Fiscal Data (Daily Treasury Statement)**  
  Dataset: `deposits_withdrawals_operating_cash` (Tables II & IIIB mapping).  

---

### ⚙️ Units
- API returns **millions of USD** → dashboards display **billions** (÷1,000).
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

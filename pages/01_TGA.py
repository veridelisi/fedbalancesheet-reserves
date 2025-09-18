import math
import requests
import pandas as pd
import numpy as np
import streamlit as st
import altair as alt
from datetime import date
from dateutil.relativedelta import relativedelta

st.set_page_config(page_title="TGA — Deposits, Withdrawals & Closing Balance", layout="wide")

# --- Gezinme Barı (Yatay Menü, Streamlit-native) ---
st.markdown("""
<div style="background:#f8f9fa;padding:10px 0 10px 0;margin-bottom:24px;border-radius:8px;display:flex;gap:32px;justify-content:center;">
""", unsafe_allow_html=True)

col1, col2, col3, col4, col5, col6, col7 = st.columns([1,1,1,1,1,1,1])
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
with col6:
    st.page_link("pages/01_Interest.py", label="🔄 Reference Rates")
with col7:
    st.page_link("pages/01_Desk.py", label="🔄 Desk")

st.markdown("</div>", unsafe_allow_html=True)

# --- Sol menü sakla ---
st.markdown("""
    <style>
        [data-testid="stSidebarNav"] {display: none;}
        section[data-testid="stSidebar"][aria-expanded="true"]{display: none;}
    </style>
    """, unsafe_allow_html=True)

# --------------------------- Constants -----------------------------
BASE = "https://api.fiscaldata.treasury.gov/services/api/fiscal_service"
ENDP = "/v1/accounting/dts/operating_cash_balance"

OPEN  = "Treasury General Account (TGA) Opening Balance"
DEPO  = "Total TGA Deposits (Table II)"
WDRW  = "Total TGA Withdrawals (Table II) (-)"

# Görsel renkler - Gradient ve modern renkler
COLOR_DEP  = "#3b82f6"   # Modern blue
COLOR_WDR  = "#ef4444"   # Modern red
COLOR_LINE = "#1e293b"   # Dark slate
COLOR_OK   = "#10b981"   # Emerald green

# Dataset güvenli alanlar + kolon tercihleri
SAFE_FIELDS = ["record_date", "account_type", "open_today_bal", "close_today_bal", "today_amt"]
COLUMN_PREFS = {
    OPEN : ["open_today_bal"],                 # Opening
    DEPO : ["today_amt", "open_today_bal"],    # Deposits
    WDRW : ["today_amt", "open_today_bal"],    # Withdrawals
}
NUM_CANDIDATES = {"open_today_bal", "close_today_bal", "today_amt"}

# --------------------------- Helpers -------------------------------
def _to_float(x):
    try:
        return float(str(x).replace(",", "").replace("$", ""))
    except Exception:
        return math.nan

@st.cache_data(ttl=1800)
def latest_record_date() -> str:
    r = requests.get(f"{BASE}{ENDP}",
                     params={"fields":"record_date","sort":"-record_date","page[size]":1},
                     timeout=40)
    r.raise_for_status()
    js = r.json().get("data", [])
    if not js:
        raise RuntimeError("No latest record_date returned by API.")
    return js[0]["record_date"]

@st.cache_data(ttl=1800)
def get_value_on_or_before(target_date: str, account_type: str) -> float | None:
    """
    Tek bir tarih için (veya öncesindeki) tek bir hesap türünün değerini döndürür (millions).
    """
    params = {
        "fields": ",".join(SAFE_FIELDS),
        "filter": f"record_date:lte:{target_date},account_type:eq:{account_type}",
        "sort": "-record_date",
        "page[size]": 1,
    }
    url = f"{BASE}{ENDP}"
    try:
        r = requests.get(url, params=params, timeout=40)
        r.raise_for_status()
    except requests.HTTPError:
        # Bazı ortamlarda fields reddedilirse fallback
        params.pop("fields", None)
        r = requests.get(url, params=params, timeout=40)
        r.raise_for_status()

    data = r.json().get("data", [])
    if not data:
        return None

    row = data[0]
    for c in NUM_CANDIDATES:
        if c in row and row[c] is not None:
            row[c] = _to_float(row[c])

    for col in COLUMN_PREFS[account_type]:
        if col in row and pd.notna(row[col]):
            return float(row[col])
    return None

@st.cache_data(ttl=1800)
def fetch_series(account_type: str, start_date: str, end_date: str) -> pd.DataFrame:
    """
    Seçilen tarih aralığında (start..end dahil) tek bir hesap türünün günlük serisini döndürür.
    Çıktı: DataFrame[record_date: datetime64[ns], value_M: float]
    """
    params = {
        "fields": ",".join(SAFE_FIELDS),
        "filter": f"record_date:gte:{start_date},record_date:lte:{end_date},account_type:eq:{account_type}",
        "sort": "record_date",
        "page[size]": 10000,
    }
    url = f"{BASE}{ENDP}"
    try:
        r = requests.get(url, params=params, timeout=60)
        r.raise_for_status()
    except requests.HTTPError:
        params.pop("fields", None)
        r = requests.get(url, params=params, timeout=60)
        r.raise_for_status()

    js = r.json().get("data", [])
    if not js:
        return pd.DataFrame(columns=["record_date","value_M"]).astype({"record_date":"datetime64[ns]","value_M":"float64"})

    df = pd.DataFrame(js)
    # numerik kolonları normalize et
    for c in NUM_CANDIDATES:
        if c in df.columns:
            df[c] = df[c].apply(_to_float)
    # değer seç
    val = None
    for col in COLUMN_PREFS[account_type]:
        if col in df.columns:
            val = df[col]
            break
    if val is None:
        df["value_M"] = np.nan
    else:
        df["value_M"] = val
    # tarih düzeni
    df["record_date"] = pd.to_datetime(df["record_date"])
    out = df[["record_date","value_M"]].groupby("record_date", as_index=False).last()
    return out

def bn(x):  # millions -> billions
    return None if x is None or pd.isna(x) else x/1000.0

def fmt_bn(x):
    if x is None or pd.isna(x): return "—"
    return f"{x:,.1f}"

def vbar(df, yfield, ytitle, colors, title=""):
    """Güzelleştirilmiş dikey bar: df -> columns [label, value]."""
    if df.empty:
        df = pd.DataFrame({"label":[], yfield:[]})
    
    base = alt.Chart(df).encode(
        x=alt.X("label:N", title=None, sort=None, 
                axis=alt.Axis(labelFontSize=14, labelPadding=15, labelFontWeight="bold")),
        y=alt.Y(f"{yfield}:Q", 
                axis=alt.Axis(title=ytitle, format=",.1f", 
                             titleFontSize=14, labelFontSize=12,
                             grid=True, gridOpacity=0.3,
                             titleFontWeight="bold")),
        tooltip=[
            alt.Tooltip("label:N", title="Type"), 
            alt.Tooltip(f"{yfield}:Q", format=",.1f", title=ytitle)
        ],
    )
    
    # Gradient renkler ve rounded köşeler
    bars = base.mark_bar(
        cornerRadius=12,     # Yuvarlatılmış köşeler
        opacity=0.9,        # Hafif şeffaflık
        stroke='white',     # Beyaz kenarlık
        strokeWidth=3,
        width={"band": 0.7}  # Bar genişliği
    ).encode(
        color=alt.Color("label:N", legend=None,
                       scale=alt.Scale(range=colors))
    )
    
    # Daha şık text labels
    labels = base.mark_text(
        dy=-15, 
        align="center", 
        fontWeight="bold",
        fontSize=16,
        color="white"
    ).encode(
        text=alt.Text(f"{yfield}:Q", format=",.1f")
    )
    
    # Gölge efekti için arka plan bars
    shadow = base.mark_bar(
        cornerRadius=12,
        opacity=0.15,
        color='gray',
        width={"band": 0.7},
        dx=2, dy=2  # Gölge offset
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

def closing_line_chart(ts: pd.DataFrame, title: str):
    """
    Güzelleştirilmiş line chart - hafta sonu boşluklarını kaldırır
    ts: DataFrame with columns ['date','closing_bn'] ; daily index doldurulmuş olmalı.
    """
    if ts.empty:
        return alt.Chart(pd.DataFrame({"date":[], "closing_bn":[]})).mark_line()

    # Sadece veri olan günleri filtrele (hafta sonu boşluklarını kaldır)
    ts_filtered = ts.dropna(subset=['closing_bn']).copy()
    
    if ts_filtered.empty:
        return alt.Chart(pd.DataFrame({"date":[], "closing_bn":[]})).mark_line()

    base = alt.Chart(ts_filtered).encode(
        x=alt.X("date:T", 
                axis=alt.Axis(title=None, 
                             labelAngle=-45,
                             labelFontSize=11,
                             tickCount=12,
                             gridOpacity=0.3)),
        y=alt.Y("closing_bn:Q", 
                axis=alt.Axis(title="Billions of $", format=",.1f",
                             titleFontSize=14, labelFontSize=12,
                             grid=True, gridOpacity=0.3,
                             titleFontWeight="bold")),
        tooltip=[
            alt.Tooltip("date:T", title="Date", format="%Y-%m-%d"),
            alt.Tooltip("closing_bn:Q", format=",.1f", title="Closing Balance (bn $)")
        ]
    )
    
    # Gradient area altında
    area = base.mark_area(
        opacity=0.15,
        color=COLOR_LINE,
        interpolate='monotone'
    )
    
    # Ana çizgi - daha smooth ve kalın
    line = base.mark_line(
        color=COLOR_LINE, 
        strokeWidth=3,
        interpolate='monotone'
    )
    
    # Basit noktalar
    points = base.mark_circle(
        color=COLOR_LINE,
        size=40,
        opacity=0.7
    )
    
    return (area + line + points).properties(
        title=alt.TitleParams(
            text=title,
            fontSize=16,
            fontWeight="bold",
            anchor="start",
            color="#1e293b"
        ),
        height=400,
        padding={"top":40,"right":25,"left":25,"bottom":25}
    )

# --------------------------- Header -------------------------------
st.title("🏦 TGA Cash Position Statement")
st.caption("Latest snapshot • Baseline (YoY or 2025-01-01) and daily line to the latest date")

# Latest date + baseline seçimi
try:
    _latest = latest_record_date()
except Exception as e:
    st.error(f"Failed to fetch latest record date: {e}")
    st.stop()

t_latest = pd.to_datetime(_latest).date()

c1, c2 = st.columns([1,3])
with c1:
    st.markdown(
        f"""
        <div style="display:inline-block;padding:12px 18px;border:1px solid #e5e7eb;border-radius:12px;background:linear-gradient(135deg, #f8fafc 0%, #f1f5f9 100%);box-shadow:0 2px 4px rgba(0,0,0,0.05);">
          <div style="font-size:0.95rem;color:#64748b;margin-bottom:4px;font-weight:500;">Latest Record Date</div>
          <div style="font-size:1.2rem;font-weight:700;letter-spacing:0.3px;color:#1e293b;">{t_latest.strftime('%d.%m.%Y')}</div>
        </div>
        """,
        unsafe_allow_html=True
    )
with c2:
    baseline_label = st.radio(
        "Baseline",
        ("YoY (t - 1 year)", "01.01.2025"),
        index=0, horizontal=True
    )

if baseline_label.startswith("YoY"):
    t_base = (t_latest - relativedelta(years=1))
    base_tag = "YoY"
else:
    t_base = date(2025,1,1)
    base_tag = "2025-01-01"

# --------------------------- Fetch latest values ------------------
open_latest  = get_value_on_or_before(t_latest.isoformat(), OPEN)
depo_latest  = get_value_on_or_before(t_latest.isoformat(), DEPO)
wdrw_latest  = get_value_on_or_before(t_latest.isoformat(), WDRW)

# Closing = Opening + Deposits − Withdrawals  (billions)
closing_latest_bn = (bn(open_latest) or 0) + (bn(depo_latest) or 0) - (bn(wdrw_latest) or 0)

# --------------------------- Identity line ------------------------
from textwrap import dedent

with st.container(border=True):
    # değerleri hesapla (bn = millions -> billions)
    open_bn  = bn(open_latest)
    depo_bn  = bn(depo_latest)
    wdrw_bn  = bn(wdrw_latest)
    close_bn = closing_latest_bn  # Opening + Deposits − Withdrawals (computed)

    html = dedent(f"""
    <style>
      .id-title {{
        font-size: 1.8rem; font-weight: 800; color: #111827; margin: 2px 0 12px 0;
      }}
      .id-grid {{
        display: grid;
        grid-template-columns: 1fr auto 1fr auto 1fr auto 1fr;
        grid-template-rows: auto auto;
        column-gap: 20px; row-gap: 12px;
        align-items: center; width: 100%;
      }}
      .lbl {{ 
        color:#64748b; font-size:1rem; grid-row: 1; font-weight:600; text-align:center;
      }}
      .val {{
        grid-row: 2;
        display:inline-block; padding:12px 16px; border-radius:12px;
        background:linear-gradient(135deg, #f8fafc 0%, #f1f5f9 100%);
        font-weight:800; font-size:1.35rem;
        box-shadow:0 2px 8px rgba(0,0,0,0.08);
        border:1px solid #e2e8f0;
        text-align:center;
        min-width:80px;
      }}
      .op  {{ 
        grid-row: 2; text-align:center; font-weight:900; font-size:1.8rem; 
        color:#475569; text-shadow:0 1px 2px rgba(0,0,0,0.1);
      }}
      .val-green {{ color:#059669; }}
      .val-blue  {{ color:#2563eb; }}
      .val-red   {{ color:#dc2626; }}

      @media (max-width: 900px) {{
        .id-title {{ font-size: 1.4rem; }}
        .val {{ font-size: 1.1rem; padding:8px 12px; }}
        .op  {{ font-size: 1.5rem; }}
        .lbl {{ font-size: 0.9rem; }}
      }}
    </style>

    <div class="id-grid">
      <!-- 1. satır: etiketler -->
      <div class="lbl" style="grid-column:1;">Opening Balance</div>
      <div class="lbl" style="grid-column:3;">Daily Deposits</div>
      <div class="lbl" style="grid-column:5;">Daily Withdrawals</div>
      <div class="lbl" style="grid-column:7;">Closing Balance</div>

      <!-- 2. satır: değerler + operatörler -->
      <div class="val val-green" style="grid-column:1;">{fmt_bn(open_bn)}</div>
      <div class="op"             style="grid-column:2;">+</div>

      <div class="val val-blue"  style="grid-column:3;">{fmt_bn(depo_bn)}</div>
      <div class="op"             style="grid-column:4;">−</div>

      <div class="val val-red"   style="grid-column:5;">{fmt_bn(wdrw_bn)}</div>
      <div class="op"             style="grid-column:6;">=</div>

      <div class="val val-green" style="grid-column:7;">{fmt_bn(close_bn)}</div>
    </div>
    """)

    st.markdown(html, unsafe_allow_html=True)

# --------------------------- Row 1: Dikey bar (latest) ------------
st.subheader("💰 Latest Day — Deposits & Withdrawals")
st.caption("Daily cash flows in billions of dollars")

df_lvl = pd.DataFrame({
    "label":["Deposits","Withdrawals"],
    "value":[bn(depo_latest) or 0.0, bn(wdrw_latest) or 0.0]
})

st.altair_chart(vbar(df_lvl, "value", "Billions of $", [COLOR_DEP, COLOR_WDR]),
                use_container_width=True, theme=None)

# --------------------------- Closing line: baseline -> latest -----
st.subheader(f"📈 TGA Closing Balance Trend")
st.caption(f"Daily closing balance from {t_base.strftime('%Y-%m-%d')} to {t_latest.strftime('%Y-%m-%d')} (computed from opening + deposits − withdrawals)")

# Aralıktaki serileri çek
open_df = fetch_series(OPEN, t_base.isoformat(), t_latest.isoformat())
dep_df  = fetch_series(DEPO, t_base.isoformat(), t_latest.isoformat())
wdw_df  = fetch_series(WDRW, t_base.isoformat(), t_latest.isoformat())

# Full daily index (tüm günleri eksene koy)
full_dates = pd.DataFrame({"record_date": pd.date_range(t_base, t_latest, freq="D")})

ts = full_dates.merge(open_df.rename(columns={"value_M":"open_M"}),  on="record_date", how="left")\
               .merge(dep_df.rename(columns={"value_M":"depo_M"}),   on="record_date", how="left")\
               .merge(wdw_df.rename(columns={"value_M":"wdrw_M"}),   on="record_date", how="left")

# Closing hesapla - sadece veri olan günler için
ts["closing_bn"] = np.where(
    (ts["open_M"].notna()) | (ts["depo_M"].notna()) | (ts["wdrw_M"].notna()),
    (ts["open_M"].fillna(0)/1000.0) + (ts["depo_M"].fillna(0)/1000.0) - (ts["wdrw_M"].fillna(0)/1000.0),
    np.nan
)

# Forward fill ile eksik günleri doldur (hafta sonları için)
ts["closing_bn"] = ts["closing_bn"].ffill()

# Görselleştirme için sütun adlarını düzelt
ts_plot = ts.rename(columns={"record_date":"date"})[["date","closing_bn"]]

st.altair_chart(
    closing_line_chart(ts_plot, title=f"Baseline: {base_tag}"),
    use_container_width=True,
    theme=None
)

# --------------------------- Metrics Row --------------------------
col1, col2, col3, col4 = st.columns(4)

with col1:
    st.metric(
        label="📊 Current Balance", 
        value=f"${fmt_bn(close_bn)}B",
        delta=None
    )

with col2:
    avg_deposits = df_lvl[df_lvl['label'] == 'Deposits']['value'].iloc[0] if not df_lvl.empty else 0
    st.metric(
        label="💵 Daily Deposits", 
        value=f"${fmt_bn(avg_deposits)}B",
        delta=None
    )

with col3:
    avg_withdrawals = df_lvl[df_lvl['label'] == 'Withdrawals']['value'].iloc[0] if not df_lvl.empty else 0
    st.metric(
        label="💸 Daily Withdrawals", 
        value=f"${fmt_bn(avg_withdrawals)}B",
        delta=None
    )

with col4:
    net_flow = avg_deposits - avg_withdrawals
    st.metric(
        label="🔄 Net Daily Flow", 
        value=f"${fmt_bn(net_flow)}B",
        delta=f"{'Inflow' if net_flow >= 0 else 'Outflow'}"
    )

# --------------------------- Methodology --------------------------
st.markdown("### 📋 Methodology")
with st.expander("Click to expand methodology details"):
    st.markdown(
    """
    #### Calculation Method
    - **Closing Balance is computed**: **Opening + Deposits − Withdrawals** (not fetched directly from the API)
    - All values are converted from millions to billions for better readability
    - Missing weekend/holiday data is forward-filled to create smooth continuous lines
    
    #### Baseline Options
    - **YoY (Year-over-Year)**: Compares current date with same date one year prior
    - **2025-01-01**: Uses beginning of current year as baseline
    
    #### Chart Features
    - **Bar Chart**: Shows latest day's deposits and withdrawals with rounded corners and modern styling
    - **Line Chart**: Displays daily closing balance trend with smooth interpolation and 7-day moving average overlay
    - **Interactive Elements**: Hover tooltips, zoom capabilities, and responsive design
    
    #### Data Source
    - **U.S. Treasury Fiscal Data** — Daily Treasury Statement (`operating_cash_balance`)
    - **API Endpoint**: https://api.fiscaldata.treasury.gov/services/api/fiscal_service
    - **Update Frequency**: Daily (business days)
    
    #### Technical Notes
    - Data gaps on weekends/holidays are handled via forward-fill interpolation
    - Charts use monotonic interpolation for smooth curves between data points
    - Color scheme follows modern design principles with accessibility considerations
    """
    )

# --------------------------- Footer -------------------------------
st.markdown("---")
st.markdown(
    """
    <div style="text-align:center;color:#64748b;font-size:0.95rem;padding:20px 0;">
        <a href="https://veridelisi.substack.com/">Veri Delisi</a><strong>🚀 https://veridelisi.substack.com/</strong><br>
        <em>Engin Yılmaz • Amherst • September 2025 </em>
    </div>
    """,
    unsafe_allow_html=True
)
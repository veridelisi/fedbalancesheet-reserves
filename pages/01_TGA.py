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

# Görsel renkler
COLOR_DEP  = "#2563eb"   # Deposits (blue)
COLOR_WDR  = "#ef4444"   # Withdrawals (red)
COLOR_LINE = "#0f172a"   # Closing line
COLOR_OK   = "#10b981"   # identity result

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
        return 0.0

@st.cache_data(ttl=1800)
def latest_record_date():
    try:
        r = requests.get(f"{BASE}{ENDP}",
                         params={"fields":"record_date","sort":"-record_date","page[size]":1},
                         timeout=40)
        r.raise_for_status()
        js = r.json().get("data", [])
        if not js:
            return None
        return js[0]["record_date"]
    except Exception:
        return None

@st.cache_data(ttl=1800)
def get_value_on_or_before(target_date, account_type):
    """
    Tek bir tarih için (veya öncesindeki) tek bir hesap türünün değerini döndürür (millions).
    """
    try:
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
            return 0.0

        row = data[0]
        for c in NUM_CANDIDATES:
            if c in row and row[c] is not None:
                row[c] = _to_float(row[c])

        for col in COLUMN_PREFS[account_type]:
            if col in row and not pd.isna(row[col]) and row[col] != 0:
                return float(row[col])
        return 0.0
    except Exception:
        return 0.0

@st.cache_data(ttl=1800)
def fetch_series(account_type, start_date, end_date):
    """
    Seçilen tarih aralığında (start..end dahil) tek bir hesap türünün günlük serisini döndürür.
    """
    try:
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
            return pd.DataFrame(columns=["record_date","value_M"])

        df = pd.DataFrame(js)
        
        # numerik kolonları normalize et
        for c in NUM_CANDIDATES:
            if c in df.columns:
                df[c] = df[c].apply(_to_float)
        
        # değer seç
        val_col = None
        for col in COLUMN_PREFS[account_type]:
            if col in df.columns:
                val_col = col
                break
        
        if val_col is None:
            df["value_M"] = 0.0
        else:
            df["value_M"] = df[val_col].fillna(0.0)
        
        # tarih düzeni
        df["record_date"] = pd.to_datetime(df["record_date"])
        out = df[["record_date","value_M"]].groupby("record_date", as_index=False).last()
        return out
    
    except Exception:
        return pd.DataFrame(columns=["record_date","value_M"])

def bn(x):  # millions -> billions
    if x is None or pd.isna(x) or x == 0:
        return 0.0
    return x/1000.0

def fmt_bn(x):
    if x is None or pd.isna(x) or x == 0:
        return "0.0"
    return f"{x:,.1f}"

def create_bar_chart(df, yfield, ytitle, colors, title=""):
    """Dikey bar chart"""
    if df.empty:
        df = pd.DataFrame({"label":[], yfield:[]})
    
    chart = alt.Chart(df).mark_bar(size=60).encode(
        x=alt.X("label:N", title=None, sort=None),
        y=alt.Y(f"{yfield}:Q", axis=alt.Axis(title=ytitle, format=",.1f")),
        color=alt.Color("label:N", legend=None, scale=alt.Scale(range=colors)),
        tooltip=[
            alt.Tooltip("label:N"), 
            alt.Tooltip(f"{yfield}:Q", format=",.1f", title=ytitle)
        ]
    ).properties(
        title=title, 
        height=300,
        width=400
    )
    
    # Add text labels
    text = alt.Chart(df).mark_text(
        dy=-10, 
        fontSize=12, 
        fontWeight="bold"
    ).encode(
        x=alt.X("label:N"),
        y=alt.Y(f"{yfield}:Q"),
        text=alt.Text(f"{yfield}:Q", format=",.1f")
    )
    
    return chart + text

def create_line_chart(ts, title):
    """Line chart for time series"""
    if ts.empty or len(ts) == 0:
        return alt.Chart(pd.DataFrame({"date":[], "closing_bn":[]})).mark_line()

    # Clean data
    ts_clean = ts.dropna(subset=['closing_bn']).copy()
    if len(ts_clean) == 0:
        return alt.Chart(pd.DataFrame({"date":[], "closing_bn":[]})).mark_line()

    base = alt.Chart(ts_clean).encode(
        x=alt.X("date:T", axis=alt.Axis(title="Date")),
        y=alt.Y("closing_bn:Q", axis=alt.Axis(title="Billions of $", format=",.1f")),
        tooltip=[
            alt.Tooltip("date:T", title="Date"),
            alt.Tooltip("closing_bn:Q", format=",.1f", title="Closing Balance (bn)")
        ]
    )
    
    bars = base.mark_bar(color=COLOR_LINE, width=2)


    
    return bars.properties(
        title=title, 
        height=400,
        width=800
    )

# --------------------------- Header -------------------------------
st.title("🏦 TGA Cash Position Statement")
st.caption("Latest snapshot • Baseline (YoY or 2025-01-01) and daily line to the latest date")

# Latest date + baseline seçimi
try:
    _latest = latest_record_date()
    if _latest is None:
        st.error("Failed to fetch latest record date from API")
        st.stop()
except Exception as e:
    st.error(f"Failed to fetch latest record date: {e}")
    st.stop()

t_latest = pd.to_datetime(_latest).date()

c1, c2 = st.columns([1,3])
with c1:
    st.markdown(
        f"""
        <div style="display:inline-block;padding:10px 14px;border:1px solid #e5e7eb;border-radius:10px;background:#fafafa;">
          <div style="font-size:0.95rem;color:#6b7280;margin-bottom:2px;">Latest Record Date</div>
          <div style="font-size:1.15rem;font-weight:600;letter-spacing:0.2px;">{t_latest.strftime('%d.%m.%Y')}</div>
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
with st.spinner("Fetching latest data..."):
    open_latest  = get_value_on_or_before(t_latest.isoformat(), OPEN)
    depo_latest  = get_value_on_or_before(t_latest.isoformat(), DEPO)
    wdrw_latest  = get_value_on_or_before(t_latest.isoformat(), WDRW)

# Closing = Opening + Deposits − Withdrawals  (billions)
closing_latest_bn = bn(open_latest) + bn(depo_latest) - bn(wdrw_latest)

# --------------------------- Identity line ------------------------
with st.container(border=True):
    # değerleri hesapla (bn = millions -> billions)
    open_bn  = bn(open_latest)
    depo_bn  = bn(depo_latest)
    wdrw_bn  = bn(wdrw_latest)
    close_bn = closing_latest_bn  # Opening + Deposits − Withdrawals (computed)

    html = f"""
    <style>
      .id-grid {{
        display: grid;
        grid-template-columns: 1fr auto 1fr auto 1fr auto 1fr;
        grid-template-rows: auto auto;
        column-gap: 16px; row-gap: 8px;
        align-items: center; width: 100%;
      }}
      .lbl {{ color:#6b7280; font-size:.95rem; grid-row: 1; text-align: center; }}
      .val {{
        grid-row: 2;
        display:inline-block; padding:8px 12px; border-radius:10px;
        background:#f6f7f9; font-weight:700; font-size:1.25rem;
        text-align: center;
      }}
      .op  {{ grid-row: 2; text-align:center; font-weight:800; font-size:1.5rem; color:#374151; }}
      .val-green {{ color:#10b981; }}
      .val-blue  {{ color:#2563eb; }}
      .val-red   {{ color:#ef4444; }}

      @media (max-width: 900px) {{
        .val {{ font-size: 1.05rem; padding:6px 10px; }}
        .op  {{ font-size: 1.3rem; }}
      }}
    </style>

    <div class="id-grid">
      <!-- 1. satır: etiketler -->
      <div class="lbl" style="grid-column:1;">Opening</div>
      <div class="lbl" style="grid-column:3;">Deposits</div>
      <div class="lbl" style="grid-column:5;">Withdrawals</div>
      <div class="lbl" style="grid-column:7;">Closing</div>

      <!-- 2. satır: değerler + operatörler -->
      <div class="val val-green" style="grid-column:1;">{fmt_bn(open_bn)}</div>
      <div class="op"             style="grid-column:2;">+</div>

      <div class="val val-blue"  style="grid-column:3;">{fmt_bn(depo_bn)}</div>
      <div class="op"             style="grid-column:4;">−</div>

      <div class="val val-red"   style="grid-column:5;">{fmt_bn(wdrw_bn)}</div>
      <div class="op"             style="grid-column:6;">=</div>

      <div class="val val-green" style="grid-column:7;">{fmt_bn(close_bn)}</div>
    </div>
    """

    st.markdown(html, unsafe_allow_html=True)

# --------------------------- Row 1: Dikey bar (latest) ------------
st.subheader("Latest Day — Deposits & Withdrawals (bn)")

# Create chart data
chart_data = pd.DataFrame({
    "label": ["Deposits", "Withdrawals"],
    "value": [bn(depo_latest), bn(wdrw_latest)]
})

chart = create_bar_chart(
    chart_data, 
    "value", 
    "Billions of $", 
    [COLOR_DEP, COLOR_WDR],
    ""
)

st.altair_chart(chart, use_container_width=True)

# --------------------------- Closing line: baseline -> latest -----
st.subheader(f"TGA Closing Balance — from {t_base.strftime('%Y-%m-%d')} to {t_latest.strftime('%Y-%m-%d')} (computed)")

with st.spinner("Loading time series data..."):
    # Aralıktaki serileri çek
    open_df = fetch_series(OPEN, t_base.isoformat(), t_latest.isoformat())
    dep_df  = fetch_series(DEPO, t_base.isoformat(), t_latest.isoformat())
    wdw_df  = fetch_series(WDRW, t_base.isoformat(), t_latest.isoformat())

    # Full daily index (tüm günleri eksene koy)
    full_dates = pd.DataFrame({"record_date": pd.date_range(t_base, t_latest, freq="D")})

    # Merge all data
    ts = full_dates.merge(
        open_df.rename(columns={"value_M":"open_M"}), 
        on="record_date", 
        how="left"
    ).merge(
        dep_df.rename(columns={"value_M":"depo_M"}), 
        on="record_date", 
        how="left"
    ).merge(
        wdw_df.rename(columns={"value_M":"wdrw_M"}), 
        on="record_date", 
        how="left"
    )

    # Fill missing values with 0
    ts = ts.fillna(0.0)

    # Closing (bn) hesapla
    ts["closing_bn"] = (ts["open_M"]/1000.0) + (ts["depo_M"]/1000.0) - (ts["wdrw_M"]/1000.0)

    # Görselleştirme için sütun adlarını düzelt
    ts_plot = ts.rename(columns={"record_date":"date"})[["date","closing_bn"]]

line_chart = create_line_chart(ts_plot, f"Baseline: {base_tag}")
st.altair_chart(line_chart, use_container_width=True)

# Show some basic stats
if not ts_plot.empty and len(ts_plot) > 0:
    col1, col2, col3, col4 = st.columns(4)
    
    with col1:
        current_balance = ts_plot["closing_bn"].iloc[-1] if len(ts_plot) > 0 else 0
        st.metric("Current Balance", f"{fmt_bn(current_balance)} B")
    
    with col2:
        max_balance = ts_plot["closing_bn"].max() if len(ts_plot) > 0 else 0
        st.metric("Maximum", f"{fmt_bn(max_balance)} B")
    
    with col3:
        min_balance = ts_plot["closing_bn"].min() if len(ts_plot) > 0 else 0
        st.metric("Minimum", f"{fmt_bn(min_balance)} B")
    
    with col4:
        avg_balance = ts_plot["closing_bn"].mean() if len(ts_plot) > 0 else 0
        st.metric("Average", f"{fmt_bn(avg_balance)} B")

# --------------------------- Methodology --------------------------
st.markdown("### Methodology")
st.markdown(
"""
- **Closing is computed**: **Opening + Deposits − Withdrawals** (not fetched from the API).
- Baseline selection: **YoY (t − 1 year)** (default) or **2025-01-01**.
- **Line chart**: daily values are plotted from the selected baseline date to the latest date; all days are shown on the axis.
- Source: U.S. Treasury Fiscal Data — *Daily Treasury Statement* (`operating_cash_balance`).

"""
)

# --------------------------- Footer -------------------------------
st.markdown(
    """
    <hr style="margin-top:28px;margin-bottom:10px;border:none;border-top:1px solid #e5e7eb;">
    <div style="text-align:center;color:#6b7280;font-size:0.95rem;">
        <strong>Engin Yılmaz</strong> · September 2025
    </div>
    """,
    unsafe_allow_html=True
)
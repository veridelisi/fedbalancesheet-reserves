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

col1, col2, col3, col4 = st.columns([1,1,1,1])
with col1:
    st.page_link("streamlit_app.py", label="🏠 Home")
with col2:
    st.page_link("pages/01_Reserves.py", label="📊 Reserves")
with col3:
    st.page_link("pages/01_Repo.py", label="🔄 Repo")
with col4:
    st.page_link("pages/01_TGA.py", label="🔄 TGA")

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

COLOR_DEP  = "#2563eb"  # blue
COLOR_WDR  = "#ef4444"  # red
COLOR_GRAY = "#94a3b8"
COLOR_DARK = "#0f172a"
COLOR_OK   = "#10b981"

# Dataset sürümlerine göre değişebilen kolon isimleri
# YERİNE GEÇSİN
COLUMN_PREFS = {
    OPEN : ["open_today_bal"],                 # Opening
    DEPO : ["today_amt", "open_today_bal"],    # Deposits
    WDRW : ["today_amt", "open_today_bal"],    # Withdrawals
}

NUM_CANDIDATES = {"open_today_bal", "close_today_bal", "today_amt"}
SAFE_FIELDS    = ["record_date", "account_type", "open_today_bal", "close_today_bal", "today_amt"]


# --------------------------- Helpers -------------------------------
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

def _to_float(x):
    try:
        return float(str(x).replace(",", "").replace("$", ""))
    except:
        return math.nan


@st.cache_data(ttl=1800)
def get_value_on_or_before(target_date: str, account_type: str) -> float | None:
    """
    Verilen hesap türü için target_date tarihindeki (veya öncesindeki) son değeri döndürür.
    Değerler *milyon $* olarak gelir.
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
        # Bazı ortamlarda fields parametresi reddedilirse 'fields'ı çıkartıp tekrar dene
        params.pop("fields", None)
        r = requests.get(url, params=params, timeout=40)
        r.raise_for_status()

    data = r.json().get("data", [])
    if not data:
        return None

    row = data[0]
    # numerikleri normalize et
    for c in NUM_CANDIDATES:
        if c in row and row[c] is not None:
            try:
                row[c] = float(str(row[c]).replace(",", "").replace("$", ""))
            except:
                row[c] = math.nan

    # tercih sırasına göre ilk mevcut alanı seç
    for col in COLUMN_PREFS[account_type]:
        if col in row and pd.notna(row[col]):
            return float(row[col])

    return None


def bn(x):  # millions -> billions
    return None if x is None or pd.isna(x) else x/1000.0

def fmt_bn(x):
    if x is None or pd.isna(x): return "—"
    return f"{x:,.1f}"

def vbar(df, yfield, ytitle, colors, title=""):
    """Dikey bar: df -> columns [label, value]."""
    if df.empty:
        df = pd.DataFrame({"label":[], yfield:[]})
    base = alt.Chart(df).encode(
        x=alt.X("label:N", title=None, sort=None),
        y=alt.Y(f"{yfield}:Q", axis=alt.Axis(title=ytitle, format=",.1f")),
        tooltip=[alt.Tooltip("label:N"), alt.Tooltip(f"{yfield}:Q", format=",.1f", title=ytitle)],
    )
    bars = base.mark_bar().encode(color=alt.Color("label:N", legend=None,
                                                  scale=alt.Scale(range=colors)))
    labels = base.mark_text(dy=-6, align="center", fontWeight="bold").encode(
        text=alt.Text(f"{yfield}:Q", format=",.1f")
    )
    return (bars + labels).properties(title=(title or ""), height=260,
                                      padding={"top":28,"right":8,"left":8,"bottom":8})

def vbar_delta(df, yfield, ytitle, colors, title=""):
    """Dikey bar (Δ). 0 referans çizgisiyle."""
    if df.empty:
        df = pd.DataFrame({"label":[], yfield:[]})
    base = alt.Chart(df).encode(
        x=alt.X("label:N", title=None, sort=None),
        y=alt.Y(f"{yfield}:Q", axis=alt.Axis(title=ytitle, format=",.1f")),
        tooltip=[alt.Tooltip("label:N"), alt.Tooltip(f"{yfield}:Q", format=",.1f", title=ytitle)],
    )
    bars = base.mark_bar().encode(color=alt.Color("label:N", legend=None,
                                                  scale=alt.Scale(range=colors)))
    zero = alt.Chart(pd.DataFrame({"y":[0]})).mark_rule(color="#111").encode(y="y:Q")
    labels = base.mark_text(dy=-6, align="center", fontWeight="bold").encode(
        text=alt.Text(f"{yfield}:Q", format=",.1f")
    )
    return (bars + zero + labels).properties(title=(title or ""), height=260,
                                             padding={"top":28,"right":8,"left":8,"bottom":8})

# --------------------------- Header -------------------------------
st.title("🏦 TGA — Deposits, Withdrawals & Closing (computed)")
st.caption("Latest snapshot • Annual compare vs selected baseline (YoY or 2025-01-01)")

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
        <div style="display:inline-block;padding:10px 14px;border:1px solid #e5e7eb;border-radius:10px;background:#fafafa;">
          <div style="font-size:0.95rem;color:#6b7280;margin-bottom:2px;">Latest Record Date</div>
          <div style="font-size:1.15rem;font-weight:600;letter-spacing:0.2px;">{t_latest.strftime('%d.%m.%Y')}</div>
        </div>
        """,
        unsafe_allow_html=True
    )
with c2:
    baseline_label = st.radio(
        "Annual baseline",
        ("YoY (t - 1 year)", "01.01.2025"),
        index=0, horizontal=True
    )

if baseline_label.startswith("YoY"):
    t_base = (t_latest - relativedelta(years=1))
    base_tag = "YoY"
else:
    t_base = date(2025,1,1)
    base_tag = "2025-01-01"

# --------------------------- Fetch values (M$) --------------------
open_latest  = get_value_on_or_before(t_latest.isoformat(), OPEN)
depo_latest  = get_value_on_or_before(t_latest.isoformat(), DEPO)
wdrw_latest  = get_value_on_or_before(t_latest.isoformat(), WDRW)

open_base  = get_value_on_or_before(t_base.isoformat(), OPEN)
depo_base  = get_value_on_or_before(t_base.isoformat(), DEPO)
wdrw_base  = get_value_on_or_before(t_base.isoformat(), WDRW)

# --------------------------- Compute closing (FORMÜL) -------------
# Closing = Opening + Deposits − Withdrawals
closing_latest_bn = (bn(open_latest) or 0) + (bn(depo_latest) or 0) - (bn(wdrw_latest) or 0)
closing_base_bn   = None
if open_base is not None and depo_base is not None and wdrw_base is not None:
    closing_base_bn = (bn(open_base) or 0) + (bn(depo_base) or 0) - (bn(wdrw_base) or 0)

# --------------------------- Identity line ------------------------
with st.container(border=True):
    st.subheader("Latest day identity (billions of $)")
    st.markdown(
        f"""
        <div style="font-size:1.1rem;">
        <strong>Opening</strong> <span style="color:#6b7280;">(+)</span>
        <strong>Deposits</strong> <span style="color:#6b7280;">(−)</span>
        <strong>Withdrawals</strong> <span style="color:#6b7280;">=</span>
        <strong>Closing</strong><br/>
        <code>{fmt_bn(bn(open_latest))}</code> +
        <code style="color:{COLOR_DEP};">{fmt_bn(bn(depo_latest))}</code> −
        <code style="color:{COLOR_WDR};">{fmt_bn(bn(wdrw_latest))}</code> =
        <code style="color:{COLOR_OK};">{fmt_bn(closing_latest_bn)}</code>
        </div>
        """,
        unsafe_allow_html=True
    )

# --------------------------- Row 1 (DİKEY) ------------------------
cA, cB = st.columns(2)
with cA:
    st.subheader("Latest Day — Deposits & Withdrawals (bn)")
    df_lvl = pd.DataFrame({
        "label":["Deposits","Withdrawals"],
        "value":[bn(depo_latest) or 0.0, bn(wdrw_latest) or 0.0]
    })
    st.altair_chart(vbar(df_lvl, "value", "Billions of $", [COLOR_DEP, COLOR_WDR]),
                    use_container_width=True, theme=None)

with cB:
    st.subheader(f"Annual Δ — per {base_tag} baseline")
    d_dep = (bn(depo_latest) or 0.0) - (bn(depo_base) or 0.0 if depo_base is not None else 0.0)
    d_wdr = (bn(wdrw_latest) or 0.0) - (bn(wdrw_base) or 0.0 if wdrw_base is not None else 0.0)
    df_delta = pd.DataFrame({"label":["Deposits Δ","Withdrawals Δ"], "value":[d_dep, d_wdr]})
    st.altair_chart(vbar_delta(df_delta, "value", "Change (billions of $)", [COLOR_DEP, COLOR_WDR]),
                    use_container_width=True, theme=None)

# --------------------------- Row 2: Closing compare (FORMÜL) -----
st.subheader(f"TGA Closing Balance — Baseline vs Latest (computed, per {base_tag})")
df_close = pd.DataFrame({
    "label":[f"Baseline ({t_base.strftime('%Y-%m-%d')})", f"Latest ({t_latest.strftime('%Y-%m-%d')})"],
    "value":[closing_base_bn if closing_base_bn is not None else np.nan,
             closing_latest_bn]
})
st.altair_chart(vbar(df_close, "value", "Billions of $", [COLOR_GRAY, COLOR_DARK]),
                use_container_width=True, theme=None)

# --------------------------- Methodology --------------------------
st.markdown("### Methodology")
st.markdown(
"""
- **Source:** U.S. Treasury Fiscal Data — *Daily Treasury Statement* (`operating_cash_balance`).
- **Closing is computed** (not fetched): **Opening + Deposits − Withdrawals**.
- Baseline: **YoY (t − 1y)** (default) veya **2025-01-01** (radyo seçimi).
- Units: API ham verisi **millions**; ekranda **billions** gösterilir.
- İlk satırdaki grafikler dikeydir: solda **latest-day seviyeleri**, sağda **yıllık değişim (Δ)**.
- Baseline bir tatil/hafta sonuna denk gelirse, o tarihten **önceki en yakın** gözlem kullanılır.
"""
)

# --------------------------- Footer -------------------------------
st.markdown(
    """
    <hr style="margin-top:28px;margin-bottom:10px;border:none;border-top:1px solid #e5e7eb;">
    <div style="text-align:center;color:#6b7280;font-size:0.95rem;">
        <strong>Engin Yılmaz</strong> · Visiting Research Scholar · UMASS Amherst · September 2025
    </div>
    """,
    unsafe_allow_html=True
)
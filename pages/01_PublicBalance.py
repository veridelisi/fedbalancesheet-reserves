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


# ---------------- API ----------------
BASE = "https://api.fiscaldata.treasury.gov/services/api/fiscal_service"
ENDP = "/v1/accounting/dts/deposits_withdrawals_operating_cash"


# ---------------- Helpers ----------------
def to_num(x):
    """Virgül/boşluk temizleyip float döndür."""
    return pd.to_numeric(str(x).replace(",", "").strip(), errors="coerce")

def bn(m):
    """$M → $Bn"""
    return float(m) / 1000.0

def fmt_bn(x):
    return f"{x:,.1f}"

def get_latest_date():
    url = f"{BASE}{ENDP}?fields=record_date&sort=-record_date&page[size]=1"
    r = requests.get(url, timeout=40)
    r.raise_for_status()
    js = r.json().get("data", [])
    if not js:
        raise RuntimeError("No data returned for latest date.")
    return js[0]["record_date"]

def fetch_day_records(on_or_before: str):
    """
    İstenen tarihte veya öncesindeki **son** günü getirir (lte + sort desc).
    """
    url = (
        f"{BASE}{ENDP}"
        f"?filter=record_date:lte:{on_or_before}"
        f"&sort=-record_date&page[size]=1"
        f"&fields=record_date"
    )
    r = requests.get(url, timeout=40)
    r.raise_for_status()
    rows = r.json().get("data", [])
    if not rows:
        return None, pd.DataFrame()
    picked = rows[0]["record_date"]

    # O günün tüm kayıtları:
    url2 = (
        f"{BASE}{ENDP}"
        f"?filter=record_date:eq:{picked}"
        f"&sort=transaction_catg&page[size]=500"
        f"&fields=record_date,transaction_type,transaction_catg,transaction_today_amt"
    )
    r2 = requests.get(url2, timeout=60)
    r2.raise_for_status()
    df = pd.DataFrame(r2.json().get("data", []))
    return picked, df


def compute_flows(df_day: pd.DataFrame):
    """
    Bir günün verisinden Taxes, Expenditures, NewDebt, DebtRedemp ve
    ayrıntı tablolarını çıkar. (Sıkılaştırma: iloc fallback + isim temizliği)
    """
    if df_day.empty:
        return None

    # Sayısal ve temizlik
    df = df_day.copy()
    df["amt"] = df["transaction_today_amt"].map(to_num).fillna(0.0)
    df["transaction_catg"] = (
        df["transaction_catg"]
        .replace({None: "Unclassified", "null": "Unclassified"})
        .fillna("Unclassified")
    )

    # ---- Deposits ----
    dep = df[df["transaction_type"].str.lower() == "deposits"].copy()
    dep = dep.sort_values("transaction_catg")
    total_dep = dep["amt"].sum()

    # Fallback: son iki satır varsayımı (Table IIIB + Total)
    if len(dep) >= 2:
        dep_newdebt = float(dep["amt"].iloc[-2])  # Public Debt Cash Issues (IIIB)
        dep_total_last = float(dep["amt"].iloc[-1])  # Total
        # Emniyet: eğer toplam ile sum uyuşmuyorsa yine de sum'ı kullan
        total_dep = float(dep["amt"].sum())
    else:
        dep_newdebt = 0.0
        dep_total_last = total_dep

    taxes = total_dep - dep_newdebt

    # Top-10 taxes havuzu (Total & IIIB hariç)
    dep_pool = dep.iloc[:-2].copy() if len(dep) >= 2 else dep.copy()
    # Emniyet ismiyle de dışarıda tut
    dep_lc = dep_pool["transaction_catg"].str.lower()
    mask_excl_dep = (
        dep_lc.str.contains("public debt cash issues", na=False)
        | dep_lc.str.contains("table iiib", na=False)
        | dep_lc.str.contains("total", na=False)
    )
    dep_pool = dep_pool.loc[~mask_excl_dep].copy()
    dep_pool.rename(
        columns={"transaction_catg": "Category", "amt": "Amount ($M)"},
        inplace=True,
    )
    dep_pool["Share of Taxes (%)"] = (
        100.0 * dep_pool["Amount ($M)"] / taxes if taxes != 0 else 0.0
    )

    # ---- Withdrawals ----
    w = df[df["transaction_type"].str.lower() == "withdrawals"].copy()
    w = w.sort_values("transaction_catg")
    total_w = w["amt"].sum()

    if len(w) >= 2:
        w_redemp = float(w["amt"].iloc[-2])  # Public Debt Cash Redemptions (IIIB)
        w_total_last = float(w["amt"].iloc[-1])  # Total
        total_w = float(w["amt"].sum())
    else:
        w_redemp = 0.0
        w_total_last = total_w

    expenditures = total_w - w_redemp

    # Top-10 expenditures havuzu (Total & IIIB hariç)
    w_pool = w.iloc[:-2].copy() if len(w) >= 2 else w.copy()
    w_lc = w_pool["transaction_catg"].str.lower()
    mask_excl_w = (
        w_lc.str.contains("public debt cash redemp", na=False)
        | w_lc.str.contains("table iiib", na=False)
        | w_lc.str.contains("total", na=False)
    )
    w_pool = w_pool.loc[~mask_excl_w].copy()
    w_pool.rename(
        columns={"transaction_catg": "Category", "amt": "Amount ($M)"},
        inplace=True,
    )
    w_pool["Share of Expenditures (%)"] = (
        100.0 * w_pool["Amount ($M)"] / expenditures if expenditures != 0 else 0.0
    )

    # Sonuçlar
    return dict(
        taxes=taxes,
        newdebt=dep_newdebt,
        expenditures=expenditures,
        redemp=w_redemp,
        dep_pool=dep_pool,
        w_pool=w_pool,
    )


def bar_pair(title, baseline_val_bn, latest_val_bn, color):
    """
    Baseline vs Latest küçük çubuk grafik (Altair).
    """
    data = pd.DataFrame(
        {
            "Label": ["Baseline", "Latest"],
            "Value": [baseline_val_bn, latest_val_bn],
        }
    )
    chart = (
        alt.Chart(data, title=title)
        .mark_bar()
        .encode(
            x=alt.X("Label:N", axis=alt.Axis(title=None)),
            y=alt.Y("Value:Q", axis=alt.Axis(title="Billions of $")),
            color=alt.value(color),
            tooltip=[alt.Tooltip("Label:N"), alt.Tooltip("Value:Q", format=",.1f")],
        )
        .properties(height=260)
    )
    labels = chart.mark_text(
        dy=-8,
        fontWeight="bold",
        color="black",
    ).encode(text=alt.Text("Value:Q", format=",.1f"))
    return chart + labels


def bar_top_share(df, value_col, share_col, title, bar_color):
    """Yüzde katkılarına göre Top-10 yatay çubuk."""
    dd = df.sort_values(share_col, ascending=True).tail(10)
    ch = (
        alt.Chart(dd, title=title)
        .mark_bar(color=bar_color)
        .encode(
            x=alt.X(f"{share_col}:Q", axis=alt.Axis(title="%")),
            y=alt.Y("Category:N", sort="-x", axis=alt.Axis(title=None)),
            tooltip=[
                alt.Tooltip("Category:N"),
                alt.Tooltip(value_col, type="quantitative", title="Amount ($M)", format=",.0f"),
                alt.Tooltip(share_col, type="quantitative", title="Share (%)", format=",.1f"),
            ],
        )
        .properties(height=320)
    )
    return ch


# ---------------- UI ----------------



with st.spinner("Fetching latest Treasury DTS data..."):
    latest_iso = get_latest_date()
    latest_dt, df_latest = fetch_day_records(latest_iso)
    if df_latest.empty:
        st.error("No data returned for the latest day.")
        st.stop()

# Baseline seçimi
colA, colB = st.columns([1, 3])
with colA:
    st.markdown(
        f"""
        <div style="display:inline-block; padding:10px 14px; border:1px solid #e5e7eb; 
            border-radius:10px; background:#fafafa;">
            <div style="font-size:0.95rem; color:#6b7280;">Latest day</div>
            <div style="font-size:1.15rem; font-weight:600;">{pd.to_datetime(latest_dt).strftime('%d.%m.%Y')}</div>
        </div>
        """,
        unsafe_allow_html=True,
    )

with colB:
    baseline_choice = st.radio(
        "Annual baseline",
        ("YoY (t − 1 year)", "01.01.2025"),
        horizontal=True,
        index=0,
    )

# Baz tarihi belirle
if baseline_choice.startswith("YoY"):
    base_date = (pd.to_datetime(latest_dt) - relativedelta(years=1)).date().isoformat()
    base_label = "YoY baseline"
else:
    base_date = date(2025, 1, 1).isoformat()
    base_label = "Fixed 2025-01-01"

# Baz veriyi çek
with st.spinner(f"Fetching baseline day on/before {base_date} ..."):
    base_dt, df_base = fetch_day_records(base_date)
    if df_base.empty:
        st.warning("Baseline day could not be fetched; using latest as baseline for display.")
        base_dt, df_base = latest_dt, df_latest.copy()

# Akım bileşenlerini çıkar
latest = compute_flows(df_latest)
base = compute_flows(df_base)

if latest is None or base is None:
    st.error("Failed to compute flows.")
    st.stop()

# Kimlik eşitliği: ΔTGA'ya göre göster
latest_delta_bn = bn(latest["taxes"] + latest["newdebt"] - latest["expenditures"] - latest["redemp"])

# ---------------- Identity (4 değer) ----------------
st.subheader("Latest day identity — components (billions of $)")
c1, c2, c3, c4, c5 = st.columns([1, 1, 1, 1, 2])

with c1:
    st.markdown("**Taxes**")
    st.metric(label="", value=fmt_bn(bn(latest["taxes"])))

with c2:
    st.markdown("**Expenditures**")
    st.metric(label="", value=fmt_bn(bn(latest["expenditures"])))

with c3:
    st.markdown("**New Debt (IIIB)**")
    st.metric(label="", value=fmt_bn(bn(latest["newdebt"])))

with c4:
    st.markdown("**Debt Redemp (IIIB)**")
    st.metric(label="", value=fmt_bn(bn(latest["redemp"])))

with c5:
    st.markdown("**Daily Result**")
    st.metric( value=fmt_bn(latest_delta_bn))

st.markdown("---")

# ---------------- Annual compare — 3 grafik ----------------
st.subheader(f"Annual compare per baseline ({base_label})")

left, mid, right = st.columns(3)
with left:
    ch = bar_pair(
        f"Taxes — Baseline ({base_dt}) vs Latest ({latest_dt})",
        bn(base["taxes"]),
        bn(latest["taxes"]),
        color="#2563eb",
    )
    st.altair_chart(ch, use_container_width=True)

with mid:
    ch = bar_pair(
        f"Expenditures — Baseline ({base_dt}) vs Latest ({latest_dt})",
        bn(base["expenditures"]),
        bn(latest["expenditures"]),
        color="#ef4444",
    )
    st.altair_chart(ch, use_container_width=True)

with right:
    base_debt_net = bn(base["newdebt"] - base["redemp"])
    latest_debt_net = bn(latest["newdebt"] - latest["redemp"])
    ch = bar_pair(
        f"Debt net (New Debt − Redemp) — Baseline vs Latest",
        base_debt_net,
        latest_debt_net,
        color="#6b7280",
    )
    st.altair_chart(ch, use_container_width=True)

st.markdown("---")

# ---------------- Top-10 (% pay) — Taxes & Expenditures ----------------
st.subheader("Daily Top-10 contributors (share %)")

colL, colR = st.columns(2)

with colL:
    st.caption("Taxes — Top-10 categories (share of Taxes)")
    st.altair_chart(
        bar_top_share(
            latest["dep_pool"],
            value_col="Amount ($M)",
            share_col="Share of Taxes (%)",
            title=f"Latest {latest_dt}",
            bar_color="#2563eb",
        ),
        use_container_width=True,
    )

with colR:
    st.caption("Expenditures — Top-10 categories (share of Expenditures)")
    st.altair_chart(
        bar_top_share(
            latest["w_pool"],
            value_col="Amount ($M)",
            share_col="Share of Expenditures (%)",
            title=f"Latest {latest_dt}",
            bar_color="#ef4444",
        ),
        use_container_width=True,
    )

st.markdown("---")

# ---------------- Tam tablolar (seviye) ----------------
st.subheader("Category-level tables (latest day)")
t1, t2 = st.columns(2)

with t1:
    st.markdown("**Taxes pool (Deposits excl. IIIB & Total)**")
    dep_tbl = latest["dep_pool"].copy()
    dep_tbl["Amount ($Bn)"] = dep_tbl["Amount ($M)"] / 1000.0
    st.dataframe(
        dep_tbl[["Category", "Amount ($Bn)", "Share of Taxes (%)"]].sort_values("Amount ($Bn)", ascending=False),
        use_container_width=True,
    )

with t2:
    st.markdown("**Expenditures pool (Withdrawals excl. IIIB & Total)**")
    w_tbl = latest["w_pool"].copy()
    w_tbl["Amount ($Bn)"] = w_tbl["Amount ($M)"] / 1000.0
    st.dataframe(
        w_tbl[["Category", "Amount ($Bn)", "Share of Expenditures (%)"]].sort_values("Amount ($Bn)", ascending=False),
        use_container_width=True,
    )

# ---------------- Footer ----------------
st.markdown(
    """
    <hr style="margin-top:28px; margin-bottom:10px; border:none; border-top:1px solid #e5e7eb;">
    <div style="text-align:center; color:#6b7280; font-size:0.95rem;">
        <strong>Engin Yılmaz</strong> · Visiting Research Scholar · UMASS Amherst · September 2025
    </div>
    """,
    unsafe_allow_html=True,
)

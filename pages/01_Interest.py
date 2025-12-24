# streamlit_app.py
# NY Fed Reference Rates (EFFR, OBFR, SOFR, BGCR, TGCR)
# Run:  pip install streamlit pandas requests altair python-dateutil
#       streamlit run streamlit_app.py

import io
import requests
import pandas as pd
import altair as alt
import streamlit as st
from datetime import date, timedelta

st.set_page_config(page_title="NY Fed Reference Rates", layout="wide")

# ---------------------------- Top nav (your template) -----------------
cols = st.columns(11)
with cols[0]:
    st.page_link("streamlit_app.py", label="🏠 Home")
with cols[1]:
    st.page_link("pages/01_Reserves.py", label="🌍 Reserves")
with cols[2]:
    st.page_link("pages/01_FDIC.py", label="🏦 FDIC")
with cols[3]:
    st.page_link("pages/01_Repo.py", label="🔄 Repo")
with cols[4]:
    st.page_link("pages/01_Repo2.py", label="♻️ Repo 2")
with cols[5]:
    st.page_link("pages/01_TGA.py", label="🏛️ TGA")
with cols[6]:
    st.page_link("pages/01_PublicBalance.py", label="📊 P.Balance")
with cols[7]:
    st.page_link("pages/01_Interest.py", label="📈 Rates")
with cols[8]:
    st.page_link("pages/01_Desk.py", label="🛰️ Desk")
with cols[9]:
    st.page_link("pages/01_Yield.py", label="🌍 Yield")
with cols[10]:
    st.page_link("pages/01_Eurodollar.py", label="💡 Eurodollar")

# ---------------------------- STOP Expanded -----------------
st.markdown(
    """
<style>
    [data-testid="stSidebarNav"] {display: none;}
    section[data-testid="stSidebar"][aria-expanded="true"]{display: none;}
</style>
""",
    unsafe_allow_html=True,
)

# ---------------------------- CODE -----------------

API_BASE = "https://markets.newyorkfed.org/api/rates"
SPECS = {
    "EFFR": {"group": "unsecured", "code": "effr"},
    "OBFR": {"group": "unsecured", "code": "obfr"},
    "SOFR": {"group": "secured",   "code": "sofr"},
    "BGCR": {"group": "secured",   "code": "bgcr"},
    "TGCR": {"group": "secured",   "code": "tgcr"},
}

# fixed colors (EFFR black)
COLOR_MAP = {
    "EFFR": "#000000",  # black
    "OBFR": "#D62728",
    "SOFR": "#1F77B4",
    "BGCR": "#2CA02C",
    "TGCR": "#9467BD",
}

# dashed styles (hide legend)
DASH_MAP = {"EFFR":[1,0], "OBFR":[6,3], "SOFR":[1,0], "BGCR":[2,2], "TGCR":[2,3]}

# -------------------------
# Download ONLY date + rate
# -------------------------
def fetch_rates(rate_name: str, last_n: int = 500) -> pd.DataFrame:
    spec = SPECS[rate_name]
    url = f"{API_BASE}/{spec['group']}/{spec['code']}/last/{last_n}.csv"
    r = requests.get(url, timeout=20)
     # Check for HTML or maintenance message
    if "text/html" in r.headers.get("Content-Type", "") or "Site Maintenance" in r.text:
        st.warning(
            "The page you are looking for is temporarily unavailable and will be available shortly.\n\n"
            "We are sorry for any inconvenience and appreciate your patience.\n\n"
            "Thank you."
        )
        st.stop()
    r.raise_for_status()
    raw = pd.read_csv(io.StringIO(r.text))
    if "Effective Date" in raw.columns and "Rate (%)" in raw.columns:
        df = raw[["Effective Date", "Rate (%)"]].copy()
        df.columns = ["date", "rate"]
    else:
        raise ValueError(f"{rate_name} columns not found. Got: {list(raw.columns)}")
    df["date"] = pd.to_datetime(df["date"]).dt.date
    df["series"] = rate_name
    return df.sort_values("date")

def value_on_yoy(df: pd.DataFrame, window_days: int = 7):
    last_date = df["date"].max()
    target = last_date - timedelta(days=365)
    exact = df[df["date"] == target]
    if not exact.empty:
        return float(exact.iloc[0]["rate"])
    tmp = df.copy()
    tmp["diff"] = tmp["date"].apply(lambda d: abs((d - target).days))
    closest = tmp.sort_values(["diff", "date"]).iloc[0]
    if closest["diff"] <= window_days:
        return float(closest["rate"])
    past = df[df["date"] < target]
    return float(past.iloc[-1]["rate"]) if not past.empty else None

def value_on_or_after_anchor(df: pd.DataFrame, anchor: date = date(2025, 1, 1)):
    sub = df[df["date"] >= anchor]
    return float(sub.iloc[0]["rate"]) if not sub.empty else None

def dynamic_y_domain(levels_df: pd.DataFrame, pad_pp: float = 0.04):
    """Return (ymin, ymax) based on selected series; pad in percentage points."""
    if levels_df.empty:
        return None
    lo = float(levels_df["rate"].min())
    hi = float(levels_df["rate"].max())
    if pd.isna(lo) or pd.isna(hi):
        return None
    if abs(hi - lo) < 0.01:  # çok dar aralık → biraz aç
        lo -= pad_pp
        hi += pad_pp
    else:
        lo -= pad_pp
        hi += pad_pp
    return (lo, hi)

def checkbox_row(default_selected=("SOFR",)):
    """5 kutucuk yan yana döndürür, seçilen serileri listeler."""
    series = ["EFFR","OBFR","SOFR","BGCR","TGCR"]
    cols = st.columns(5)
    chosen = []
    for c, s in zip(cols, series):
        with c:
            val = st.checkbox(s, value=(s in default_selected), key=f"chk_{s}_{st.session_state.get('chart_scope','')}")
            if val:
                chosen.append(s)
    return chosen

st.markdown("### 🏦 NY Fed Reference Rates — EFFR · OBFR · SOFR · BGCR · TGCR")

# -------------------------
# Fetch data
# -------------------------
with st.spinner("Fetching rates..."):
    frames, errors = [], []
    for k in SPECS.keys():
        try:
            frames.append(fetch_rates(k, last_n=500))
        except Exception as e:
            errors.append(f"{k}: {e}")
    if errors:
        st.warning("Some series failed:\n\n- " + "\n- ".join(errors))
    data = pd.concat(frames, ignore_index=True) if frames else pd.DataFrame(columns=["date","rate","series"])

if data.empty:
    st.stop()

# -------------------------
# Summary table (values)
# -------------------------
rows = []
anchor_2025 = date(2025, 1, 1)
for s in SPECS.keys():
    ds = data[data["series"] == s].sort_values("date")
    last_date = ds["date"].max()
    last_rate = float(ds.loc[ds["date"] == last_date, "rate"].iloc[0])
    yoy_val   = value_on_yoy(ds)
    a2025_val = value_on_or_after_anchor(ds, anchor_2025)
    rows.append({
        "Series": s,
        "Last Day": last_date.strftime("%Y-%m-%d"),
        "Last Rate (%)": round(last_rate, 4),
        "YoY Value (%)": None if yoy_val is None else round(yoy_val, 4),
        "01-01-2025 Value (%)": None if a2025_val is None else round(a2025_val, 4),
    })
summary_df = pd.DataFrame(rows)
st.markdown("#### 📌 Summary — Last Day • YoY (value) • 01-01-2025 (value)")
st.dataframe(
    summary_df.style.format({
        "Last Rate (%)": "{:.4f}",
        "YoY Value (%)": lambda v: "—" if v is None else f"{v:.4f}",
        "01-01-2025 Value (%)": lambda v: "—" if v is None else f"{v:.4f}",
    }),
    use_container_width=True,
    hide_index=True,
)

# -------------------------
# Prepare LEVELS (long)
# -------------------------
pivot = data.pivot(index="date", columns="series", values="rate").sort_index()
levels_long = pivot.reset_index().melt(id_vars="date", var_name="series", value_name="rate").dropna()
levels_long["date"] = pd.to_datetime(levels_long["date"])
levels_long["dash"] = levels_long["series"].map(DASH_MAP)

# Universal color scale (EFFR black)
COLOR_DOMAIN = ["EFFR","OBFR","SOFR","BGCR","TGCR"]
COLOR_RANGE  = [COLOR_MAP[s] for s in COLOR_DOMAIN]

# =========================================================
# CHART 1 — Last 7 Days — Levels (default: only EFFR)
# =========================================================
st.markdown("### ⏱️ Last 7 Days — Levels")
st.session_state["chart_scope"] = "7d"  # unique keys for checkboxes
sel7 = checkbox_row(default_selected=("SOFR",))
last_all = levels_long["date"].max()
lvl7 = levels_long[(levels_long["date"] >= (last_all - timedelta(days=7))) & (levels_long["series"].isin(sel7))]
domain7 = dynamic_y_domain(lvl7)

chart7 = alt.Chart(lvl7).mark_line().encode(
    x=alt.X("date:T", title="Date"),
    y=alt.Y("rate:Q", title="Rate (%)", scale=alt.Scale(domain=domain7)),
    color=alt.Color("series:N", title="Series", scale=alt.Scale(domain=COLOR_DOMAIN, range=COLOR_RANGE)),
    strokeDash=alt.StrokeDash("dash", legend=None),
    tooltip=["date:T","series:N",alt.Tooltip("rate:Q", title="Rate (%)", format=".4f")],
).properties(height=360)

st.altair_chart(chart7, use_container_width=True)

# =========================================================
# CHART 2 — Since 01-01-2025 — Levels (default: only EFFR)
# =========================================================
st.markdown("### 📅 Since 01-01-2025 — Levels")
st.session_state["chart_scope"] = "ytd"
selytd = checkbox_row(default_selected=("SOFR",))
lvl_ytd = levels_long[(levels_long["date"] >= pd.to_datetime(date(2025,1,1))) & (levels_long["series"].isin(selytd))]
domain_ytd = dynamic_y_domain(lvl_ytd)

chart_ytd = alt.Chart(lvl_ytd).mark_line().encode(
    x=alt.X("date:T", title="Date"),
    y=alt.Y("rate:Q", title="Rate (%)", scale=alt.Scale(domain=domain_ytd)),
    color=alt.Color("series:N", title="Series", scale=alt.Scale(domain=COLOR_DOMAIN, range=COLOR_RANGE)),
    strokeDash=alt.StrokeDash("dash", legend=None),
    tooltip=["date:T","series:N",alt.Tooltip("rate:Q", title="Rate (%)", format=".4f")],
).properties(height=360)

st.altair_chart(chart_ytd, use_container_width=True)
# =========================
# VOLUME CHARTS (Amounts)
# =========================

# Helpers specific to volume charts (kept local so we don't touch earlier code)
def _dynamic_y_domain_volume(df_vol: pd.DataFrame, pad_abs: float = 2.0):
    """
    Return (ymin, ymax) based on selected series volume (in $ Billions).
    Adds a small absolute pad so axis doesn't hug lines.
    """
    if df_vol.empty:
        return None
    lo = float(df_vol["volume"].min())
    hi = float(df_vol["volume"].max())
    if pd.isna(lo) or pd.isna(hi):
        return None
    if abs(hi - lo) < pad_abs:  # very tight range → open a bit
        lo -= pad_abs
        hi += pad_abs
    else:
        lo -= pad_abs
        hi += pad_abs
    return (lo, hi)

def _fetch_volumes(last_n: int = 500) -> pd.DataFrame:
    """
    Fetch only Effective Date + Volume ($Billions) for all series
    without changing the earlier fetch_rates logic.
    """
    frames = []
    for k, spec in SPECS.items():
        url = f"{API_BASE}/{spec['group']}/{spec['code']}/last/{last_n}.csv"
        r = requests.get(url, timeout=20)
        r.raise_for_status()
        raw = pd.read_csv(io.StringIO(r.text))

        # Flexible column detection for date and volume
        # (Typical: 'Effective Date', 'Volume ($Billions)')
        date_col = None
        for c in raw.columns:
            lc = c.lower().strip()
            if lc.startswith("effective") and "date" in lc:
                date_col = c
                break
        vol_col = None
        for c in raw.columns:
            if "volume" in c.lower():
                vol_col = c
                break

        if date_col is None or vol_col is None:
            # If a series has no volume column, skip it gracefully
            continue

        dfv = raw[[date_col, vol_col]].copy()
        dfv.columns = ["date", "volume"]
        dfv["date"] = pd.to_datetime(dfv["date"]).dt.date
        dfv["series"] = k
        frames.append(dfv.sort_values("date"))

    if not frames:
        return pd.DataFrame(columns=["date", "volume", "series"])
    out = pd.concat(frames, ignore_index=True)
    return out

# Build long-form volume data (without touching existing 'data' frame)
with st.spinner("Fetching volumes..."):
    volumes_long = _fetch_volumes(last_n=500)

# Map styles/colors same as rate charts
if not volumes_long.empty:
    volumes_long["date"] = pd.to_datetime(volumes_long["date"])
    volumes_long["dash"] = volumes_long["series"].map(DASH_MAP)
else:
    volumes_long = pd.DataFrame(columns=["date","volume","series","dash"])

# Common color scale
V_COLOR_DOMAIN = ["EFFR","OBFR","SOFR","BGCR","TGCR"]
V_COLOR_RANGE  = [COLOR_MAP[s] for s in V_COLOR_DOMAIN]

# ---------------------------------------------------------
# CHART 3 — Last 7 Days — Levels (Volume Amount)
# ---------------------------------------------------------
st.markdown("### ⏱️ Last 7 Days — Levels volume amount")
st.session_state["chart_scope"] = "vol7d"
sel_vol_7 = checkbox_row(default_selected=("SOFR",))  # 5 kutucuk, EFFR varsayılan
if not volumes_long.empty:
    last_vol_date = volumes_long["date"].max()
    vol7 = volumes_long[
        (volumes_long["date"] >= (last_vol_date - timedelta(days=7))) &
        (volumes_long["series"].isin(sel_vol_7))
    ]
else:
    vol7 = volumes_long

domain_v7 = _dynamic_y_domain_volume(vol7)

chart_vol7 = alt.Chart(vol7).mark_line().encode(
    x=alt.X("date:T", title="Date"),
    y=alt.Y("volume:Q", title="Volume ($ Billions)", scale=alt.Scale(domain=domain_v7)),
    color=alt.Color("series:N", title="Series", scale=alt.Scale(domain=V_COLOR_DOMAIN, range=V_COLOR_RANGE)),
    strokeDash=alt.StrokeDash("dash", legend=None),
    tooltip=["date:T","series:N",alt.Tooltip("volume:Q", title="Volume ($B)", format=".2f")],
).properties(height=360)

st.altair_chart(chart_vol7, use_container_width=True)

# ---------------------------------------------------------
# CHART 4 — Since 01-01-2025 — Levels (Volume Amount)
# ---------------------------------------------------------
st.markdown("### 📅 Since 01-01-2025 — Levels volume amount")
st.session_state["chart_scope"] = "volytd"
sel_vol_ytd = checkbox_row(default_selected=("SOFR",))  # 5 kutucuk, EFFR varsayılan
if not volumes_long.empty:
    vol_ytd = volumes_long[
        (volumes_long["date"] >= pd.to_datetime(date(2025,1,1))) &
        (volumes_long["series"].isin(sel_vol_ytd))
    ]
else:
    vol_ytd = volumes_long

domain_vytd = _dynamic_y_domain_volume(vol_ytd)

chart_volytd = alt.Chart(vol_ytd).mark_line().encode(
    x=alt.X("date:T", title="Date"),
    y=alt.Y("volume:Q", title="Volume ($ Billions)", scale=alt.Scale(domain=domain_vytd)),
    color=alt.Color("series:N", title="Series", scale=alt.Scale(domain=V_COLOR_DOMAIN, range=V_COLOR_RANGE)),
    strokeDash=alt.StrokeDash("dash", legend=None),
    tooltip=["date:T","series:N",alt.Tooltip("volume:Q", title="Volume ($B)", format=".2f")],
).properties(height=360)

st.altair_chart(chart_volytd, use_container_width=True)

# ------------------------------ Methodology ---------------------------
st.markdown("### 📋 Methodology")
with st.expander("🔎 Click to expand methodology details", expanded=False):
    st.markdown(
        """
**What this page shows**  
- 🧭 NY Fed **overnight reference rates** with two level charts:  
  - 📅 **Last 7 business days**  
  - 📆 **Since 2025-01-01 (YTD)**

---

### 🗂️ Data source & fields
- 🇺🇸 **Federal Reserve Bank of New York — Reference Rates API**  
- Retrieved per series: **Effective Date** and **Rate (%)** only.  
- Series supported: **EFFR**, **OBFR**, **SOFR**, **BGCR**, **TGCR**.

---

### 🎛️ Series selection & defaults
- ✅ Default: **SOFR** only.  
- ⬜ Inline checkboxes let you add **EFFR**, **OBFR**, **BGCR**, **TGCR** dynamically.

---

### 📊 Chart behavior
- 📈 Levels (no diffs), business days only, **auto y-axis** (no forced zero).  
- 🧰 Tooltips show **Effective Date** and **Rate (%)**; zoom/pan enabled.  
- 🎨 Style: **EFFR black solid**, OBFR dashed, SOFR solid, **BGCR/TGCR dotted** (dash legend hidden).

---

### 🗺️ Glossary — one-line definitions
- **EFFR** — Overnight **unsecured** federal funds rate among depository institutions (volume-weighted median of fed funds trades).  
- **OBFR** — Overnight **unsecured** bank funding rate combining **fed funds + Eurodollar** transactions (volume-weighted).  
- **SOFR** — Overnight **secured** repo rate backed by **U.S. Treasuries** across tri-party/cleared/bi-lateral transactions (transaction-based).  
- **BGCR** — **Broad** general collateral repo rate from **tri-party** repo excluding specials, across Treasury/agency collateral.  
- **TGCR** — **Tri-party** general collateral repo rate backed by **Treasury** collateral only (ex-specials).

---

### ⚠️ Notes & caveats
- ⏳ Publication timing: latest prints may post next business morning and can revise.  
- 🔁 Missing series on a given date are omitted (no forward-fill).
        """
    )


# --------------------------- Footer -------------------------------
st.markdown("---")
st.markdown(
    """
    <div style="text-align:center;color:#64748b;font-size:0.95rem;padding:20px 0;">
        <a href="https://veridelisi.substack.com/">Veri Delisi</a>🚀 <br>
        <em>Engin Yılmaz • Amherst • September 2025 </em>
    </div>
    """,
    unsafe_allow_html=True
)

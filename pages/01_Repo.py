
# -----------------------------------------------------------------------------
# Streamlit Dashboard — NY Fed Primary Dealer Repo / Reverse Repo
# Son tarih + YoY + 01.01.2025 (YTD)
# -----------------------------------------------------------------------------
import streamlit as st
import pandas as pd
import numpy as np
import requests
from io import StringIO
from datetime import datetime, timedelta
import altair as alt
import datetime as dt

# ---------------------------- Page config -----------------------------
API_URL = "https://markets.newyorkfed.org/api/pd/get/all/timeseries.csv"
st.set_page_config(page_title="NY Fed Primary Dealer • Repo Dashboard", layout="wide")

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

# ------------------------------ Helpers -------------------------------
COLOR_REPO = "#2563eb"   # blue
COLOR_RR   = "#ef4444"   # red

def find_col(cols, candidates):
    """Find a column by a list of candidate names (case-insensitive, partial)."""
    lower = {c.lower(): c for c in cols}
    for cand in candidates:
        if cand.lower() in lower:
            return lower[cand.lower()]
    for c in cols:
        if any(k in c.lower() for k in candidates):
            return c
    return None

def to_num(s):
    if pd.api.types.is_numeric_dtype(s):
        return s
    return pd.to_numeric(s.astype(str).str.replace(",", "").str.strip(), errors="coerce")

@st.cache_data(ttl=60*60, show_spinner=False)
def fetch_data():
    """Load full Primary Dealer timeseries and standardize columns."""
    r = requests.get(API_URL, timeout=60)
    r.raise_for_status()
    df = pd.read_csv(StringIO(r.text))

    date_col   = find_col(df.columns, ["as of date", "date", "asof"])
    series_col = find_col(df.columns, ["time series", "timeseries", "series", "keyid"])
    value_col  = find_col(df.columns, ["value (millions)", "value", "amount"])

    if not date_col or not series_col or not value_col:
        raise RuntimeError(f"Missing required columns. Found: {list(df.columns)}")

    out = df.rename(columns={date_col: "date", series_col: "series", value_col: "value_mn"}).copy()
    out["date"] = pd.to_datetime(out["date"], errors="coerce")
    out["value_mn"] = to_num(out["value_mn"])
    return out.dropna(subset=["date"])

# Reverse Repo (Securities In) — Treasury (exc TIPS)
IRRA_UB_G = "PDSIRRA-UBGUTSET"   # Uncleared Bilateral General
IRRA_UB_S = "PDSIRRA-UBSUTSET"   # Uncleared Bilateral Specified
IRRA_CB_G = "PDSIRRA-CBGUTSET"   # Cleared Bilateral General
IRRA_CB_S = "PDSIRRA-CBSUTSET"   # Cleared Bilateral Specified
IRRA_GCF  = "PDSIRRA-GCFUTSET"   # GCF
IRRA_TRI  = "PDSIRRA-TRIGUTSET"  # Triparty

# Repo (Securities Out) — Treasury (exc TIPS)
ORA_UB_G  = "PDSORA-UBGUTSET"
ORA_UB_S  = "PDSORA-UBSUTSET"
ORA_CB_G  = "PDSORA-CBGUTSET"
ORA_CB_S  = "PDSORA-CBSUTSET"
ORA_GCF   = "PDSORA-GCFUTSET"
ORA_TRI   = "PDSORA-TRIGUTSET"

TARGET = {
    IRRA_UB_G, IRRA_UB_S, IRRA_CB_G, IRRA_CB_S, IRRA_GCF, IRRA_TRI,
    ORA_UB_G,  ORA_UB_S,  ORA_CB_G,  ORA_CB_S,  ORA_GCF,  ORA_TRI
}

GROUPS = {
    # Reverse Repo groups
    "Reverse Repo — Uncleared Bilateral": {IRRA_UB_G, IRRA_UB_S},
    "Reverse Repo — Cleared Bilateral"  : {IRRA_CB_G, IRRA_CB_S},
    "Reverse Repo — Treasury (GCF+Triparty)" : {IRRA_GCF, IRRA_TRI},
    # Repo groups
    "Repo — Uncleared Bilateral": {ORA_UB_G, ORA_UB_S},
    "Repo — Cleared Bilateral"  : {ORA_CB_G, ORA_CB_S},
    "Repo — Treasury (GCF+Triparty)" : {ORA_GCF, ORA_TRI},
}

def filter_target(df):
    return df[df["series"].isin(TARGET)].copy()

def latest_date(df):
    return df["date"].max()

def nearest_on_or_before(df, when):
    d = df[df["date"] <= when]
    return None if d.empty else d["date"].max()

def rr_repo_split(df, day):
    """Two rows (Repo, Reverse Repo) with billions for a given day."""
    snap = df[df["date"] == day]
    if snap.empty:
        return pd.DataFrame({"Type": [], "Value (bn)": []})
    rr_mask = snap["series"].str.startswith("PDSIRRA")
    repo_mask = snap["series"].str.startswith("PDSORA")
    return pd.DataFrame({
        "Type": ["Reverse Repo", "Repo"],
        "Value (bn)": [snap[rr_mask]["value_mn"].sum()/1000.0,
                       snap[repo_mask]["value_mn"].sum()/1000.0]
    })

def grouped_breakdown(df, day, side="repo"):
    """Aggregate as requested (UB = Gen+Spec, CB = Gen+Spec, Treasury = GCF+Triparty)."""
    snap = df[df["date"] == day]
    rows = []
    for gname, sids in GROUPS.items():
        if side == "repo" and not gname.startswith("Repo"):
            continue
        if side == "rr" and not gname.startswith("Reverse"):
            continue
        val = snap[snap["series"].isin(sids)]["value_mn"].sum() / 1000.0
        rows.append({"Category": gname.split(" — ")[1], "Value (bn)": val})
    return pd.DataFrame(rows).sort_values("Value (bn)", ascending=False)

def side_total_M(df, day, prefix):
    return df[(df["date"] == day) & (df["series"].str.startswith(prefix))]["value_mn"].sum()

def get_baseline(df, latest_day, choice):
    if choice.startswith("YoY"):
        return nearest_on_or_before(df, latest_day - timedelta(days=365)), "per selected YoY"
    else:
        return nearest_on_or_before(df, pd.Timestamp("2025-01-01")), "per 01.01.2025 baseline"

def annual_delta_rr_repo(df, latest_day, baseline_day):
    """Return 2-row DF: deltas (Latest − Baseline) for Repo and Reverse Repo (billions)."""
    if baseline_day is None:
        return pd.DataFrame({"Type": [], "Δ (bn)": []})
    latest = rr_repo_split(df, latest_day).set_index("Type")["Value (bn)"]
    base   = rr_repo_split(df, baseline_day).set_index("Type")["Value (bn)"]
    for t in ["Repo", "Reverse Repo"]:
        if t not in latest: latest.loc[t] = 0.0
        if t not in base:   base.loc[t] = 0.0
    delta = (latest - base)
    return pd.DataFrame({"Type": delta.index, "Δ (bn)": delta.values})

# ----------------------------- Charts ---------------------------------
def chart_latest_two(df_two, title):
    color = alt.Scale(domain=["Reverse Repo","Repo"], range=[COLOR_RR, COLOR_REPO])

    base = alt.Chart(df_two).encode(
        x=alt.X("Type:N", sort=["Repo", "Reverse Repo"], title=None),
        y=alt.Y("Value (bn):Q", title="Billions of dollars")
    )

    bars = base.mark_bar().encode(
        color=alt.Color("Type:N", scale=color, legend=None),
        tooltip=["Type","Value (bn)"]
    )

    labels = base.mark_text(dy=-6, fontWeight="bold").encode(
        text=alt.Text("Value (bn):Q", format=",.1f")
    )

    return (bars + labels).properties(
        title=alt.TitleParams(text=title, anchor="start", dy=12),
        height=280,
        padding={"top": 28, "right": 8, "left": 8, "bottom": 8},
    ).configure_title(fontSize=16, fontWeight="bold")


def chart_annual_delta(df_delta, title):
    color = alt.Scale(domain=["Reverse Repo","Repo"], range=[COLOR_RR, COLOR_REPO])

    base = alt.Chart(df_delta).encode(
        x=alt.X("Type:N", sort=["Repo", "Reverse Repo"], title=None),
        y=alt.Y("Δ (bn):Q", title="Change (Billions of dollars)")
    )

    bars = base.mark_bar().encode(
        color=alt.Color("Type:N", scale=color, legend=None),
        tooltip=["Type","Δ (bn)"]
    )

    labels = base.mark_text(dy=-6, fontWeight="bold").encode(
        text=alt.Text("Δ (bn):Q", format=",.1f")
    )

    return (bars + labels).properties(
        title=alt.TitleParams(text=title, anchor="start", dy=12),
        height=280,
        padding={"top": 28, "right": 8, "left": 8, "bottom": 8},
    ).configure_title(fontSize=16, fontWeight="bold")


def chart_grouped(df_grouped, title):
    # base: yatay bar + eksen formatı
    base = (
        alt.Chart(df_grouped)
        .encode(
            x=alt.X(
                "Value (bn):Q",
                title="Billions of dollars",
                axis=alt.Axis(format=",.1f")   # <-- 1 ondalık, binlik ayırıcı
            ),
            y=alt.Y("Category:N", sort="-x", title=None),
            tooltip=[
                alt.Tooltip("Category:N"),
                alt.Tooltip("Value (bn):Q", format=",.1f")  # <-- tooltip da 1 ondalık
            ],
        )
    )

    bars = base.mark_bar()

    # bar sonuna metin etiketi (715.6 gibi)
    labels = (
        base.mark_text(dx=6, align="left", baseline="middle", fontWeight="bold")
        .encode(text=alt.Text("Value (bn):Q", format=",.1f"))  # <-- 1 ondalık
    )

    return (bars + labels).properties(
        title=alt.TitleParams(text=title, anchor="start", dy=12),
        height=320,
        padding={"top": 28, "right": 8, "left": 8, "bottom": 8},
    ).configure_title(fontSize=16, fontWeight="bold")


# ------------------------------- Data ---------------------------------
raw = fetch_data()
sub = filter_target(raw)
sub["date"] = pd.to_datetime(sub["date"], errors="coerce")
sub = sub.dropna(subset=["date"]).sort_values("date")
LATEST = sub["date"].max()

# ------------------------------- Top row ------------------------------
# ---- manual refresh to bust cache ----
ref1, ref2 = st.columns([1, 6])
with ref1:
    if st.button("↻ Refresh data", use_container_width=True):
        st.cache_data.clear()
        st.rerun()

left_top, right_top = st.columns([1.2, 2])

with left_top:
    with st.container(border=True):
        st.caption("Latest Data")
        st.markdown(f"<h5 style='margin:0'>{LATEST.strftime('%b %d, %Y')}</h2>", unsafe_allow_html=True)

with right_top:
    with st.container(border=True):
        baseline_choice = st.radio(
            "Annual baseline",
            ["YoY (t - 1 year)", "01.01.2025"],
            index=0,
            horizontal=True
        )

st.divider()

# ------------------------------ Row 2 ---------------------------------
col2_l, col2_r = st.columns(2)

with col2_l:
    with st.container(border=True):
        st.altair_chart(
            chart_latest_two(rr_repo_split(sub, LATEST), "Latest Day: Reverse Repo vs Repo (bn)"),
            use_container_width=True
        )

with col2_r:
    baseline_day, baseline_label = get_baseline(sub, LATEST, baseline_choice)
    with st.container(border=True):
        if baseline_day is None:
            st.info("No valid baseline date found.")
        else:
            ddf = annual_delta_rr_repo(sub, LATEST, baseline_day)
            st.altair_chart(
                chart_annual_delta(ddf, f"Annual Δ — Repo & Reverse Repo ({baseline_label})"),
                use_container_width=True
            )

st.divider()

# ------------------------------ Row 3 ---------------------------------
col3_l, col3_r = st.columns(2)

with col3_l:
    with st.container(border=True):
        st.altair_chart(
            chart_grouped(grouped_breakdown(sub, LATEST, side="repo"),
                          "Latest Day — Repo breakdown (UB, CB, Treasury)"),
            use_container_width=True
        )

with col3_r:
    with st.container(border=True):
        st.altair_chart(
            chart_grouped(grouped_breakdown(sub, LATEST, side="rr"),
                          "Latest Day — Reverse Repo breakdown (UB, CB, Treasury)"),
            use_container_width=True
        )

# ------------------------------ Row 4 ---------------------------------
col4_l, col4_r = st.columns(2)

with col4_l:
    with st.container(border=True):
        if baseline_day is None:
            st.info("No valid baseline date found.")
        else:
            st.altair_chart(
                chart_grouped(grouped_breakdown(sub, baseline_day, side="repo"),
                              f"Annual Repo breakdown ({baseline_label})"),
                use_container_width=True
            )

with col4_r:
    with st.container(border=True):
        if baseline_day is None:
            st.info("No valid baseline date found.")
        else:
            st.altair_chart(
                chart_grouped(grouped_breakdown(sub, baseline_day, side="rr"),
                              f"Annual Reverse Repo breakdown ({baseline_label})"),
                use_container_width=True
            )

st.divider()

# =========================== Net (Repo − RR) • Historical Δ ===========================
# Kullanıcı seçimi: baseline_choice ("YoY (t - 1 year)" veya "01.01.2025")
with st.container(border=True):
    st.subheader("Net (Repo − Reverse Repo) — Historical change vs baseline")

    # -- Günlük net seri (bn $): net = repo - reverse repo
    # sub: (date, series, value_mn)
    daily = (
        sub.assign(is_repo=sub["series"].str.startswith("PDSORA"),
                   is_rr=sub["series"].str.startswith("PDSIRRA"))
           .groupby("date", as_index=False)
           .agg(repo_M=("value_mn", lambda s: s[sub.loc[s.index, "is_repo"]].sum()),
                rr_M=("value_mn",   lambda s: s[sub.loc[s.index, "is_rr"]].sum()))
    )
    daily["net_bn"] = (daily["repo_M"] - daily["rr_M"]) / 1000.0
    daily = daily.sort_values("date").reset_index(drop=True)

    # --- Yardımcı: YoY için merge_asof ile t-365'e göre eşle
    def yoy_delta(df):
        base = df[["date", "net_bn"]].rename(columns={"date": "ref_date", "net_bn": "base_net"})
        # Her tarih için "anchor = date - 365 gün"; anchor'a en yakın önceki iş günü ref_date bulunur
        tmp = pd.merge_asof(
            df.assign(anchor=df["date"] - pd.Timedelta(days=365)).sort_values("anchor"),
            base.sort_values("ref_date"),
            left_on="anchor",
            right_on="ref_date",
            direction="backward"
        )
        tmp = tmp.dropna(subset=["base_net"]).copy()
        tmp["delta_bn"] = tmp["net_bn"] - tmp["base_net"]
        return tmp[["date", "delta_bn"]]

    # --- 01.01.2025 bazlı sabit referans: tüm tarihler için (net(t) - net(t0))
    def fixed_baseline_delta(df, baseline_ts=pd.Timestamp("2025-01-01")):
        # veri gününe göre en yakın/öncesi baseline günü
        base_day = nearest_on_or_before(sub, baseline_ts)
        if base_day is None:
            return pd.DataFrame(columns=["date", "delta_bn"])
        base_net = df.loc[df["date"] == base_day, "net_bn"]
        base_net = base_net.iloc[0] if not base_net.empty else 0.0
        out = df.copy()
        out["delta_bn"] = out["net_bn"] - base_net
        # referans gününden önceki günleri istersen kırpmak için:
        out = out[out["date"] >= base_day].copy()
        return out[["date", "delta_bn"]]

    if baseline_choice.startswith("YoY"):
        series = yoy_delta(daily)
        title  = "YoY Δ net (Repo − RR) — t vs t-1y"
    else:
        series = fixed_baseline_delta(daily, pd.Timestamp("2025-01-01"))
        title  = "Δ net (Repo − RR) — vs 01.01.2025 baseline"

    # Pozitif mavi, negatif kırmızı için imza kolonu
    series["Sign"] = np.where(series["delta_bn"] >= 0, "Positive", "Negative")

    # Altair çizimi
    color_scale = alt.Scale(domain=["Positive", "Negative"], range=[COLOR_REPO, COLOR_RR])

    base = alt.Chart(series).encode(
        x=alt.X("date:T", title=None),
        y=alt.Y("delta_bn:Q", title="Δ (Billions of dollars)", axis=alt.Axis(format=",.1f")),
        tooltip=[alt.Tooltip("date:T", title="Date"),
                 alt.Tooltip("delta_bn:Q", title="Δ (bn $)", format=",.1f")]
    )

    # Çizgi + nokta (nokta rengi işarete göre)
    line = base.mark_line(strokeWidth=2, opacity=0.9, interpolate="monotone").encode(
        color=alt.Color("Sign:N", scale=color_scale, legend=None)
    )
    points = base.mark_point(size=35, filled=True).encode(
        color=alt.Color("Sign:N", scale=color_scale, legend=None)
    )

    # Sıfır çizgisi
    zero = alt.Chart(pd.DataFrame({"y": [0]})).mark_rule(strokeDash=[4,4]).encode(y="y:Q")

    chart = (zero + line + points).properties(
        title=alt.TitleParams(text=title, anchor="start", dy=12),
        height=320,
        padding={"top": 28, "right": 8, "left": 8, "bottom": 8},
    ).configure_title(fontSize=16, fontWeight="bold")

    st.altair_chart(chart, use_container_width=True)



# ------------------------------ Methodology ---------------------------
with st.expander("Methodology"):
    st.markdown("""
**Source:** Federal Reserve Bank of New York — *Primary Dealer Statistics* (timeseries.csv).  
**Grouping logic (both Repo and Reverse Repo):**
- **Uncleared Bilateral** = *General* + *Specified*  
- **Cleared Bilateral** = *General* + *Specified*  
- **Treasury** = *GCF* + *Triparty*

**Baseline selection:**  
- **YoY (t - 1 year):** Uses the **nearest on/before** date that is approximately one year earlier than the latest date.  
- **01.01.2025:** Uses the **nearest on/before** 2025-01-01.  

**Units:**  
- Charts display **Billions of dollars (bn)**.  
- Net impact displays **Billions of dollars ($B)**.  

**Notes:** Minor calendar alignment differences are handled by “nearest on/before” logic to avoid gaps on non-trading days.
""")

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

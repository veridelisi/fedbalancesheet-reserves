# pages/01_Eurodollar.py
import requests, xml.etree.ElementTree as ET
import pandas as pd
import numpy as np
import streamlit as st
import plotly.graph_objects as go

st.set_page_config(page_title="Eurodollar Market Evolution — 2000-2025", layout="wide")

# --- Top nav ---
cols = st.columns(8)
with cols[0]: st.page_link("streamlit_app.py", label="🏠 Home")
with cols[1]: st.page_link("pages/01_Reserves.py", label="🌍 Reserves")
with cols[2]: st.page_link("pages/01_Repo.py", label="♻️ Repo")
with cols[3]: st.page_link("pages/01_TGA.py", label="🌐 TGA")
with cols[4]: st.page_link("pages/01_PublicBalance.py", label="💹 Public Balance")
with cols[5]: st.page_link("pages/01_Interest.py", label="✈️ Reference Rates")
with cols[6]: st.page_link("pages/01_Desk.py", label="📡 Desk")
with cols[7]: st.page_link("pages/01_Eurodollar.py", label="💡 Eurodollar")

# --- Hide sidebar + tab style ---
st.markdown("""
<style>
  [data-testid="stSidebarNav"]{display:none;}
  section[data-testid="stSidebar"][aria-expanded="true"]{display:none;}
  .stTabs [role="tablist"] { gap: 16px; border-bottom:1px solid #eee; }
  .stTabs [role="tab"]{ padding:8px 10px; font-weight:600; color:#6b7280; }
  .stTabs [role="tab"][aria-selected="true"]{
    color:#e74c3c; border-bottom:3px solid #e74c3c; background:transparent;
  }
</style>
""", unsafe_allow_html=True)

# ======================= BIS LOADER (generic XML) =======================
FLOW_PATH = "dataflow/BIS/WS_GLI/1.0"
HEADERS   = {"Accept": "application/vnd.sdmx.genericdata+xml;version=2.1"}

@st.cache_data(ttl=3600, show_spinner=False)
def bis_series_xml(key: str, start="2000", end="2025") -> pd.DataFrame:
    url = f"https://stats.bis.org/api/v2/data/{FLOW_PATH}/{key}/all?detail=full&startPeriod={start}&endPeriod={end}"
    r = requests.get(url, headers=HEADERS, timeout=60)
    r.raise_for_status()
    root = ET.fromstring(r.content)
    ns = {'g': 'http://www.sdmx.org/resources/sdmxml/schemas/v2_1/data/generic'}
    rows = []
    for series in root.findall('.//g:Series', ns):
        for obs in series.findall('.//g:Obs', ns):
            dim = obs.find('g:ObsDimension', ns)
            val = obs.find('g:ObsValue', ns)
            if val is None: continue
            rows.append({'period': (dim.get('value') if dim is not None else None),
                         'Val': val.get('value')})
    df = pd.DataFrame(rows)
    if df.empty: return df
    df["Val"] = pd.to_numeric(df["Val"], errors="coerce")
    # 'YYYY-Qn' -> çeyrek sonu
    per = pd.PeriodIndex(df["period"].astype(str).str.replace("-Q","Q"), freq="Q")
    df["Time"] = per.to_timestamp(how="end")
    return df.dropna(subset=["Time","Val"]).sort_values("Time")[["Time","Val"]].reset_index(drop=True)

# --- Seriler ---
SERIES = {
    "AllCredit":      "Q.USD.3P.N.A.I.B.USD",
    "DebtSecurities": "Q.USD.3P.N.A.I.D.USD",
    "Loans":          "Q.USD.3P.N.B.I.G.USD",

    # Emerging economy serileri (total)
    "EmeDebt":       "Q.USD.4T.N.A.I.D.USD",
    "EmeBankLoans":  "Q.USD.4T.N.B.I.G.USD",
}

st.sidebar.header("BIS WS_GLI")
start_year = st.sidebar.number_input("Start", 1980, 2025, 2000)
end_year   = st.sidebar.text_input("End", "2025")

# --- Pull & merge ana seriler ---
try:
    dfs = []
    for name, key in SERIES.items():
        s = bis_series_xml(key, start=str(start_year), end=(end_year or "2025")).rename(columns={"Val": name})
        dfs.append(s)
    df = dfs[0]
    for s in dfs[1:]: df = df.merge(s, on="Time", how="outer")

    df = df.sort_values("Time").reset_index(drop=True)
    df["Year"] = df["Time"].dt.year
    for c in SERIES.keys(): df[c] = pd.to_numeric(df[c], errors="coerce") / 1000.0  # M$ → B$
    # Advanced = Total − Emerging
    df["AdvancedDebtSecurities"] = df["DebtSecurities"] - df["EmeDebt"]
    df["AdvancedLoans"]          = df["Loans"]          - df["EmeBankLoans"]
except Exception as e:
    st.error(f"BIS verisi çekilemedi: {e}"); st.stop()

# --------------------- helpers ---------------------
def add_shading(fig):
    crisis = [(pd.to_datetime("2007-12-01"), pd.to_datetime("2009-06-01"), "Financial Crisis"),
              (pd.to_datetime("2020-02-01"), pd.to_datetime("2020-04-01"), "COVID-19")]
    for x0,x1,lab in crisis:
        fig.add_vrect(x0=x0,x1=x1,fillcolor="red",opacity=.10,line_width=0,
                      annotation_text=lab,annotation_position="top left")
    fig.add_vrect(x0=pd.to_datetime("2022-06-01"),
                  x1=pd.to_datetime(df["Time"].max()),
                  fillcolor="orange",opacity=.08,line_width=0,
                  annotation_text="Fed Tightening",annotation_position="top left")

def yaxis_k(fig, tickvals=None, decimals=0):
    # 1,250B stili: binlik ayraç + B son ek
    if tickvals is not None:
        fig.update_yaxes(tickvals=tickvals)
    fig.update_yaxes(
        tickformat=f",.{decimals}f",   # ",.0f" → 1,250   ",.1f" → 1,250.5
        ticksuffix="B",
        separatethousands=True,
        showexponent="none"
    )

def title_range(prefix):
    return f"<b>{prefix} ({df['Time'].min().year}–{df['Time'].max().year})</b>"

# --------------------- reusable panels ---------------------
def two_series_panels(left_name, left_series, right_name, right_series,
                      title_top, title_yoy,
                      color_left="#8e44ad", color_right="#f39c12"):
    d = df[["Time", left_series, right_series]].sort_values("Time").copy()

    # --- Seviye (üst) ---
    fig = go.Figure()
    fig.add_trace(go.Scatter(x=d["Time"], y=d[left_series], mode="lines",
                             name=left_name, line=dict(width=3, color=color_left)))
    fig.add_trace(go.Scatter(x=d["Time"], y=d[right_series], mode="lines",
                             name=right_name, line=dict(width=3, color=color_right)))
    add_shading(fig); yaxis_k(fig)
    fig.update_layout(title=dict(text=title_range(title_top), x=0.5),
                      height=560, legend=dict(orientation="h"))
    st.plotly_chart(fig, use_container_width=True)

    # --- YoY (alt) ---
    lag = 4  # çeyrek
    d[f"{left_series}_YoY"]  = d[left_series].pct_change(lag)*100
    d[f"{right_series}_YoY"] = d[right_series].pct_change(lag)*100
    d2 = d.dropna(subset=[f"{left_series}_YoY", f"{right_series}_YoY"])

    fig2 = go.Figure()
    fig2.add_trace(go.Bar(x=d2["Time"], y=d2[f"{left_series}_YoY"], name=f"{left_name} YoY",
                          marker_color=color_left, hovertemplate="%{y:.1f}%<extra></extra>"))
    fig2.add_trace(go.Bar(x=d2["Time"], y=d2[f"{right_series}_YoY"], name=f"{right_name} YoY",
                          marker_color=color_right, hovertemplate="%{y:.1f}%<extra></extra>"))
    fig2.add_hline(y=0, line_dash="dash", line_color="black")
    add_shading(fig2)
    fig2.update_yaxes(title="YoY (%)", ticksuffix="%", tickformat=".1f")
    fig2.update_layout(title=dict(text=title_range(title_yoy), x=0.5),
                       barmode="group", height=420,
                       legend=dict(orientation="h", yanchor="top", y=-0.25, xanchor="center", x=0.5))
    st.plotly_chart(fig2, use_container_width=True)

@st.cache_data(ttl=3600, show_spinner=False)
def load_series_billion(key: str) -> pd.DataFrame:
    """Tek seriyi (M$) çek, B$'a çevir."""
    s = bis_series_xml(key, start=str(start_year), end=(end_year or "2025"))
    if s.empty: return s
    s["Val"] = pd.to_numeric(s["Val"], errors="coerce") / 1000.0
    return s.dropna()

def one_series_panels(label: str, key: str, color="#e74c3c"):
    """Emerging Area / Country için tek seri paneli (seviye + YoY)."""
    s = load_series_billion(key)
    if s.empty:
        st.info(f"{label}: veri bulunamadı.")
        return

    # Üst: seviye
    fig = go.Figure()
    fig.add_trace(go.Scatter(x=s["Time"], y=s["Val"], mode="lines",
                             name=label, line=dict(width=3, color=color)))
    add_shading(fig); yaxis_k(fig)
    fig.update_traces(hovertemplate="$%{y:,.0f}B<extra></extra>")
    fig.update_layout(title=dict(text=title_range(f"{label} — Total Credit (USD bn)"), x=0.5),
                      height=560, legend=dict(orientation="h"))
    st.plotly_chart(fig, use_container_width=True)

    # Alt: YoY (%)
    s2 = s.copy()
    s2["YoY"] = s2["Val"].pct_change(4)*100
    fig2 = go.Figure()
    fig2.add_trace(go.Bar(x=s2["Time"], y=s2["YoY"], marker_color=color))
    fig2.add_hline(y=0, line_dash="dash", line_color="black")
    add_shading(fig2)
    fig2.update_yaxes(title="YoY (%)", tickformat=".1f", ticksuffix="%")
    fig2.update_layout(title=dict(text=title_range(f"{label} — YoY"), x=0.5),
                       height=420, showlegend=False)
    st.plotly_chart(fig2, use_container_width=True)

# --------------------- charts (senin düzen) ---------------------
def total_credit():
    fig = go.Figure()
    fig.add_trace(go.Scatter(x=df["Time"], y=df["AllCredit"], mode="lines",
                             line=dict(width=3, color="#e74c3c")))
    add_shading(fig)
    fig.update_layout(title=dict(text=title_range("Total Eurodollar Credit (USD bn)"), x=0.5),
                      height=520)
    yaxis_k(fig); st.plotly_chart(fig, use_container_width=True)

    yoy = df.copy(); yoy["YoY"] = yoy["AllCredit"].pct_change(4)*100
    fig2 = go.Figure()
    fig2.add_trace(go.Bar(x=yoy["Time"], y=yoy["YoY"],
                          marker_color=np.where(yoy["YoY"]>=0,"#27ae60","#e74c3c")))
    fig2.add_hline(y=0, line_dash="dash", line_color="black")
    fig2.update_layout(title=dict(text=title_range("Total Credit — YoY"), x=0.5),
                       height=420)
    st.plotly_chart(fig2, use_container_width=True)

def debt_securities():
    fig = go.Figure()
    fig.add_trace(go.Scatter(x=df["Time"], y=df["DebtSecurities"], mode="lines",
                             line=dict(width=3, color="#8e44ad")))
    add_shading(fig); yaxis_k(fig)
    fig.update_layout(title=dict(text=title_range("Debt Securities (USD bn)"), x=0.5),
                      height=520)
    st.plotly_chart(fig, use_container_width=True)

    yoy = df.copy(); yoy["YoY"] = yoy["DebtSecurities"].pct_change(4)*100
    fig2 = go.Figure()
    fig2.add_trace(go.Bar(x=yoy["Time"], y=yoy["YoY"],
                          marker_color=np.where(yoy["YoY"]>=0,"#27ae60","#e74c3c")))
    fig2.add_hline(y=0, line_dash="dash", line_color="black")
    fig2.update_layout(title=dict(text=title_range("Debt Securities — YoY"), x=0.5),
                       height=420)
    st.plotly_chart(fig2, use_container_width=True)

def loans():
    fig = go.Figure()
    fig.add_trace(go.Scatter(x=df["Time"], y=df["Loans"], mode="lines",
                             line=dict(width=3, color="#f39c12")))
    add_shading(fig); yaxis_k(fig)
    fig.update_layout(title=dict(text=title_range("Loans (USD bn)"), x=0.5),
                      height=520)
    st.plotly_chart(fig, use_container_width=True)

    yoy = df.copy(); yoy["YoY"] = yoy["Loans"].pct_change(4)*100
    fig2 = go.Figure()
    fig2.add_trace(go.Bar(x=yoy["Time"], y=yoy["YoY"],
                          marker_color=np.where(yoy["YoY"]>=0,"#27ae60","#e74c3c")))
    fig2.add_hline(y=0, line_dash="dash", line_color="black")
    fig2.update_layout(title=dict(text=title_range("Loans — YoY"), x=0.5),
                       height=420)
    st.plotly_chart(fig2, use_container_width=True)

def comparison():
    fig = go.Figure()
    fig.add_trace(go.Scatter(x=df["Time"], y=df["AllCredit"], mode="lines",
                             name="Total", line=dict(width=3, color="#e74c3c")))
    fig.add_trace(go.Scatter(x=df["Time"], y=df["DebtSecurities"], mode="lines",
                             name="Debt", line=dict(width=3, color="#8e44ad")))
    fig.add_trace(go.Scatter(x=df["Time"], y=df["Loans"], mode="lines",
                             name="Loans", line=dict(width=3, color="#f39c12")))
    add_shading(fig); yaxis_k(fig)
    fig.update_layout(title=dict(text=title_range("Comparison (USD bn)"), x=0.5),
                      height=620, legend=dict(orientation="h"))
    st.plotly_chart(fig, use_container_width=True)

    d = df.sort_values("Time").copy()
    d["TotalYoY"] = d["AllCredit"].pct_change(4)*100
    d["DebtYoY"]  = d["DebtSecurities"].pct_change(4)*100
    d["LoansYoY"] = d["Loans"].pct_change(4)*100
    yoy_plot = d.dropna(subset=["TotalYoY","DebtYoY","LoansYoY"])
    fig2 = go.Figure()
    fig2.add_trace(go.Bar(x=yoy_plot["Time"], y=yoy_plot["TotalYoY"], name="Total YoY",
                          marker_color="#e74c3c", hovertemplate="%{y:.1f}%<extra>Total</extra>"))
    fig2.add_trace(go.Bar(x=yoy_plot["Time"], y=yoy_plot["DebtYoY"], name="Debt YoY",
                          marker_color="#8e44ad", hovertemplate="%{y:.1f}%<extra>Debt</extra>"))
    fig2.add_trace(go.Bar(x=yoy_plot["Time"], y=yoy_plot["LoansYoY"], name="Loans YoY",
                          marker_color="#f39c12", hovertemplate="%{y:.1f}%<extra>Loans</extra>"))
    fig2.add_hline(y=0, line_dash="dash", line_color="black")
    add_shading(fig2)
    fig2.update_yaxes(title="YoY (%)", ticksuffix="%", tickformat=".1f")
    fig2.update_layout(title=dict(text=title_range("YoY Growth — Total vs Debt vs Loans"), x=0.5),
                       barmode="group", height=420,
                       legend=dict(orientation="h", yanchor="top", y=-0.25, xanchor="center", x=0.5))
    st.plotly_chart(fig2, use_container_width=True)

# =========================== LAYOUT: TABS ===========================
st.title("Eurodollar Market Evolution — 2000-2025")
tabs = st.tabs([
    "Total Credit", "Debt Securities", "Loans", "Comparison",
    "Advanced vs Emerging", "Emerging Area", "Emerging Countries"
])
t1, t2, t3, t4, tAE, tEA, tEC = tabs

with t1: total_credit()
with t2: debt_securities()
with t3: loans()
with t4: comparison()

# --- Advanced vs Emerging (ALT SEKME) ---
with tAE:
    sub1, sub2, sub3, sub4 = st.tabs([
        "Advanced Debt vs Loans",
        "Emerging Debt vs Loans",
        "Debt Comparison",
        "Loans Comparison"
    ])

    with sub1:
        two_series_panels(
            "Advanced Debt", "AdvancedDebtSecurities",
            "Advanced Loans", "AdvancedLoans",
            "Advanced Economies — Debt vs Loans (USD bn)",
            "Advanced — YoY (Debt vs Loans)",
            color_left="#8e44ad", color_right="#f39c12"
        )

    with sub2:
        two_series_panels(
            "Emerging Debt", "EmeDebt",
            "Emerging Bank Loans", "EmeBankLoans",
            "Emerging Economies — Debt vs Bank Loans (USD bn)",
            "Emerging — YoY (Debt vs Loans)",
            color_left="#8e44ad", color_right="#27ae60"
        )

    with sub3:
        two_series_panels(
            "Advanced Debt", "AdvancedDebtSecurities",
            "Emerging Debt", "EmeDebt",
            "Debt Securities — Advanced vs Emerging (USD bn)",
            "Debt — YoY (Adv vs Eme)",
            color_left="#8e44ad", color_right="#27ae60"
        )

    with sub4:
        two_series_panels(
            "Advanced Loans", "AdvancedLoans",
            "Emerging Bank Loans", "EmeBankLoans",
            "Loans — Advanced vs Emerging (USD bn)",
            "Loans — YoY (Adv vs Eme)",
            color_left="#f39c12", color_right="#27ae60"
        )

# --- Emerging Area (ALT SEKME) ---
with tEA:
    area_tabs = st.tabs(["Africa & Middle East", "Emerging Asia", "Emerging Europe", "Latin America", "Comparison"])


    with area_tabs[0]:
        one_series_panels("Africa & Middle East", "Q.USD.4W.N.A.I.B.USD", color="#e74c3c")
    with area_tabs[1]:
        one_series_panels("Emerging Asia", "Q.USD.4Y.N.A.I.B.USD", color="#27ae60")
    with area_tabs[2]:
        one_series_panels("Emerging Europe", "Q.USD.3C.N.A.I.B.USD", color="#8e44ad")
    with area_tabs[3]:
        one_series_panels("Latin America", "Q.USD.4U.N.A.I.B.USD", color="#f39c12")
     # --- Comparison: Regional Shares + Time Evolution ---
    with area_tabs[4]:
        st.markdown("### 🌍 Emerging Areas — Regional Shares & Evolution")

        AREA_KEYS = {
            "Africa & Middle East": "Q.USD.4W.N.A.I.B.USD",
            "Emerging Asia":        "Q.USD.4Y.N.A.I.B.USD",
            "Emerging Europe":      "Q.USD.3C.N.A.I.B.USD",
            "Latin America":        "Q.USD.4U.N.A.I.B.USD"
        }
        COLORS = ["#e74c3c", "#27ae60", "#8e44ad", "#f39c12"]

        # 1️⃣ Serileri çek ve birleştir
        merged = None
        for name, key in AREA_KEYS.items():
            s = load_series_billion(key).rename(columns={"Val": name})
            merged = s if merged is None else merged.merge(s, on="Time", how="outer")
        if merged is None or merged.empty:
            st.warning("No area data found.")
            st.stop()

        merged = merged.sort_values("Time").reset_index(drop=True)
        merged["Year"] = merged["Time"].dt.year

        # 2️⃣ Yıl seçimi
        years_avail = sorted(merged["Year"].dropna().unique().tolist())
        mode = st.radio("Select period", ["Latest", "Select year"], horizontal=True)
        if mode == "Select year":
            year_sel = st.selectbox("Year", years_avail, index=len(years_avail)-1)
            snap = merged[merged["Year"] == year_sel].iloc[-1]
            title_suffix = f"{year_sel}"
        else:
            snap = merged.iloc[-1]
            title_suffix = f"{snap['Time'].date()}"

        # 3️⃣ Pie veri
        parts = []
        for name in AREA_KEYS.keys():
            val = pd.to_numeric(snap.get(name), errors="coerce")
            if pd.notna(val):
                parts.append((name, float(val)))

        if not parts:
            st.warning("No values for the selected period.")
        else:
            df_pie = pd.DataFrame(parts, columns=["Region", "Value"]).sort_values("Region")

            # PIE
            fig_pie = go.Figure(go.Pie(
                labels=df_pie["Region"],
                values=df_pie["Value"],
                hole=0.45,
                textinfo="label+percent",
                hovertemplate="%{label}: $%{value:,.0f}B<extra></extra>",
                marker=dict(colors=COLORS)
            ))
            fig_pie.update_layout(
                title=dict(text=title_range(f"Shares in Emerging Total"), x=0.5),
                height=480,
                legend=dict(orientation="h", yanchor="top", y=-0.15, xanchor="center", x=0.5)
            )
            st.plotly_chart(fig_pie, use_container_width=True)



            # 4️⃣ ZAMAN SERİSİ — 4 bölgenin gelişimi
            fig_line = go.Figure()
            for i, name in enumerate(AREA_KEYS.keys()):
                if name in merged.columns:
                    fig_line.add_trace(go.Scatter(
                        x=merged["Time"],
                        y=merged[name],
                        mode="lines",
                        name=name,
                        line=dict(width=3, color=COLORS[i]),
                        hovertemplate="$%{y:,.0f}B<extra>"+name+"</extra>"
                    ))

            add_shading(fig_line)
            yaxis_k(fig_line)
            fig_line.update_layout(
                title=dict(text=title_range("Emerging Areas — Time Evolution (USD bn)"), x=0.5),
                height=520,
                legend=dict(orientation="h", yanchor="top", y=-0.25, xanchor="center", x=0.5)
            )
            st.plotly_chart(fig_line, use_container_width=True)


# --- Emerging Countries (ALT SEKME) ---
with tEC:
    COUNTRY_KEYS = {
        "SaudiArabia": "Q.USD.SA.N.A.I.B.USD",
        "SouthAfrica": "Q.USD.ZA.N.A.I.B.USD",
        "China":       "Q.USD.CN.N.A.I.B.USD",
        "Taipei":      "Q.USD.TW.N.A.I.B.USD",
        "India":       "Q.USD.IN.N.A.I.B.USD",
        "Indonesia":   "Q.USD.ID.N.A.I.B.USD",
        "Korea":       "Q.USD.KR.N.A.I.B.USD",
        "Malaysia":    "Q.USD.MY.N.A.I.B.USD",
        "Russia":      "Q.USD.RU.N.A.I.B.USD",
        "Turkey":      "Q.USD.TR.N.A.I.B.USD",
        "Argentina":   "Q.USD.AR.N.A.I.B.USD",
        "Brazil":      "Q.USD.BR.N.A.I.B.USD",
        "Chile":       "Q.USD.CL.N.A.I.B.USD",
        "Mexico":      "Q.USD.MX.N.A.I.B.USD",
    }

# ---------- (1) TOP-10 PIE: paylar (seçim gerektirmez) ----------
    # Tüm ülke serilerini çek; aynı tarihe (snap_date) hizala ve son değeri al
    series_cache = {}
    last_dates = []
    for cname, ckey in COUNTRY_KEYS.items():
        s = load_series_billion(ckey)
        if s.empty: 
            continue
        series_cache[cname] = s.sort_values("Time")
        last_dates.append(series_cache[cname]["Time"].iloc[-1])

    # Emerging toplam (AllCredit, emerging economies)
    EME_TOTAL_KEY = "Q.USD.4T.N.A.I.B.USD"
    eme_total = load_series_billion(EME_TOTAL_KEY).sort_values("Time")
    if not eme_total.empty:
        last_dates.append(eme_total["Time"].iloc[-1])

    if last_dates:
        snap_date = min(last_dates)  # hepsi için ortak alınabilecek en son tarih
        latest_rows = []
        for cname, s in series_cache.items():
            s_cut = s[s["Time"] <= snap_date]
            if not s_cut.empty:
                latest_rows.append((cname, float(s_cut["Val"].iloc[-1])))
        df_latest = pd.DataFrame(latest_rows, columns=["Country","Value"]).sort_values("Value", ascending=False)

        # Emerging toplamı aynı tarihte al
        eme_cut = eme_total[eme_total["Time"] <= snap_date]
        eme_total_val = float(eme_cut["Val"].iloc[-1]) if not eme_cut.empty else df_latest["Value"].sum()

        # ========= TOP-14 + OTHERS (fixed shares vs Emerging total) =========
        N_TOP = 14
        df_top = df_latest.head(N_TOP).copy()
        others_val = max(eme_total_val - df_top["Value"].sum(), 0.0)
        if others_val > 0:
            df_top = pd.concat(
                [df_top, pd.DataFrame([["Others", others_val]], columns=["Country","Value"])],
                ignore_index=True
            )

        # Sabit yüzdeler (her zaman Emerging toplamına göre)
        total_ref = max(eme_total_val, 1e-9)
        df_top["ShareTotal"] = df_top["Value"] / total_ref
        df_top["Text"] = df_top["Country"] + "\n" + (df_top["ShareTotal"]*100).round(1).astype(str) + "%"

        # Renk paleti (yeterince uzun)
        base_colors = [
            "#e74c3c","#8e44ad","#f39c12","#27ae60","#d35400",
            "#c0392b","#9b59b6","#16a085","#7f8c8d","#1abc9c",
            "#2ecc71","#d35400","#7f8c8d","#9b59b6","#bdc3c7"  # son: Others gri
        ]
        colors = base_colors[:len(df_top)]

        fig_pie = go.Figure(go.Pie(
            labels=df_top["Country"],
            values=df_top["Value"],
            hole=0.45,
            sort=False,
            text=df_top["Text"],           # Ülke + % (sabit)
            textinfo="text",
            textposition="inside",
            insidetextorientation="radial",
            customdata=(df_top["ShareTotal"]*100),
            hovertemplate="%{label}: $%{value:,.0f}B"
                          "<br>Share of Emerging Total: %{customdata:.1f}%<extra></extra>",
            marker=dict(colors=colors)
        ))
        fig_pie.update_layout(
            title=dict(
                text=title_range(
                    f"Top {N_TOP} Emerging Countries — Share in Emerging Total (as of {snap_date.date()})"
                ),
                x=0.5
            ),
            height=520,
            legend=dict(
                orientation="h", yanchor="top", y=-0.15, xanchor="center", x=0.5,
                itemclick="toggle", itemdoubleclick="toggleothers"
            )
        )
        st.plotly_chart(fig_pie, use_container_width=True)




    st.markdown("### Select countries")
    default_countries = ["Mexico","China","Turkey"]
    sel = st.multiselect("", list(COUNTRY_KEYS.keys()), default=default_countries)
    
    




    if not sel:
        st.info("Ülke seçiniz.")
    else:
        # Birleştir
        dfc = None
        for i, c in enumerate(sel):
            s = load_series_billion(COUNTRY_KEYS[c]).rename(columns={"Val": c})
            dfc = s if dfc is None else dfc.merge(s, on="Time", how="outer")
        dfc = dfc.sort_values("Time").reset_index(drop=True)

        # Üst: seviye (çoklu çizgi)
        palette = ["#e74c3c","#8e44ad","#f39c12","#27ae60","#2980b9","#d35400",
                   "#2c3e50","#9b59b6","#16a085","#c0392b","#7f8c8d","#1abc9c",
                   "#34495e","#f1c40f"]
        fig = go.Figure()
        for i, c in enumerate(sel):
            fig.add_trace(go.Scatter(x=dfc["Time"], y=dfc[c], mode="lines",
                                     name=c, line=dict(width=3, color=palette[i % len(palette)]),
                                     hovertemplate="$%{y:,.0f}B<extra>"+c+"</extra>"))
        add_shading(fig); yaxis_k(fig)
        fig.update_layout(title=dict(text=title_range("Emerging Countries — Total Credit (USD bn)"), x=0.5),
                          height=560, legend=dict(orientation="h"))
        st.plotly_chart(fig, use_container_width=True)

        # Alt: YoY (çoklu BAR, %)
        fig2 = go.Figure()
        for i, c in enumerate(sel):
            yo = dfc[["Time", c]].copy()
            yo[c] = pd.to_numeric(yo[c], errors="coerce")
            yo["YoY"] = yo[c].pct_change(4)*100

            fig2.add_trace(go.Bar(
                x=yo["Time"], y=yo["YoY"], name=c,
                marker_color=palette[i % len(palette)],
                hovertemplate="%{y:.1f}%<extra>"+c+"</extra>"
            ))

        fig2.add_hline(y=0, line_dash="dash", line_color="black")
        add_shading(fig2)
        fig2.update_yaxes(title="YoY (%)", tickformat=".1f", ticksuffix="%")
        fig2.update_layout(
            title=dict(text=title_range("Emerging Countries — YoY"), x=0.5),
            barmode="group",   # yan yana barlar
            height=420,
            legend=dict(orientation="h", yanchor="top", y=-0.25, xanchor="center", x=0.5)
        )
        st.plotly_chart(fig2, use_container_width=True)

# -*- coding: utf-8 -*-
# Country decomposition — Debt (IDS), Cross-border (LBS), Local FX (LBS)

import requests, xml.etree.ElementTree as ET
import pandas as pd, numpy as np
import streamlit as st
import plotly.graph_objects as go



# ---------------------- Genel stil ----------------------
st.markdown("""
<style>
  [data-testid="stSidebarNav"]{display:none;}
  section[data-testid="stSidebar"][aria-expanded="true"]{display:none;}
  .metric-small .stMetric-value { font-size: 1.35rem; }
</style>
""", unsafe_allow_html=True)

# ---------------------- Yardımcılar ----------------------
HEADERS = {"Accept": "application/vnd.sdmx.genericdata+xml;version=2.1"}

def _sdmx_generic_to_df(content: bytes) -> pd.DataFrame:
    root = ET.fromstring(content)
    ns = {'g': 'http://www.sdmx.org/resources/sdmxml/schemas/v2_1/data/generic'}
    rows = []
    for series in root.findall('.//g:Series', ns):
        for obs in series.findall('.//g:Obs', ns):
            dim = obs.find('g:ObsDimension', ns)
            val = obs.find('g:ObsValue', ns)
            if val is None: 
                continue
            rows.append({'period': (dim.get('value') if dim is not None else None),
                         'Val': val.get('value')})
    df = pd.DataFrame(rows)
    if df.empty:
        return df
    df["Val"] = pd.to_numeric(df["Val"], errors="coerce")
    per = pd.PeriodIndex(df["period"].astype(str).str.replace("-Q","Q"), freq="Q")
    df["Time"] = per.to_timestamp(how="end")
    return df.dropna(subset=["Time","Val"]).sort_values("Time")[["Time","Val"]].reset_index(drop=True)

def _bis_series(flow: str, key: str, start="2000", end="2025") -> pd.DataFrame:
    """
    flow:  ör. 'BIS/WS_DEBT_SEC2_PUB/1.0' veya 'BIS/WS_LBS_D_PUB/1.0'
    key:   SDMX key (örnekler aşağıda fonksiyonlarda)
    """
    url = f"https://stats.bis.org/api/v2/data/{flow}/{key}/all?detail=full&startPeriod={start}&endPeriod={end}"
    r = requests.get(url, headers=HEADERS, timeout=60)
    r.raise_for_status()
    return _sdmx_generic_to_df(r.content)

# ---------------------- Anahtar oluşturucular ----------------------
def _ids_key(iso: str) -> str:
    """
    IDS (debt securities, amounts outstanding), USD.
    Örnek (sizin ekran görüntüsüyle uyumlu): Q.MX.3P.1.1.C.A.F.USD.A.A.A.A.A.A.A.I
    Parçalar:  geo | freq(Q) | residents (3P=Residents) | issuer sector vb…
    """
    return f"Q.{iso}.3P.1.1.C.A.F.USD.A.A.A.A.A.A.A.I"

def _lbs_cross_key(iso: str) -> str:
    """
    LBS - Cross-border total claims, all reporting countries → residents of {iso}, USD.
    Örnek: Q.S.C.G.USD.A.5J.A.5A.A.{iso}.N
      S=All reporting ctrys, C=Claims, G=Cross-border,
      USD, A=all maturity, 5J=all sectors (counterparty), 5A=all instruments,
      A=all positions?, {iso}=counterparty country, N=stock
    """
    return f"Q.S.C.G.USD.A.5J.A.5A.A.{iso}.N"

def _lbs_local_fx_key(iso: str) -> str:
    """
    LBS - Local claims in foreign currency (banks in reporting country {iso}), USD.
    Örnek (screen shot): Q.S.C.A.USD.F.5J.A.{iso}.A.5J.N
      C=A? (claims), A=Local claims, USD, F=foreign currency,
      5J=all sectors, A=all instruments, {iso}=reporting country,
      A=all counterparty, 5J=all ???, N=stock
    Pratikte farklı varyantlar olabilir; BIS portalındaki 'Observations' → 'SDMX key' ile kontrol edin.
    """
    return f"Q.S.C.A.USD.F.5J.A.{iso}.A.5J.N"

@st.cache_data(ttl=3600, show_spinner=False)
def load_ids_usd(iso: str, start="2000", end="2025") -> pd.DataFrame:
    return _bis_series("BIS/WS_DEBT_SEC2_PUB/1.0", _ids_key(iso), start, end)

@st.cache_data(ttl=3600, show_spinner=False)
def load_lbs_crossborder_usd(iso: str, start="2000", end="2025") -> pd.DataFrame:
    return _bis_series("BIS/WS_LBS_D_PUB/1.0", _lbs_cross_key(iso), start, end)

@st.cache_data(ttl=3600, show_spinner=False)
def load_lbs_local_fx_usd(iso: str, start="2000", end="2025") -> pd.DataFrame:
    return _bis_series("BIS/WS_LBS_D_PUB/1.0", _lbs_local_fx_key(iso), start, end)

# 1) Ülke seçimi — yatay radio, benzersiz key
COUNTRY_ISO = {
    "Mexico":"MX","China":"CN","Turkey":"TR","SaudiArabia":"SA","Indonesia":"ID","Brazil":"BR",
    "Korea":"KR","Chile":"CL","India":"IN","Argentina":"AR","Taipei":"TW","Russia":"RU",
    "SouthAfrica":"ZA","Malaysia":"MY"
}
PALETTE = {
    "Mexico":"#e74c3c","China":"#8e44ad","Turkey":"#f39c12","SaudiArabia":"#27ae60","Indonesia":"#d35400",
    "Brazil":"#c0392b","Korea":"#9b59b6","Chile":"#16a085","India":"#7f8c8d","Argentina":"#1abc9c",
    "Taipei":"#2ecc71","Russia":"#d35400","SouthAfrica":"#7f8c8d","Malaysia":"#9b59b6","Others":"#bdc3c7"
}

sel_country = st.radio(
    "Select country",
    options=list(COUNTRY_ISO.keys()),
    index=list(COUNTRY_ISO.keys()).index("Mexico"),
    horizontal=True,
    key="cd_country_radio",
)

# 2) SADECE İKİNCİ PALET (legend görünümü) — tıklanmaz, görsel referans
st.markdown(
    " ".join([
        f"<span style='display:inline-flex;align-items:center;margin-right:18px'>"
        f"<span style='width:14px;height:14px;border-radius:4px;background:{PALETTE[k]};display:inline-block;margin-right:8px'></span>"
        f"<span style='font-weight:500;color:#2b2f36'>{k}</span></span>"
        for k in ["Mexico","China","Turkey","SaudiArabia","Indonesia","Brazil","Korea",
                  "Chile","India","Argentina","Taipei","Russia","SouthAfrica","Malaysia"]
    ] + [
        "<span style='display:inline-flex;align-items:center;margin-right:18px'>"
        "<span style='width:14px;height:14px;border-radius:4px;background:#bdc3c7;display:inline-block;margin-right:8px'></span>"
        "<span style='font-weight:500;color:#2b2f36'>Others</span></span>"
    ]),
    unsafe_allow_html=True
)

# 3) Başlangıç–Bitiş: Sayfada önceden varsa onları kullan; yoksa benzersiz key’lerle oluştur
if "start_year" in st.session_state and "end_year" in st.session_state:
    start_used = st.session_state.start_year
    end_used   = st.session_state.end_year
else:
    col_a, col_b = st.sidebar.columns(2)
    with col_a:
        start_used = st.number_input("Start", 1980, 2025, 2000, key="cd_start_input")
    with col_b:
        end_used = st.text_input("End", "2025", key="cd_end_input")




# ---------------------- Veri çek / birleştir ----------------------
iso = COUNTRY_ISO[sel_country]

try:
    ids = load_ids_usd(iso, start=str(start_year), end=(end_year or "2025")).rename(columns={"Val":"Debt"})
except Exception as e:
    ids = pd.DataFrame(columns=["Time","Debt"])

try:
    xb  = load_lbs_crossborder_usd(iso, start=str(start_year), end=(end_year or "2025")).rename(columns={"Val":"CrossBorder"})
except Exception as e:
    xb = pd.DataFrame(columns=["Time","CrossBorder"])

try:
    lfx = load_lbs_local_fx_usd(iso, start=str(start_year), end=(end_year or "2025")).rename(columns={"Val":"LocalFX"})
except Exception as e:
    lfx = pd.DataFrame(columns=["Time","LocalFX"])

if ids.empty and xb.empty and lfx.empty:
    st.error("BIS IDS/LBS serileri alınamadı (üçü de boş döndü). Anahtarları BIS portalındaki SDMX Key’e göre kontrol edin.")
    st.stop()

dfs = [s for s in [ids, xb, lfx] if not s.empty]
dfc = dfs[0]
for s in dfs[1:]:
    dfc = dfc.merge(s, on="Time", how="outer")
dfc = dfc.sort_values("Time").reset_index(drop=True)

# USD milyon → milyar
for c in ["Debt","CrossBorder","LocalFX"]:
    if c in dfc.columns:
        dfc[c] = pd.to_numeric(dfc[c], errors="coerce")/1000.0

present_cols = [c for c in ["Debt","CrossBorder","LocalFX"] if c in dfc.columns]
if present_cols:
    dfc["Total"] = dfc[present_cols].sum(axis=1, min_count=1)

# ---------------------- KPI kutuları ----------------------
if dfc["Total"].notna().any():
    last_idx = dfc["Total"].last_valid_index()
    latest = dfc.loc[last_idx]
else:
    latest = pd.Series(dtype=float)

k1, k2, k3, k4 = st.columns(4)
with k1: st.metric("Debt (USD bn)", f"{latest.get('Debt', np.nan):,.0f}")
with k2: st.metric("Cross-border (USD bn)", f"{latest.get('CrossBorder', np.nan):,.0f}")
with k3: st.metric("Local FX (USD bn)", f"{latest.get('LocalFX', np.nan):,.0f}")
with k4: st.metric("Total (USD bn)", f"{latest.get('Total', np.nan):,.0f}")

# ---------------------- Çizgi grafik ----------------------
fig = go.Figure()
if "Debt" in dfc: 
    fig.add_trace(go.Scatter(x=dfc["Time"], y=dfc["Debt"], name="Debt (IDS)", mode="lines", line=dict(width=3, color="#8e44ad")))
if "CrossBorder" in dfc: 
    fig.add_trace(go.Scatter(x=dfc["Time"], y=dfc["CrossBorder"], name="Cross-border (LBS)", mode="lines", line=dict(width=3, color="#2980b9")))
if "LocalFX" in dfc: 
    fig.add_trace(go.Scatter(x=dfc["Time"], y=dfc["LocalFX"], name="Local FX (LBS)", mode="lines", line=dict(width=3, color="#27ae60")))
if present_cols:
    fig.add_trace(go.Scatter(x=dfc["Time"], y=dfc["Total"], name="Total", mode="lines", line=dict(width=2, dash="dot", color="#7f8c8d")))

fig.update_layout(
    title=dict(text=f"{sel_country} — Debt vs Cross-border vs Local FX (USD bn)", x=0.5),
    height=520,
    legend=dict(orientation="h", yanchor="top", y=-0.2, xanchor="center", x=0.5)
)
fig.update_yaxes(tickformat=",.0f", ticksuffix="B", separatethousands=True)
st.plotly_chart(fig, use_container_width=True)

# ---------------------- Donut (son dönem karışımı) ----------------------
if present_cols and len(present_cols) >= 2 and dfc.dropna(subset=present_cols).shape[0] > 0:
    last = dfc.dropna(subset=present_cols).iloc[-1]
    vals = [last[c] for c in present_cols]
    labs_map = {"Debt":"Debt","CrossBorder":"Cross-border","LocalFX":"Local FX"}
    labs = [labs_map[c] for c in present_cols]
    cols = ["#8e44ad","#2980b9","#27ae60"][:len(vals)]
    fig2 = go.Figure(go.Pie(values=vals, labels=labs, hole=0.5, textinfo="label+percent",
                            marker=dict(colors=cols)))
    fig2.update_layout(title=dict(text=f"{sel_country} — latest mix (share of total)", x=0.5), height=380)
    st.plotly_chart(fig2, use_container_width=True)
else:
    st.info("Mix grafiği için en az iki dolu bileşen gerekir.")





# ---------- Methodology ----------
st.markdown("### 📋 Methodology")
with st.expander("🔎 Click to expand methodology details", expanded=False):
    st.markdown("""
**🌍 Data Source**
- BIS Global Liquidity Indicators (GLI) — [link](https://data.bis.org/topics/GLI)  
- Coverage: USD-denominated *cross-border credit* to non-bank borrowers  

**📏 Units & Scaling**
- Raw data: millions of USD → converted to **billions** (÷1000)  
- Time frequency: **quarterly** observations  

**📈 Metrics**
- **YoY Growth (%):** 4-quarter percent change  
- **Comparison logic:**  
  - *AllCredit ≈ Loans + Debt Securities*  
  - Advanced vs Emerging, Regional Areas, Individual Countries  

**🎨 Visual Conventions**
- 📈 Line charts → stock levels  
- 📊 Bar charts → YoY growth  
- ✅ Green = positive growth, ❌ Red = negative growth  
- 🟪 Advanced = purple, 🟧 Loans = orange, 🟥 Emerging = red, 🟩 Regions = green  

**🕑 Shaded Periods**
- 2007–09: Financial Crisis  
- 2020: COVID-19 Shock  
- 2022– : Fed Tightening Cycle  

**🧩 Structure**
- Tabs: Total, Debt, Loans, Comparison  
- Advanced vs Emerging (aggregate)  
- Emerging Area (regional totals: 🌍 Africa & ME, Asia, Europe, LatAm)  
- Emerging Countries (country-level drilldown)  

**🌐 Country Coverage**
- 🌍 Africa & Middle East: Saudi Arabia, South Africa  
- 🌏 Emerging Asia: China, Taipei, India, Indonesia, Korea, Malaysia  
- 🌍 Emerging Europe: Russia, Turkey  
- 🌎 Latin America: Argentina, Brazil, Chile, Mexico  
    """)

# ---------- Footer ----------
st.markdown(
    """
    <div style="text-align:center;color:#64748b;font-size:0.95rem;padding:20px 0;">
        <a href="https://veridelisi.substack.com/">Veri Delisi</a>🚀 <br>
        <em>Engin Yılmaz • Amherst • September 2025 </em>
    </div>
    """,
    unsafe_allow_html=True
)

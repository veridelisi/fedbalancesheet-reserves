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
    

    # ALT SEKME ÇUBUĞU: Credits | Debts | Loans
    ec_tabs = st.tabs(["Credits", "Debts", "Loans"])
    tabCredits, tabDebts, tabLoans = ec_tabs

    # Ortak: Ülke anahtarları
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

    # ====================== TAB 1: Credits ======================
    with tabCredits:
        # (1) Top-14 pie (emerging total referans)
        series_cache = {}
        last_dates = []
        for cname, ckey in COUNTRY_KEYS.items():
            s = load_series_billion(ckey)
            if s.empty: 
                continue
            s = s.sort_values("Time")
            series_cache[cname] = s
            last_dates.append(s["Time"].iloc[-1])

        EME_TOTAL_KEY = "Q.USD.4T.N.A.I.B.USD"
        eme_total = load_series_billion(EME_TOTAL_KEY).sort_values("Time")
        if not eme_total.empty:
            last_dates.append(eme_total["Time"].iloc[-1])

        if last_dates:
            snap_date = min(last_dates)
            latest_rows = []
            for cname, s in series_cache.items():
                s_cut = s[s["Time"] <= snap_date]
                if not s_cut.empty:
                    latest_rows.append((cname, float(s_cut["Val"].iloc[-1])))
            df_latest = pd.DataFrame(latest_rows, columns=["Country","Value"]).sort_values("Value", ascending=False)

            eme_cut = eme_total[eme_total["Time"] <= snap_date]
            eme_total_val = float(eme_cut["Val"].iloc[-1]) if not eme_cut.empty else df_latest["Value"].sum()

            N_TOP = 14
            df_top = df_latest.head(N_TOP).copy()
            others_val = max(eme_total_val - df_top["Value"].sum(), 0.0)
            if others_val > 0:
                df_top = pd.concat([df_top, pd.DataFrame([["Others", others_val]], columns=["Country","Value"])], ignore_index=True)

            total_ref = max(eme_total_val, 1e-9)
            df_top["ShareTotal"] = df_top["Value"] / total_ref
            df_top["Text"] = df_top["Country"] + "\n" + (df_top["ShareTotal"]*100).round(1).astype(str) + "%"

            base_colors = [
                "#e74c3c","#8e44ad","#f39c12","#27ae60","#2980b9",
                "#d35400","#2c3e50","#9b59b6","#16a085","#c0392b",
                "#7f8c8d","#1abc9c","#34495e","#f1c40f","#bdc3c7"
            ]
            colors = base_colors[:len(df_top)]

            fig_pie = go.Figure(go.Pie(
                labels=df_top["Country"],
                values=df_top["Value"],
                hole=0.45,
                sort=False,
                text=df_top["Text"],
                textinfo="text",
                textposition="inside",
                insidetextorientation="radial",
                customdata=(df_top["ShareTotal"]*100),
                hovertemplate="%{label}: $%{value:,.0f}B"
                              "<br>Share of Emerging Total: %{customdata:.1f}%<extra></extra>",
                marker=dict(colors=colors)
            ))
            fig_pie.update_layout(
                title=dict(text=title_range(f"Top {N_TOP} Emerging Countries — Share in Emerging Total (as of {snap_date.date()})"), x=0.5),
                height=520,
                legend=dict(orientation="h", yanchor="top", y=-0.15, xanchor="center", x=0.5)
            )
            st.plotly_chart(fig_pie, use_container_width=True)

        # (2) Country selection + çoklu çizgi & YoY
        st.markdown("### Select countries")
        default_countries = ["Mexico","China","Turkey"]
        sel = st.multiselect("", list(COUNTRY_KEYS.keys()), default=default_countries)

        if not sel:
            st.info("Ülke seçiniz.")
        else:
            dfc = None
            for i, c in enumerate(sel):
                s = load_series_billion(COUNTRY_KEYS[c]).rename(columns={"Val": c})
                dfc = s if dfc is None else dfc.merge(s, on="Time", how="outer")
            dfc = dfc.sort_values("Time").reset_index(drop=True)

            palette = ["#e74c3c","#8e44ad","#f39c12","#27ae60","#2980b9","#d35400",
                       "#2c3e50","#9b59b6","#16a085","#c0392b","#7f8c8d","#1abc9c",
                       "#34495e","#f1c40f"]

            # Seviye
            fig = go.Figure()
            for i, c in enumerate(sel):
                fig.add_trace(go.Scatter(
                    x=dfc["Time"], y=dfc[c], mode="lines", name=c,
                    line=dict(width=3, color=palette[i % len(palette)]),
                    hovertemplate="$%{y:,.0f}B<extra>"+c+"</extra>"
                ))
            add_shading(fig); yaxis_k(fig)
            fig.update_layout(title=dict(text=title_range("Emerging Countries — Total Credit (USD bn)"), x=0.5),
                              height=560, legend=dict(orientation="h"))
            st.plotly_chart(fig, use_container_width=True)

            # YoY
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
                barmode="group",
                height=420,
                legend=dict(orientation="h", yanchor="top", y=-0.25, xanchor="center", x=0.5)
            )
            st.plotly_chart(fig2, use_container_width=True)

    # ====================== TAB 2: Debts ======================
    with tabDebts:
        st.markdown("## USD Debt (IDS) — Sector Breakdown (2000–2025)")

        IDS_FLOW = "dataflow/BIS/WS_DEBT_SEC2_PUB/1.0"
        IDS_HEADERS = {"Accept":"application/vnd.sdmx.genericdata+xml;version=2.1"}

        IDS_SECTORS = {
            "Financial corporations":     ("B.1", "#2980b9"),
            "General government":         ("2.1", "#8e44ad"),
            "Non-financial corporations": ("J.1", "#e74c3c"),
            "Private banks":              ("E.1", "#16a085"),
            "Public banks":               ("I.1", "#27ae60"),
            "Private other FIs":          ("G.1", "#f39c12"),
            "Public other FIs":           ("K.1", "#d35400"),
        }

        def ids_key(cc: str, token: str) -> str:
    # Match BIS web filter: International markets [C], USD, Foreign currency group [F]
            return f"Q.{cc}.3P.{token}.C.A.F.USD.A.A.A.A.A.I"
     

        @st.cache_data(ttl=3600, show_spinner=False)
        def fetch_ids_series_full(key: str, start="2000", end="2025") -> pd.DataFrame:
            url = f"https://stats.bis.org/api/v2/data/{IDS_FLOW}/{key}/all"
            params = {"detail":"full","startPeriod":start,"endPeriod":end}
            try:
                r = requests.get(url, params=params, headers=IDS_HEADERS, timeout=60)
                if r.status_code == 404:
                    return pd.DataFrame(columns=["Time","Val"])
                r.raise_for_status()
            except Exception:
                return pd.DataFrame(columns=["Time","Val"])
            try:
                root = ET.fromstring(r.content)
            except Exception:
                return pd.DataFrame(columns=["Time","Val"])

            ns = {'g':'http://www.sdmx.org/resources/sdmxml/schemas/v2_1/data/generic'}
            rows = []
            for s in root.findall('.//g:Series', ns):
                for obs in s.findall('.//g:Obs', ns):
                    dim = obs.find('g:ObsDimension', ns)
                    val = obs.find('g:ObsValue', ns)
                    if dim is None or val is None or not val.get('value'):
                        continue
                    t = dim.get('value')
                    v = pd.to_numeric(val.get('value'), errors="coerce")
                    if pd.isna(v): 
                        continue
                    if "Q" in t:
                        y, q = t.split("-Q")
                        m = {"1":3,"2":6,"3":9,"4":12}[q]
                        dt = pd.Timestamp(int(y), m, 1)
                    else:
                        dt = pd.Timestamp(int(t), 12, 1)
                    rows.append((dt, v/1000.0))  # M$ → B$
            if not rows:
                return pd.DataFrame(columns=["Time","Val"])
            return pd.DataFrame(rows, columns=["Time","Val"]).sort_values("Time").reset_index(drop=True)

        @st.cache_data(ttl=3600, show_spinner=False)
        def load_ids_country_long(country_label: str) -> pd.DataFrame:
            cc_map = {
                "SaudiArabia":"SA","SouthAfrica":"ZA","China":"CN","Taipei":"TW","India":"IN",
                "Indonesia":"ID","Korea":"KR","Malaysia":"MY","Russia":"RU","Turkey":"TR",
                "Argentina":"AR","Brazil":"BR","Chile":"CL","Mexico":"MX"
            }
            cc = cc_map.get(country_label)
            if not cc:
                return pd.DataFrame(columns=["Time","Sector","Val","Country"])
            frames = []
            for sector, (token, _color) in IDS_SECTORS.items():
                key = ids_key(cc, token)
                s = fetch_ids_series_full(key, start=str(start_year), end=(end_year or "2025"))
                if s.empty:
                    continue
                s["Sector"] = sector
                s["Country"] = country_label
                frames.append(s)
            return pd.concat(frames, ignore_index=True) if frames else pd.DataFrame(columns=["Time","Sector","Val","Country"])

        # Ülke seçimi (Debts)
        st.markdown("#### Select a country")
        country_list = list(COUNTRY_KEYS.keys())
        default_country = "Mexico" if "Mexico" in country_list else country_list[0]
        try:
            country_sel = st.segmented_control("Country", country_list, selection=default_country)
        except Exception:
            country_sel = st.radio("Country", country_list, horizontal=True, index=country_list.index(default_country))

        ids_long = load_ids_country_long(country_sel)

        if ids_long.empty:
            st.info("Seçili ülke için IDS (USD debt) sektörel seriler bulunamadı.")
        else:
            color_map = {k:v for k, (_t, v) in IDS_SECTORS.items()}
            fig = go.Figure()
            for sec in IDS_SECTORS.keys():
                sdf = ids_long[ids_long["Sector"] == sec]
                if sdf.empty:
                    continue
                fig.add_trace(go.Scatter(
                    x=sdf["Time"], y=sdf["Val"], mode="lines", name=sec,
                    line=dict(width=3, color=color_map.get(sec)),
                    hovertemplate=f"{country_sel} — {sec}<br>%{{x|%Y-%m}}: $%{{y:,.1f}}B<extra></extra>"
                ))
            add_shading(fig); yaxis_k(fig)
            fig.update_layout(
                title=dict(text=title_range(f"{country_sel}: USD Debt Securities — Sector Breakdown"), x=0.5),
                height=560, legend=dict(orientation="h")
            )
            st.plotly_chart(fig, use_container_width=True)


        # ====================== TAB 3: Loans (CROSS-BORDER only) ======================
    with tabLoans:
        st.markdown("### USD Loans (LBS) — Cross-border (2000–2025)")

        # ---- LBS fetcher ----
        LBS_FLOW = "dataflow/BIS/WS_LBS_D_PUB/1.0"
        LBS_HEADERS = {"Accept": "application/vnd.sdmx.genericdata+xml;version=2.1"}

        @st.cache_data(ttl=3600, show_spinner=False)
        def lbs_series_xml(key: str, start="2000", end="2025") -> pd.DataFrame:
            url = f"https://stats.bis.org/api/v2/data/{LBS_FLOW}/{key}/all"
            params = {"detail":"full", "startPeriod":start, "endPeriod":end}
            try:
                r = requests.get(url, params=params, headers=LBS_HEADERS, timeout=60)
                r.raise_for_status()
            except Exception:
                return pd.DataFrame(columns=["Time","Val"])
            try:
                root = ET.fromstring(r.content)
            except Exception:
                return pd.DataFrame(columns=["Time","Val"])

            ns = {'g':'http://www.sdmx.org/resources/sdmxml/schemas/v2_1/data/generic'}
            rows = []
            for s in root.findall('.//g:Series', ns):
                for obs in s.findall('.//g:Obs', ns):
                    dim = obs.find('g:ObsDimension', ns)
                    val = obs.find('g:ObsValue', ns)
                    if dim is None or val is None or not val.get('value'):
                        continue
                    t = dim.get('value')
                    v = pd.to_numeric(val.get('value'), errors="coerce")
                    if pd.isna(v): 
                        continue
                    if "Q" in t:
                        y, q = t.split("-Q")
                        m = {"1":3, "2":6, "3":9, "4":12}[q]
                        dt = pd.Timestamp(int(y), m, 1)
                    else:
                        dt = pd.Timestamp(int(t), 12, 1)
                    rows.append((dt, v/1000.0))  # M$ → B$
            return pd.DataFrame(rows, columns=["Time","Val"]).sort_values("Time").reset_index(drop=True)

        # Ülke kodları
        _cc_map = {
            "SaudiArabia":"SA","SouthAfrica":"ZA","China":"CN","Taipei":"TW","India":"IN",
            "Indonesia":"ID","Korea":"KR","Malaysia":"MY","Russia":"RU","Turkey":"TR",
            "Argentina":"AR","Brazil":"BR","Chile":"CL","Mexico":"MX"
        }

        # Cross-border non-bank key (tam senin verdiğin şablon)
        def lbs_key_cross_border(cc: str) -> str:
            # Q.S.C.G.USD.A.5J.A.5A.N.{CC}.N
            return f"Q.S.C.G.USD.A.5J.A.5A.N.{cc}.N"

        # ------------ Select countries (benzersiz key!) ------------
        st.markdown("### Select countries")
        default_countries = ["China","Brazil","SaudiArabia","Mexico","India"]
        sel_loans = st.multiselect(
            "", list(_cc_map.keys()),
            default=default_countries,
            key="loans_cb_country_select"   # <<<<< ÖNEMLİ: benzersiz key
        )

        if not sel_loans:
            st.info("Ülke seçiniz.")
        else:
            # ---- Cross-border merge ----
            cb_df = None
            for cname in sel_loans:
                cc = _cc_map[cname]
                key = lbs_key_cross_border(cc)
                s = lbs_series_xml(key, start=str(start_year), end=(end_year or "2025")).rename(columns={"Val": cname})
                cb_df = s if cb_df is None else cb_df.merge(s, on="Time", how="outer")
            cb_df = cb_df.sort_values("Time").reset_index(drop=True)

            palette = ["#e74c3c","#8e44ad","#f39c12","#27ae60","#2980b9","#d35400",
                    "#2c3e50","#9b59b6","#16a085","#c0392b","#7f8c8d","#1abc9c",
                    "#34495e","#f1c40f"]

            # Seviye
            fig_cb = go.Figure()
            for i, cname in enumerate(sel_loans):
                if cname in cb_df.columns:
                    fig_cb.add_trace(go.Scatter(
                        x=cb_df["Time"], y=pd.to_numeric(cb_df[cname], errors="coerce"),
                        mode="lines", name=cname,
                        line=dict(width=3, color=palette[i % len(palette)]),
                        hovertemplate="$%{y:,.0f}B<extra>"+cname+"</extra>"
                    ))
            add_shading(fig_cb); yaxis_k(fig_cb)
            fig_cb.update_layout(
                title=dict(text=title_range("Cross-border USD Loans to Non-banks (BIS LBS, USD bn)"), x=0.5),
                height=560, legend=dict(orientation="h")
            )
            st.plotly_chart(fig_cb, use_container_width=True)

            # YoY
            fig_cb_yoy = go.Figure()
            for i, cname in enumerate(sel_loans):
                if cname in cb_df.columns:
                    yo = cb_df[["Time", cname]].copy()
                    yo[cname] = pd.to_numeric(yo[cname], errors="coerce")
                    yo["YoY"] = yo[cname].pct_change(4)*100
                    fig_cb_yoy.add_trace(go.Bar(
                        x=yo["Time"], y=yo["YoY"], name=cname,
                        marker_color=palette[i % len(palette)],
                        hovertemplate="%{y:.1f}%<extra>"+cname+"</extra>"
                    ))
            fig_cb_yoy.add_hline(y=0, line_dash="dash", line_color="black")
            add_shading(fig_cb_yoy)
            fig_cb_yoy.update_yaxes(title="YoY (%)", tickformat=".1f", ticksuffix="%")
            fig_cb_yoy.update_layout(
                title=dict(text=title_range("Cross-border Loans — YoY"), x=0.5),
                barmode="group", height=420,
                legend=dict(orientation="h", yanchor="top", y=-0.25, xanchor="center", x=0.5)
            )
            st.plotly_chart(fig_cb_yoy, use_container_width=True)

        # ---------------- LOCAL TOTAL CLAIMS (USD) ----------------
    st.markdown("#### USD Loans (LBS) — Local total claims (USD)")

    # Eğer henüz yoksa local key şablonunu ekleyelim
    def lbs_key_local_total(cc: str) -> str:
        # Q.S.C.A.TO1.F.5J.A.{CC}.N.5J.R
        return f"Q.S.C.A.TO1.F.5J.A.{cc}.N.5J.R"

    # Ayrı bir seçim kutusu (farklı key!)
    st.markdown("### Select countries (Local)")
    default_local = ["Turkey", "SaudiArabia", "Mexico", "Indonesia"]
    sel_local = st.multiselect(
        "", list(_cc_map.keys()),
        default=default_local,
        key="loans_local_country_select"
    )

    if not sel_local:
        st.info("Ülke seçiniz.")
    else:
        # Veriyi birleştir
        lc_df = None
        for cname in sel_local:
            cc = _cc_map[cname]
            key = lbs_key_local_total(cc)
            s = lbs_series_xml(key, start=str(start_year), end=(end_year or "2025")).rename(columns={"Val": cname})
            lc_df = s if lc_df is None else lc_df.merge(s, on="Time", how="outer")
        lc_df = lc_df.sort_values("Time").reset_index(drop=True)

        palette = ["#e74c3c","#8e44ad","#f39c12","#27ae60","#2980b9","#d35400",
                "#2c3e50","#9b59b6","#16a085","#c0392b","#7f8c8d","#1abc9c",
                "#34495e","#f1c40f"]

        # Seviye grafiği
        fig_lc = go.Figure()
        for i, cname in enumerate(sel_local):
            if cname in lc_df.columns:
                fig_lc.add_trace(go.Scatter(
                    x=lc_df["Time"], y=pd.to_numeric(lc_df[cname], errors="coerce"),
                    mode="lines", name=cname,
                    line=dict(width=3, color=palette[i % len(palette)]),
                    hovertemplate="$%{y:,.0f}B<extra>"+cname+"</extra>"
                ))
        add_shading(fig_lc); yaxis_k(fig_lc)
        fig_lc.update_layout(
            title=dict(text=title_range("Local Total Claims (BIS LBS, USD bn)"), x=0.5),
            height=560, legend=dict(orientation="h")
        )
        st.plotly_chart(fig_lc, use_container_width=True)

        # YoY grafiği
        fig_lc_yoy = go.Figure()
        for i, cname in enumerate(sel_local):
            if cname in lc_df.columns:
                yo = lc_df[["Time", cname]].copy()
                yo[cname] = pd.to_numeric(yo[cname], errors="coerce")
                yo["YoY"] = yo[cname].pct_change(4)*100
                fig_lc_yoy.add_trace(go.Bar(
                    x=yo["Time"], y=yo["YoY"], name=cname,
                    marker_color=palette[i % len(palette)],
                    hovertemplate="%{y:.1f}%<extra>"+cname+"</extra>"
                ))
        fig_lc_yoy.add_hline(y=0, line_dash="dash", line_color="black")
        add_shading(fig_lc_yoy)
        fig_lc_yoy.update_yaxes(title="YoY (%)", tickformat=".1f", ticksuffix="%")
        fig_lc_yoy.update_layout(
            title=dict(text=title_range("Local Total Claims — YoY"), x=0.5),
            barmode="group", height=420,
            legend=dict(orientation="h", yanchor="top", y=-0.25, xanchor="center", x=0.5)
        )
        st.plotly_chart(fig_lc_yoy, use_container_width=True)

# ---------- Methodology ----------
st.markdown("### 📋 Methodology")
with st.expander("🔎 Click to expand methodology details", expanded=False):
    st.markdown("""
**🧾 Basics**
- 📦 Units → BIS data are in *millions of USD* → converted to **billions (÷1000)**.  
- 🗓️ Frequency → **Quarterly** (`YYYY-Qn`) → converted to end-of-quarter timestamps.  
- 📈 Growth → **YoY (%) = 4-quarter change**.  
- 🗓️ API Base Information: (https://stats.bis.org/api-doc/v2/)
- 🧭 API base pattern: https://stats.bis.org/api/v2/data/%7BFLOW_PATH%7D/%7BKEY%7D/all?detail=full&startPeriod=YYYY&endPeriod=YYYY
Data are parsed from **SDMX GenericData 2.1 XML**.

---

## 1️⃣ Top Tabs
### • Total Credit / Debt Securities / Loans / Comparison
- **Flow:** `BIS/WS_GLI/1.0`
- **Keys (USD totals):**         
                   
- All sectors - US dollar cross-border & local in fcy credit vis-a-vis non-banks, total, in All countries excluding residents, 
in terms of credit (loans & debt securities)
- Total Credit → `Q.USD.3P.N.A.I.B.USD`  
- Example: (https://data.bis.org/topics/GLI/BIS,WS_GLI,1.0/Q.USD.3P.N.A.I.B.USD) 
                
- Total Credit= Debt Securities + Loans
                
- Debt Securities → `Q.USD.3P.N.A.I.D.USD`
- Example: (https://data.bis.org/topics/GLI/BIS,WS_GLI,1.0/Q.USD.3P.N.A.I.D.USD)
                
- Loans → `Q.USD.3P.N.B.I.G.USD`
- Example: (https://data.bis.org/topics/GLI/BIS,WS_GLI,1.0/Q.USD.3P.N.B.I.G.USD)
- The **Comparison** tab overlays these three (levels + YoY).

---

## 2️⃣ Advanced vs Emerging
- **Flow:** `BIS/WS_GLI/1.0`
- **Emerging aggregates:**
- Emerging Debt → `Q.USD.4T.N.A.I.D.USD`
- Example:(https://data.bis.org/topics/GLI/BIS,WS_GLI,1.0/Q.USD.4T.P.A.I.D.USD)              
- Emerging Bank Loans → `Q.USD.4T.N.B.I.G.USD`
- Example: (https://data.bis.org/topics/GLI/BIS,WS_GLI,1.0/Q.USD.4T.N.B.I.G.USD)             
- **Advanced** = Total − Emerging  
Both plotted as level and YoY charts.

---

## 3️⃣ Emerging Area
- **Flow:** `BIS/WS_GLI/1.0`
- **Regional total credit (USD):**
- 🌍 Africa & Middle East → `Q.USD.4W.N.A.I.B.USD`
- Example: (https://data.bis.org/topics/GLI/BIS,WS_GLI,1.0/Q.USD.4W.N.A.I.B.USD)
- 🌏 Emerging Asia → `Q.USD.4Y.N.A.I.B.USD`
- Example: (https://data.bis.org/topics/GLI/BIS,WS_GLI,1.0/Q.USD.4Y.N.A.I.B.USD)               
- 🌍 Emerging Europe → `Q.USD.3C.N.A.I.B.USD`
- Example:(https://data.bis.org/topics/GLI/BIS,WS_GLI,1.0/Q.USD.3C.N.A.I.B.USD)              
- 🌎 Latin America → `Q.USD.4U.N.A.I.B.USD`
- Example:(https://data.bis.org/topics/GLI/BIS,WS_GLI,1.0/Q.USD.4U.N.A.I.B.USD)               
- **Comparison** shows a pie of latest regional shares + line chart for evolution (2000–2025).

---

## 4️⃣ Emerging Countries (with inner tabs)

### A) Credits 💳
- **Flow:** `BIS/WS_GLI/1.0`
- **Key pattern (country total credit, USD):**  
`Q.USD.{CC}.N.A.I.B.USD`  
`{CC}` = ISO-2 code (e.g., MX, CN, TR).  
- Example Mexico : (https://data.bis.org/topics/GLI/BIS,WS_GLI,1.0/Q.USD.MX.N.A.I.B.USD)
- Uses Emerging Total (`Q.USD.4T.N.A.I.B.USD`) for Top-14 share pie.

---

### B) Debts 🧩
- **Flow:** `BIS/WS_DEBT_SEC2_PUB/1.0`
- **Key pattern (country × sector):**  
`Q.{CC}.3P.{TOKEN}.C.A.F.USD.A.A.A.A.A.I`
- **Sector tokens:**
- Financial corporations → `B.1`
- General government → `2.1`
- Non-financial corporations → `J.1`
- Private banks → `E.1`
- Public banks → `I.1`
- Private other FIs → `G.1`
- Public other FIs → `K.1`
- Example (Turkey – Government):
- **Sector Share logic:**
- Banks = Private + Public banks  
- Government = General government  
- Non-banks = Financial corp + NFC + Private OFIs + Public OFIs  
- Shares = bucket / (Banks + Government + Non-banks)

---

### C) Loans 🏦
- **Flow:** `BIS/WS_LBS_D_PUB/1.0`

**Cross-border claims on non-banks (USD)**  
- Key: `Q.S.C.G.USD.A.5J.A.5A.N.{CC}.N`  
Example (Mexico):  
[Cross-border MX](https://stats.bis.org/api/v2/data/dataflow/BIS/WS_LBS_D_PUB/1.0/Q.S.C.G.USD.A.5J.A.5A.N.MX.N/all?detail=full&startPeriod=2000&endPeriod=2025)

**Local total claims (USD)**  
- Key: `Q.S.C.A.TO1.F.5J.A.{CC}.N.5J.R`  
Example (Mexico):  
[Local MX](https://stats.bis.org/api/v2/data/dataflow/BIS/WS_LBS_D_PUB/1.0/Q.S.C.A.TO1.F.5J.A.MX.N.5J.R/all?detail=full&startPeriod=2000&endPeriod=2025)
- Both use the same selection widget and display **lines (levels)** + **bars (YoY)**.

---

## ⚙️ Transformations & UI
- 🔁 SDMX GenericData parsing; missing obs safely skipped.  
- 🧮 Converted to billions; year-end = last quarterly obs.  
- 🎛️ Streamlit tabs + multiselects with unique keys.  
- 🎨 Plotly:
- Lines → stock levels  
- Bars → YoY growth  
- Shading:
  🟥 2007–09 Financial Crisis  
  🟧 2020 COVID-19  
  🟦 2022– Fed Tightening Cycle
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

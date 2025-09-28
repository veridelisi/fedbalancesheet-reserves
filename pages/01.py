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

# --- Hide sidebar + tab style (eski görünüm) ---
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

SERIES = {
    "AllCredit":      "Q.USD.3P.N.A.I.B.USD",
    "DebtSecurities": "Q.USD.3P.N.A.I.D.USD",
    "Loans":          "Q.USD.3P.N.B.I.G.USD",
}

st.sidebar.header("BIS WS_GLI")
start_year = st.sidebar.number_input("Start", 1980, 2025, 2000)
end_year   = st.sidebar.text_input("End", "2025")

# --- Pull & merge ---
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
        tickformat=f",.{decimals}f",  # ",.0f" → 1,250   ",.1f" → 1,250.5
        ticksuffix="B",
        separatethousands=True,
        showexponent="none"
    )

def title_range(prefix):
    return f"<b>{prefix} ({df['Time'].min().year}–{df['Time'].max().year})</b>"

# --------------------- charts (senin düzen) ---------------------
def total_credit():
    fig = go.Figure()
    fig.add_trace(go.Scatter(x=df["Time"], y=df["AllCredit"], mode="lines",
                             line=dict(width=3, color="#e74c3c")))
    add_shading(fig)
    fig.update_layout(title=dict(text=title_range("Total Eurodollar Credit($bn)"), x=0.5),
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
    fig.add_trace(go.Scatter(x=df["Time"], y=df["DebtSecurities($bn)"], mode="lines",
                             line=dict(width=3, color="#8e44ad")))
    add_shading(fig); yaxis_k(fig)
    fig.update_layout(title=dict(text=title_range("Debt Securities"), x=0.5),
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
    fig.add_trace(go.Scatter(x=df["Time"], y=df["Loans($bn)"], mode="lines",
                             line=dict(width=3, color="#f39c12")))
    add_shading(fig); yaxis_k(fig)
    fig.update_layout(title=dict(text=title_range("Loans"), x=0.5),
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
    fig.update_layout(title=dict(text=title_range("Comparison"), x=0.5),
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

# --------------------- LAYOUT: TABS ---------------------
st.title("Eurodollar Market Evolution — 2000-2025")
t1, t2, t3, t4 = st.tabs(["Total Credit", "Debt Securities", "Loans", "Comparison"])
with t1: total_credit()
with t2: debt_securities()
with t3: loans()
with t4: comparison()

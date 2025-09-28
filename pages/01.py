import requests
import pandas as pd
import numpy as np
import streamlit as st
import plotly.graph_objects as go
import xml.etree.ElementTree as ET

st.set_page_config(page_title="Eurodollar Market Evolution — 2000-2025", layout="wide")

# --- Gezinme Barı ---
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

# --- Sol menü gizle ---
st.markdown("""
<style>
  [data-testid="stSidebarNav"]{display:none;}
  section[data-testid="stSidebar"][aria-expanded="true"]{display:none;}
</style>
""", unsafe_allow_html=True)

# ======================= BIS LOADER (GENERIC XML) =======================
FLOW_PATH = "dataflow/BIS/WS_GLI/1.0"  # sabit
HEADERS   = {"Accept": "application/vnd.sdmx.genericdata+xml;version=2.1"}

@st.cache_data(ttl=3600, show_spinner=False)
def bis_series_xml(key: str, start="2000", end="2025") -> pd.DataFrame:
    """
    BIS SDMX-XML (genericdata 2.1) -> DataFrame[Time, Val]
    - Endpoint: https://stats.bis.org/api/v2/data/dataflow/BIS/WS_GLI/1.0/{key}/all?detail=full&startPeriod=...&endPeriod=...
    - Dönen Val: ham değer (çoğunlukla USD milyon). Aşağıda milyara ölçekleyeceğiz.
    """
    base = f"https://stats.bis.org/api/v2/data/{FLOW_PATH}/{key}/all?detail=full"
    if start: base += f"&startPeriod={start}"
    if end:   base += f"&endPeriod={end}"

    r = requests.get(base, headers=HEADERS, timeout=60)
    r.raise_for_status()

    root = ET.fromstring(r.content)
    ns = {'g': 'http://www.sdmx.org/resources/sdmxml/schemas/v2_1/data/generic'}

    rows = []
    for series in root.findall('.//g:Series', ns):
        for obs in series.findall('.//g:Obs', ns):
            dim = obs.find('g:ObsDimension', ns)
            val = obs.find('g:ObsValue', ns)
            if val is None: 
                continue
            period = dim.get('value') if dim is not None else None
            value  = val.get('value')
            rows.append({'period': period, 'Val': value})

    out = pd.DataFrame(rows)
    if out.empty:
        return out

    out["Val"] = pd.to_numeric(out["Val"], errors="coerce")

    # 'YYYY-Qn' -> çeyrek sonu timestamp
    def to_q_end(s):
        s = str(s)
        if "-Q" in s: s = s.replace("-Q","Q")
        try: return pd.Period(s, freq="Q").to_timestamp(how="end")
        except: return pd.to_datetime(s, errors="coerce")
    out["Time"] = out["period"].apply(to_q_end)

    out = out.dropna(subset=["Time","Val"]).sort_values("Time").reset_index(drop=True)
    return out[["Time","Val"]]

# --- Seriler (senin anahtarların) ---
SERIES = {
    "AllCredit":      "Q.USD.3P.N.A.I.B.USD",
    "DebtSecurities": "Q.USD.3P.N.A.I.D.USD",
    "Loans":          "Q.USD.3P.N.B.I.G.USD",
}

st.sidebar.header("BIS WS_GLI (XML)")
start_year = st.sidebar.number_input("Başlangıç yılı", min_value=1980, max_value=2025, value=2000, step=1)
end_year   = st.sidebar.text_input("Bitiş yılı (boş=2025)", value="2025")

# --- Çek & Birleştir ---
try:
    dfs = []
    for name, key in SERIES.items():
        s = bis_series_xml(key, start=str(start_year), end=(end_year or "2025"))
        s = s.rename(columns={"Val": name})
        dfs.append(s)

    df = dfs[0]
    for s in dfs[1:]:
        df = df.merge(s, on="Time", how="outer")

    df = df.sort_values("Time").reset_index(drop=True)
    df["Year"] = df["Time"].dt.year

    # Birimler: (BIS çoğunlukla USD milyon) → milyar
    for name in SERIES.keys():
        df[name] = pd.to_numeric(df[name], errors="coerce") / 1000.0

except Exception as e:
    st.error(f"BIS verisi çekilemedi: {e}")
    st.stop()

# ============================ HELPERS =============================
def add_shading(fig):
    crisis = [
        (pd.to_datetime("2007-12-01"), pd.to_datetime("2009-06-01"), "Financial Crisis"),
        (pd.to_datetime("2020-02-01"), pd.to_datetime("2020-04-01"), "COVID-19"),
    ]
    for x0, x1, label in crisis:
        fig.add_vrect(x0=x0, x1=x1, fillcolor="red", opacity=0.10, line_width=0,
                      annotation_text=label, annotation_position="top left")
    x0 = pd.to_datetime("2022-06-01")
    x1 = pd.to_datetime(df["Time"].max())
    fig.add_vrect(x0=x0, x1=x1, fillcolor="orange", opacity=0.08, line_width=0,
                  annotation_text="Fed Tightening", annotation_position="top left")

def yaxis_k(fig, tickvals=None):
    if tickvals is not None:
        fig.update_yaxes(tickformat="~s", tickvals=tickvals,
                         ticktext=[f"{int(v/1000)}k" for v in tickvals], showexponent="none")
    else:
        fig.update_yaxes(tickformat="~s", showexponent="none")

def title_range(prefix):
    return f"<b>{prefix} ({df['Time'].min().year}–{df['Time'].max().year})</b>"

def legend_bottom():
    return dict(orientation="h", yanchor="top", y=-0.25, xanchor="center", x=0.5)

# ============================ CHARTS ==============================
st.title("Eurodollar Market Evolution — 2000-2025")

def total_credit():
    fig = go.Figure()
    fig.add_trace(go.Scatter(x=df["Time"], y=df["AllCredit"], mode="lines",
                             line=dict(width=3, color="#e74c3c")))
    add_shading(fig)
    fig.update_layout(title=dict(text=title_range("Total Eurodollar Credit"), x=0.5),
                      height=520)
    yaxis_k(fig)
    st.plotly_chart(fig, use_container_width=True)

    yoy = df.copy()
    yoy["YoY"] = yoy["AllCredit"].pct_change(4)*100
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
    fig.update_layout(title=dict(text=title_range("Debt Securities"), x=0.5),
                      height=520)
    st.plotly_chart(fig, use_container_width=True)

    yoy = df.copy()
    yoy["YoY"] = yoy["DebtSecurities"].pct_change(4)*100
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
    fig.update_layout(title=dict(text=title_range("Loans"), x=0.5),
                      height=520)
    st.plotly_chart(fig, use_container_width=True)

    yoy = df.copy()
    yoy["YoY"] = yoy["Loans"].pct_change(4)*100
    fig2 = go.Figure()
    fig2.add_trace(go.Bar(x=yoy["Time"], y=yoy["YoY"],
                          marker_color=np.where(yoy["YoY"]>=0,"#27ae60","#e74c3c")))
    fig2.add_hline(y=0, line_dash="dash", line_color="black")
    fig2.update_layout(title=dict(text=title_range("Loans — YoY"), x=0.5),
                       height=420)
    st.plotly_chart(fig2, use_container_width=True)

def comparison():
    # --- LEVELS (üstte) ---
    fig = go.Figure()
    fig.add_trace(go.Scatter(x=df["Time"], y=df["AllCredit"], mode="lines",
                             name="Total", line=dict(width=3, color="#e74c3c")))
    fig.add_trace(go.Scatter(x=df["Time"], y=df["DebtSecurities"], mode="lines",
                             name="Debt", line=dict(width=3, color="#8e44ad")))
    fig.add_trace(go.Scatter(x=df["Time"], y=df["Loans"], mode="lines",
                             name="Loans", line=dict(width=3, color="#f39c12")))
    add_shading(fig); yaxis_k(fig)
    fig.update_layout(title=dict(text=title_range("Comparison"), x=0.5),
                      height=620, legend=legend_bottom())
    st.plotly_chart(fig, use_container_width=True)

    # --- YoY (altta: tek grafik, 3 seri) ---
    d = df.sort_values("Time").copy()
    lag = 4  # çeyrek verisi
    d["TotalYoY"] = d["AllCredit"].pct_change(lag) * 100
    d["DebtYoY"]  = d["DebtSecurities"].pct_change(lag) * 100
    d["LoansYoY"] = d["Loans"].pct_change(lag) * 100
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
    fig2.update_layout(
        title=dict(text=title_range("YoY Growth — Total vs Debt vs Loans"), x=0.5),
        barmode="group",
        height=420,
        legend=legend_bottom()
    )
    st.plotly_chart(fig2, use_container_width=True)

# ========================== ÇAĞIR =========================
st.subheader("Total Credit")
total_credit()

st.subheader("Debt Securities")
debt_securities()

st.subheader("Loans")
loans()

st.subheader("Comparison")
comparison()

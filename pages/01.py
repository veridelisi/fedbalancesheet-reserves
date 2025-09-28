# pages/01_Eurodollar.py  (veya senin sayfa dosyan)
import requests
import pandas as pd
import numpy as np
import streamlit as st
import plotly.graph_objects as go
from pathlib import Path

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

# ========================== BIS YÜKLEYİCİ ==========================
FLOW = "WS_GLI"
SERIES = {
    "AllCredit":      "Q.USD.3P.N.A.I.B.USD",
    "DebtSecurities": "Q.USD.3P.N.A.I.D.USD",
    "Loans":          "Q.USD.3P.N.B.I.G.USD",
}

@st.cache_data(ttl=3600, show_spinner=False)
def bis_series_json(key: str, start="2000", end=2025) -> pd.DataFrame:
    """
    BIS SDMX-JSON -> DataFrame[Time, Val]
    - Time: çeyrek sonu timestamp
    - Val: ham değer (BIS çoğunlukla milyon USD)
    """
    url = f"https://stats.bis.org/api/v2/data/{FLOW}/{key}?format=sdmx-json"
    if start: url += f"&startPeriod={start}"
    if end:   url += f"&endPeriod={end}"

    r = requests.get(url, timeout=60)
    r.raise_for_status()
    js = r.json()

    # TIME_PERIOD etiketleri
    obs_dims = js["structure"]["dimensions"]["observation"]
    time_vals = []
    for d in obs_dims:
        if d.get("id","").upper() in ("TIME_PERIOD","TIME"):
            time_vals = [v.get("id") or v.get("name") for v in d.get("values", [])]
            break

    rows = []
    series = js["dataSets"][0]["series"]
    for _, sobj in series.items():
        for ok, arr in sobj.get("observations", {}).items():
            t = int(ok)
            rows.append({
                "_period": time_vals[t] if t < len(time_vals) else None,
                "Val": arr[0]
            })

    out = pd.DataFrame(rows)
    out["Val"] = pd.to_numeric(out["Val"], errors="coerce")

    # 'YYYY-Qn' -> çeyrek sonu timestamp
    per = pd.PeriodIndex(out["_period"].astype(str).str.replace("-Q","Q"), freq="Q")
    out["Time"] = per.to_timestamp(how="end")
    return out[["Time", "Val"]].dropna().sort_values("Time").reset_index(drop=True)

# --- Kullanıcı seçenekleri (isteğe bağlı) ---
st.sidebar.header("Veri Kaynağı: BIS WS_GLI")
start_year = st.sidebar.number_input("Başlangıç yılı", min_value=1980, max_value=2025, value=2000, step=1)
end_year   = st.sidebar.text_input("Bitiş yılı (boş = son)", value="")

# --- Çek & Birleştir ---
try:
    dfs = []
    for name, key in SERIES.items():
        s = bis_series_json(key, start=str(start_year), end=(2025))
        s = s.rename(columns={"Val": name})
        dfs.append(s)

    df = dfs[0]
    for s in dfs[1:]:
        df = df.merge(s, on="Time", how="outer")

    # Hazırlık
    df = df.sort_values("Time").reset_index(drop=True)
    df["Year"] = df["Time"].dt.year

    # Birimler: milyon USD → milyar USD
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
                      height=620, legend=dict(orientation="h"))
    st.plotly_chart(fig, use_container_width=True)

    # --- YoY (altta: tek grafik, 3 seri) ---
    d = df.sort_values("Time").copy()

    # Aylık/çeyreklik lag algıla (≈30 gün -> 12; ≈90 gün -> 4)
    try:
        delta_days = (d["Time"].diff().median()).days
    except Exception:
        delta_days = 30
    lag = 4 if (pd.notnull(delta_days) and delta_days >= 80) else 12

    d["TotalYoY"] = d["AllCredit"].pct_change(lag) * 100
    d["DebtYoY"]  = d["DebtSecurities"].pct_change(lag) * 100
    d["LoansYoY"] = d["Loans"].pct_change(lag) * 100
    yoy_plot = d.dropna(subset=["TotalYoY","DebtYoY","LoansYoY"])

    fig2 = go.Figure()
    fig2.add_trace(go.Bar(x=yoy_plot["Time"], y=yoy_plot["TotalYoY"], name="Total YoY",
                          marker_color="#e74c3c",
                          hovertemplate="%{y:.1f}%<extra>Total</extra>"))
    fig2.add_trace(go.Bar(x=yoy_plot["Time"], y=yoy_plot["DebtYoY"], name="Debt YoY",
                          marker_color="#8e44ad",
                          hovertemplate="%{y:.1f}%<extra>Debt</extra>"))
    fig2.add_trace(go.Bar(x=yoy_plot["Time"], y=yoy_plot["LoansYoY"], name="Loans YoY",
                          marker_color="#f39c12",
                          hovertemplate="%{y:.1f}%<extra>Loans</extra>"))

    fig2.add_hline(y=0, line_dash="dash", line_color="black")
    add_shading(fig2)
    fig2.update_yaxes(title="YoY (%)", ticksuffix="%", tickformat=".1f")
    fig2.update_layout(
        title=dict(text=title_range("YoY Growth — Total vs Debt vs Loans"), x=0.5),
        barmode="group",
        height=420,
        legend=dict(orientation="h", yanchor="top", y=-0.25, xanchor="center", x=0.5)
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

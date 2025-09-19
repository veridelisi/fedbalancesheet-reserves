import streamlit as st
import pandas as pd
import numpy as np
from pathlib import Path
import plotly.graph_objects as go

st.set_page_config(page_title="Eurodollar Market Evolution — 2000..latest", layout="wide")

st.title("Eurodollar Market Evolution — 2000..latest")

# ---------- File input ----------
st.sidebar.header("Veri Kaynağı")
uploaded = st.sidebar.file_uploader("CSV veya Excel (.csv, .xlsx) yükleyin", type=["csv","xlsx"])

default_path = Path("0analysis.xlsx")

@st.cache_data(show_spinner=False)
def load_data(file, filename_hint=None):
    # file: BytesIO veya Path
    # filename_hint dosya uzantısı ayırt etmek için
    if file is None:
        # fallback: yerel 0analysis.xlsx
        if default_path.exists():
            xls = pd.ExcelFile(default_path)
            sheet = "all" if "all" in xls.sheet_names else xls.sheet_names[0]
            df = pd.read_excel(default_path, sheet_name=sheet)
        else:
            raise FileNotFoundError("Veri bulunamadı. Dosya yükleyin ya da 0analysis.xlsx aynı klasöre koyun.")
    else:
        name = filename_hint or (getattr(file, "name", None) or "")
        if str(name).lower().endswith(".csv"):
            df = pd.read_csv(file)
        elif str(name).lower().endswith(".xlsx"):
            try:
                df = pd.read_excel(file, sheet_name="all")
            except Exception:
                xls = pd.ExcelFile(file)
                df = pd.read_excel(file, sheet_name=xls.sheet_names[0])
        else:
            # İçeriğe bak: önce CSV dene, olmazsa Excel
            try:
                df = pd.read_csv(file)
            except Exception:
                df = pd.read_excel(file)
    return df

try:
    df = load_data(uploaded, getattr(uploaded, "name", None))
except Exception as e:
    st.error(f"Veri yüklenemedi: {e}")
    st.stop()

# ---------- Prep ----------
# Zaman
df["Time"] = pd.to_datetime(df["Time"])
df = df.sort_values("Time").reset_index(drop=True)
df["Year"] = df["Time"].dt.year

# Finansal kolonlar (milyon → milyar)
value_cols = [c for c in df.columns if c not in ["Time","Year"]]
for c in value_cols:
    df[c] = pd.to_numeric(df[c], errors="coerce") / 1000.0

# Kontroller
need_cols = ["AllCredit","DebtSecurities","Loans"]
for nc in need_cols:
    if nc not in df.columns:
        st.error(f"Kolon eksik: {nc}")
        st.stop()

# ---------- Helpers ----------
def add_shading(fig):
    crisis = [
        (pd.to_datetime("2007-12-01"), pd.to_datetime("2009-06-01"), "Financial Crisis"),
        (pd.to_datetime("2020-02-01"), pd.to_datetime("2020-04-01"), "COVID-19"),
    ]
    for x0, x1, label in crisis:
        fig.add_vrect(
            x0=x0, x1=x1,
            fillcolor="red", opacity=0.10, line_width=0,
            annotation_text=label, annotation_position="top left"
        )
    x0 = pd.to_datetime("2022-06-01")
    x1 = pd.to_datetime(df["Time"].max())
    fig.add_vrect(
        x0=x0, x1=x1,
        fillcolor="orange", opacity=0.08, line_width=0,
        annotation_text="Fed Tightening", annotation_position="top left"
    )

def yaxis_k(fig, tickvals=None):
    if tickvals is not None:
        fig.update_yaxes(tickformat="~s",
                         tickvals=tickvals,
                         ticktext=[f"{int(v/1000)}k" for v in tickvals],
                         showexponent="none")
    else:
        fig.update_yaxes(tickformat="~s", showexponent="none")

def title_range(prefix):
    return f"<b>{prefix} ({df['Time'].min().year}–{df['Time'].max().year})</b>"

# ---------- Charts ----------
def total_credit():
    fig = go.Figure()
    fig.add_trace(go.Scatter(
        x=df["Time"], y=df["AllCredit"],
        mode="lines", name="Total Credit", line=dict(width=3)
    ))
    add_shading(fig)
    fig.update_layout(
        title=dict(text=title_range("Total Eurodollar Credit Market Evolution"), x=0.5),
        xaxis_title="Time Period",
        yaxis_title="USD Billions",
        height=520, showlegend=False
    )
    yaxis_k(fig)
    st.plotly_chart(fig, use_container_width=True)

    yoy = df.copy()
    yoy["YoY_AllCredit"] = yoy["AllCredit"].pct_change(4)*100
    fig2 = go.Figure()
    fig2.add_trace(go.Bar(
        x=yoy["Time"], y=yoy["YoY_AllCredit"],
        marker_color=np.where(yoy["YoY_AllCredit"]>=0, "green", "red"),
        name="YoY"
    ))
    fig2.add_hline(y=0, line_dash="dash", line_color="black", opacity=0.5)
    fig2.update_layout(
        title=dict(text=title_range("Total Credit — Year-over-Year (YoY)"), x=0.5),
        xaxis_title="Time Period",
        yaxis_title="YoY (%)",
        height=420, showlegend=False
    )
    st.plotly_chart(fig2, use_container_width=True)

def debt_securities():
    fig = go.Figure()
    fig.add_trace(go.Scatter(
        x=df["Time"], y=df["DebtSecurities"],
        mode="lines", name="Debt Securities", line=dict(width=3)
    ))
    add_shading(fig)
    fig.update_layout(
        title=dict(text=title_range("Eurodollar Debt Securities Market Evolution"), x=0.5),
        xaxis_title="Time Period",
        yaxis_title="USD Billions",
        height=520, showlegend=False
    )
    yaxis_k(fig)
    st.plotly_chart(fig, use_container_width=True)

    yoy = df.copy()
    yoy["YoY_Debt"] = yoy["DebtSecurities"].pct_change(4)*100
    fig2 = go.Figure()
    fig2.add_trace(go.Bar(
        x=yoy["Time"], y=yoy["YoY_Debt"],
        marker_color=np.where(yoy["YoY_Debt"]>=0, "green", "red"),
        name="YoY"
    ))
    fig2.add_hline(y=0, line_dash="dash", line_color="black", opacity=0.5)
    fig2.update_layout(
        title=dict(text=title_range("Debt Securities — Year-over-Year (YoY)"), x=0.5),
        xaxis_title="Time Period",
        yaxis_title="YoY (%)",
        height=420, showlegend=False
    )
    st.plotly_chart(fig2, use_container_width=True)

def loans():
    fig = go.Figure()
    fig.add_trace(go.Scatter(
        x=df["Time"], y=df["Loans"],
        mode="lines", name="Loans", line=dict(width=3)
    ))
    add_shading(fig)
    fig.update_layout(
        title=dict(text=title_range("Eurodollar Loans Market Evolution"), x=0.5),
        xaxis_title="Time Period",
        yaxis_title="USD Billions",
        height=520, showlegend=False
    )
    yaxis_k(fig)
    st.plotly_chart(fig, use_container_width=True)

    yoy = df.copy()
    yoy["YoY_Loans"] = yoy["Loans"].pct_change(4)*100
    fig2 = go.Figure()
    fig2.add_trace(go.Bar(
        x=yoy["Time"], y=yoy["YoY_Loans"],
        marker_color=np.where(yoy["YoY_Loans"]>=0, "green", "red"),
        name="YoY"
    ))
    fig2.add_hline(y=0, line_dash="dash", line_color="black", opacity=0.5)
    fig2.update_layout(
        title=dict(text=title_range("Loans — Year-over-Year (YoY)"), x=0.5),
        xaxis_title="Time Period",
        yaxis_title="YoY (%)",
        height=420, showlegend=False
    )
    st.plotly_chart(fig2, use_container_width=True)

def comparison():
    fig = go.Figure()
    fig.add_trace(go.Scatter(x=df["Time"], y=df["AllCredit"], mode="lines", name="Total Credit", line=dict(width=3)))
    fig.add_trace(go.Scatter(x=df["Time"], y=df["DebtSecurities"], mode="lines", name="Debt Securities", line=dict(width=3)))
    fig.add_trace(go.Scatter(x=df["Time"], y=df["Loans"], mode="lines", name="Loans", line=dict(width=3)))
    add_shading(fig)
    fig.update_layout(
        title=dict(text=title_range("Total vs Debt Securities vs Loans"), x=0.5),
        xaxis_title="Time Period",
        yaxis_title="USD Billions",
        height=620,
        legend=dict(orientation="h", yanchor="bottom", y=1.02, xanchor="left", x=0)
    )
    # Sadece 2k ve 5k etiket
    fig.update_yaxes(tickformat="~s",
                     tickvals=[2000, 5000],
                     ticktext=[f"{int(v/1000)}k" for v in [2000,5000]],
                     showexponent="none")
    st.plotly_chart(fig, use_container_width=True)

# ---------- Layout ----------
tab1, tab2, tab3, tab4 = st.tabs(["Total Credit", "Debt Securities", "Loans", "Comparison"])

with tab1:
    total_credit()
with tab2:
    debt_securities()
with tab3:
    loans()
with tab4:
    comparison()

# küçük özet
st.caption(f"Veri aralığı: {df['Time'].min().date()} → {df['Time'].max().date()} • Satır: {len(df)} • Kolonlar: {', '.join(df.columns)}")

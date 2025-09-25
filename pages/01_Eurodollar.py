import streamlit as st
import pandas as pd
import numpy as np
from pathlib import Path
import plotly.graph_objects as go

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
        [data-testid="stSidebarNav"] {display: none;}
        section[data-testid="stSidebar"][aria-expanded="true"]{display: none;}
    </style>
    """, unsafe_allow_html=True)

# ---------- Veri yükleme ----------
st.sidebar.header("Veri Kaynağı")
st.title("Eurodollar Market Evolution — 2000-2025")
uploaded = st.sidebar.file_uploader("CSV veya Excel (.csv, .xlsx) yükleyin", type=["csv","xlsx"])

default_path = Path("assets/thumbs/0analysis.xlsx")

@st.cache_data(show_spinner=False)
def load_data(file, filename_hint=None):
    if file is None:
        if default_path.exists():
            xls = pd.ExcelFile(default_path)
            sheet = "all" if "all" in xls.sheet_names else xls.sheet_names[0]
            df = pd.read_excel(default_path, sheet_name=sheet)
        else:
            raise FileNotFoundError("Veri bulunamadı.")
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

# ---------- Hazırlık ----------
df["Time"] = pd.to_datetime(df["Time"])
df = df.sort_values("Time").reset_index(drop=True)
df["Year"] = df["Time"].dt.year

value_cols = [c for c in df.columns if c not in ["Time","Year"]]
for c in value_cols:
    df[c] = pd.to_numeric(df[c], errors="coerce") / 1000.0  # milyon → milyar

# ---------- Helpers ----------
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


# ---------- Classic Charts ----------
def total_credit():
    fig = go.Figure()
    fig.add_trace(go.Scatter(x=df["Time"], y=df["AllCredit"], mode="lines",
                             line=dict(width=3, color="#e74c3c")))
    add_shading(fig)
    fig.update_layout(title=dict(text=title_range("Total Eurodollar Credit"), x=0.5),
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
    fig.add_trace(go.Scatter(x=df["Time"], y=df["Loans"], mode="lines",
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
    fig.add_trace(go.Scatter(x=df["Time"], y=df["AllCredit"], mode="lines", name="Total", line=dict(width=3, color="#e74c3c")))
    fig.add_trace(go.Scatter(x=df["Time"], y=df["DebtSecurities"], mode="lines", name="Debt", line=dict(width=3, color="#8e44ad")))
    fig.add_trace(go.Scatter(x=df["Time"], y=df["Loans"], mode="lines", name="Loans", line=dict(width=3, color="#f39c12")))
    add_shading(fig); yaxis_k(fig)
    fig.update_layout(title=dict(text=title_range("Comparison"), x=0.5),
                      height=620, legend=dict(orientation="h"))
    st.plotly_chart(fig, use_container_width=True)

# ---------- Advanced vs Emerging ----------
def adv_vs_eme():
    tabA1, tabA2, tabA3, tabA4 = st.tabs([
        "Advanced Debt vs Loans", "Emerging Debt vs Loans", "Debt Comparison", "Loans Comparison"
    ])

    with tabA1:
        fig = go.Figure()
        fig.add_trace(go.Scatter(x=df["Time"], y=df["AdvancedDebtSecurities"], mode="lines",
                                 name="Adv Debt", line=dict(width=3, color="#8e44ad")))
        fig.add_trace(go.Scatter(x=df["Time"], y=df["AdvancedLoans"], mode="lines",
                                 name="Adv Loans", line=dict(width=3, color="#f39c12")))
        add_shading(fig); yaxis_k(fig)
        fig.update_layout(
    title=dict(text=title_range("Advanced Securities Loans"), x=0.5),
    height=520,
    legend=dict(
        orientation="h",
        yanchor="top",
        y=-0.25,   # alta indir
        xanchor="center",
        x=0.5
    )
)

        st.plotly_chart(fig, use_container_width=True)

        yoy = df.copy()
        yoy["DebtYoY"] = yoy["AdvancedDebtSecurities"].pct_change(4)*100
        yoy["LoansYoY"] = yoy["AdvancedLoans"].pct_change(4)*100
        fig2 = go.Figure()
        fig2.add_trace(go.Bar(x=yoy["Time"], y=yoy["DebtYoY"], name="Debt YoY", marker_color="#8e44ad"))
        fig2.add_trace(go.Bar(x=yoy["Time"], y=yoy["LoansYoY"], name="Loans YoY", marker_color="#f39c12"))
        fig2.add_hline(y=0, line_dash="dash", line_color="black")
        fig2.update_layout(
            title=dict(text="Advanced: YoY Growth", x=0.5),
            barmode="group",
            height=420,
            legend=dict(
                orientation="h",
                yanchor="top",
                y=-0.25,
                xanchor="center",
                x=0.5
            )
        )
        st.plotly_chart(fig2, use_container_width=True)

    with tabA2:
        fig = go.Figure()
        fig.add_trace(go.Scatter(x=df["Time"], y=df["EmeDebt"], mode="lines",
                                 name="Eme Debt", line=dict(width=3, color="#27ae60")))
        fig.add_trace(go.Scatter(x=df["Time"], y=df["EmeBankLoans"], mode="lines",
                                 name="Eme Loans", line=dict(width=3, color="#e74c3c")))
        add_shading(fig); yaxis_k(fig)
        fig.update_layout(
    title=dict(text=title_range("EME Securities Loans"), x=0.5),
    height=520,
    legend=dict(
        orientation="h",
        yanchor="top",
        y=-0.25,   # alta indir
        xanchor="center",
        x=0.5
    )
)

        st.plotly_chart(fig, use_container_width=True)

        yoy = df.copy()
        yoy["DebtYoY"] = yoy["EmeDebt"].pct_change(4)*100
        yoy["LoansYoY"] = yoy["EmeBankLoans"].pct_change(4)*100
        fig2 = go.Figure()
        fig2.add_trace(go.Bar(x=yoy["Time"], y=yoy["DebtYoY"], name="Debt YoY", marker_color="#27ae60"))
        fig2.add_trace(go.Bar(x=yoy["Time"], y=yoy["LoansYoY"], name="Loans YoY", marker_color="#e74c3c"))
        fig2.add_hline(y=0, line_dash="dash", line_color="black")
        fig2.update_layout(
            title=dict(text="Emerging: YoY Growth", x=0.5),
            barmode="group",
            height=420,
            legend=dict(
                orientation="h",
                yanchor="top",
                y=-0.25,
                xanchor="center",
                x=0.5
            )
        )
        st.plotly_chart(fig2, use_container_width=True)

    with tabA3:
        fig = go.Figure()
        fig.add_trace(go.Scatter(x=df["Time"], y=df["AdvancedDebtSecurities"], mode="lines",
                                 name="Advanced", line=dict(width=3, color="#8e44ad")))
        fig.add_trace(go.Scatter(x=df["Time"], y=df["EmeDebt"], mode="lines",
                                 name="Emerging", line=dict(width=3, color="#27ae60")))
        add_shading(fig); yaxis_k(fig)
        fig.update_layout(
    title=dict(text=title_range("Securities: Adv vs Eme"), x=0.5),
    height=520,
    legend=dict(
        orientation="h",
        yanchor="top",
        y=-0.25,   # alta indir
        xanchor="center",
        x=0.5
    )
)

        st.plotly_chart(fig, use_container_width=True)

        yoy = df.copy()
        yoy["AdvYoY"] = yoy["AdvancedDebtSecurities"].pct_change(4)*100
        yoy["EmeYoY"] = yoy["EmeDebt"].pct_change(4)*100
        fig2 = go.Figure()
        fig2.add_trace(go.Bar(x=yoy["Time"], y=yoy["AdvYoY"], name="Adv YoY", marker_color="#8e44ad"))
        fig2.add_trace(go.Bar(x=yoy["Time"], y=yoy["EmeYoY"], name="Eme YoY", marker_color="#27ae60"))
        fig2.add_hline(y=0, line_dash="dash", line_color="black")
        fig2.update_layout(
            title=dict(text="Debt: YoY Growth", x=0.5),
            barmode="group",
            height=420,
            legend=dict(
                orientation="h",
                yanchor="top",
                y=-0.25,
                xanchor="center",
                x=0.5
            )
        )
        st.plotly_chart(fig2, use_container_width=True)

    with tabA4:
        fig = go.Figure()
        fig.add_trace(go.Scatter(x=df["Time"], y=df["AdvancedLoans"], mode="lines",
                                 name="Advanced", line=dict(width=3, color="#f39c12")))
        fig.add_trace(go.Scatter(x=df["Time"], y=df["EmeBankLoans"], mode="lines",
                                 name="Emerging", line=dict(width=3, color="#e74c3c")))
        add_shading(fig); yaxis_k(fig)
        fig.update_layout(
    title=dict(text=title_range("Loans: Adv vs Eme"), x=0.5),
    height=520,
    legend=dict(
        orientation="h",
        yanchor="top",
        y=-0.25,   # alta indir
        xanchor="center",
        x=0.5
    )
)

        st.plotly_chart(fig, use_container_width=True)

        yoy = df.copy()
        yoy["AdvYoY"] = yoy["AdvancedLoans"].pct_change(4)*100
        yoy["EmeYoY"] = yoy["EmeBankLoans"].pct_change(4)*100
        fig2 = go.Figure()
        fig2.add_trace(go.Bar(x=yoy["Time"], y=yoy["AdvYoY"], name="Adv YoY", marker_color="#f39c12"))
        fig2.add_trace(go.Bar(x=yoy["Time"], y=yoy["EmeYoY"], name="Eme YoY", marker_color="#e74c3c"))
        fig2.add_hline(y=0, line_dash="dash", line_color="black")
        fig2.update_layout(
            title=dict(text="Loans: YoY Growth", x=0.5),
            barmode="group",
            height=420,
            legend=dict(
                orientation="h",
                yanchor="top",
                y=-0.25,
                xanchor="center",
                x=0.5
            )
        )
        st.plotly_chart(fig2, use_container_width=True)


# ---------- Emerging Area (regional totals only) ----------
REGIONS = [
    ("Africa & Middle East", "AfricaMiddleEast", "#e74c3c"),
    ("Emerging Asia",        "EmergingAsia",      "#8e44ad"),
    ("Emerging Europe",      "EmergingEurope",    "#27ae60"),
    ("Latin America",        "LatinAmerica",      "#f39c12"),
]

def emerging_area():
    tabs = st.tabs([r[0] for r in REGIONS])

    for (tab, (title, col, color)) in zip(tabs, REGIONS):
        with tab:
            if col not in df.columns or df[col].isna().all():
                st.info(f"ℹ️ {title} verisi bulunamadı (kolon: {col}).")
                continue

            # Üst: seviye (line)
            fig = go.Figure()
            fig.add_trace(go.Scatter(
                x=df["Time"], y=df[col], mode="lines", name=title,
                line=dict(width=4, color=color)
            ))
            add_shading(fig); yaxis_k(fig)
            fig.update_layout(
                title=dict(text=title_range(f"{title} — Eurodollar Total"), x=0.5),
                height=520, legend=legend_bottom()
            )
            st.plotly_chart(fig, use_container_width=True)

            # Alt: YoY (4Q)
            yoy = df[col].pct_change(4)*100
            fig2 = go.Figure()
            fig2.add_trace(go.Bar(x=df["Time"], y=yoy, name=f"{title} YoY", marker_color=color, opacity=0.85))
            fig2.add_hline(y=0, line_dash="dash", line_color="black", opacity=0.6)
            fig2.update_layout(
                title=dict(text=f"{title}: YoY Growth (%)", x=0.5),
                barmode="group", height=420, legend=legend_bottom()
            )
            st.plotly_chart(fig2, use_container_width=True)
# ---------- Emerging Countries (multi-select) ----------
COUNTRIES = ['SaudiArabia','SouthAfrica','China','Taipei','India','Indonesia','Korea','Malaysia',
             'Russia','Turkey','Argentina','Brazil','Chile','Mexico']

COLOR_CYCLE = ["#e74c3c", "#f39c12", "#8e44ad", "#27ae60", "#d35400", "#c0392b",
               "#9b59b6", "#16a085", "#7f8c8d", "#95a5a6", "#2ecc71", "#e67e22",
               "#bdc3c7", "#34495e"]

def emerging_countries():
    available = [c for c in COUNTRIES if c in df.columns and not df[c].isna().all()]
    if not available:
        st.info("ℹ️ Ülke kolonları bulunamadı.")
        return

    picked = st.multiselect("Select countries", available, default=available[:4])
    if not picked:
        st.warning("En az bir ülke seçin.")
        return

    # Üst: seçili ülkeler seviye (tek grafikte)
    fig = go.Figure()
    for i, c in enumerate(picked):
        fig.add_trace(go.Scatter(
            x=df["Time"], y=pd.to_numeric(df[c], errors="coerce"),
            mode="lines", name=c, line=dict(width=3, color=COLOR_CYCLE[i % len(COLOR_CYCLE)])
        ))
    add_shading(fig); yaxis_k(fig)
    fig.update_layout(
        title=dict(text=title_range("Emerging Countries — Eurodollar Totals"), x=0.5),
        height=520, legend=legend_bottom()
    )
    st.plotly_chart(fig, use_container_width=True)

    # Alt: YoY grouped bar
    fig2 = go.Figure()
    for i, c in enumerate(picked):
        yoy = pd.to_numeric(df[c], errors="coerce").pct_change(4)*100
        fig2.add_trace(go.Bar(
            x=df["Time"], y=yoy, name=f"{c} YoY",
            marker_color=COLOR_CYCLE[i % len(COLOR_CYCLE)], opacity=0.85
        ))
    fig2.add_hline(y=0, line_dash="dash", line_color="black", opacity=0.6)
    fig2.update_layout(
        title=dict(text="Emerging Countries: YoY Growth (%)", x=0.5),
        barmode="group", height=420, legend=legend_bottom()
    )
    st.plotly_chart(fig2, use_container_width=True)



# ---------- Layout ----------
# ---------- Layout ----------
tab1, tab2, tab3, tab4, tab5, tab6, tab7 = st.tabs([
    "Total Credit", "Debt Securities", "Loans", "Comparison",
    "Advanced vs Emerging", "Emerging Area", "Emerging Countries"
])

with tab1: total_credit()
with tab2: debt_securities()
with tab3: loans()
with tab4: comparison()
with tab5: adv_vs_eme()
with tab6: emerging_area()
with tab7: emerging_countries()


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

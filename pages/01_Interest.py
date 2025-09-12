# streamlit_app.py
# NY Fed Reference Rates Dashboard (EFFR, OBFR, SOFR, BGCR, TGCR)
# Gerekenler: pip install streamlit pandas requests altair python-dateutil

import io
import requests
import pandas as pd
import altair as alt
import streamlit as st
from datetime import datetime, date, timedelta

st.set_page_config(page_title="NY Fed Reference Rates", layout="wide")

# -----------------------
# Yardımcı fonksiyonlar
# -----------------------
API_BASE = "https://markets.newyorkfed.org/api/rates"

SPECS = {
    # unsecured
    "EFFR": dict(group="unsecured", code="effr"),
    "OBFR": dict(group="unsecured", code="obfr"),
    # secured
    "SOFR": dict(group="secured",   code="sofr"),
    "BGCR": dict(group="secured",   code="bgcr"),
    "TGCR": dict(group="secured",   code="tgcr"),
}

def fetch_rates_csv(rate_name: str, last_n: int = 500) -> pd.DataFrame:
    """
    NY Fed Markets API'den sadece tarih ve rate sütunlarını çek.
    """
    spec = SPECS[rate_name]
    url = f"{API_BASE}/{spec['group']}/{spec['code']}/last/{last_n}.csv"
    r = requests.get(url, timeout=20)
    r.raise_for_status()
    df = pd.read_csv(io.StringIO(r.text))
    
    # Kolon isimlerini normalize et
    cols = [c.strip().lower() for c in df.columns]
    df.columns = cols
    
    # Beklenen kolonlar
    if "effective date" in cols:
        date_col = "effective date"
    elif "date" in cols:
        date_col = "date"
    else:
        raise ValueError(f"{rate_name}: Tarih kolonu bulunamadı. Kolonlar: {cols}")
    
    if "rate (%)" in cols:
        rate_col = "rate (%)"
    elif "rate" in cols:
        rate_col = "rate"
    else:
        raise ValueError(f"{rate_name}: Rate kolonu bulunamadı. Kolonlar: {cols}")
    
    df = df[[date_col, rate_col]].copy()
    df.columns = ["date", "rate"]
    df["date"] = pd.to_datetime(df["date"]).dt.date
    df["series"] = rate_name
    df = df.sort_values("date")
    return df


def yoy_change(df: pd.DataFrame) -> float | None:
    """Son gözlem ile bir yıl önceye en yakın iş günü karşılaştırması (<= 7 gün tolerans)."""
    if df.empty:
        return None
    last_date = df["date"].max()
    target = last_date - timedelta(days=365)
    # en yakın ama target'tan küçük ya da eşit tarih
    past = df[df["date"] <= target]
    if past.empty:
        return None
    past_val = past.iloc[-1]["rate"]
    last_val = df[df["date"] == last_date].iloc[0]["rate"]
    return last_val - past_val

def ytd_change(df: pd.DataFrame, ytd_start: date) -> float | None:
    """Yılbaşı (2025-01-01) veya belirtilen tarihten bugüne fark."""
    ref = df[df["date"] >= ytd_start]
    if ref.empty:
        return None
    first_val = ref.iloc[0]["rate"]
    last_val = df.iloc[-1]["rate"]
    return last_val - first_val

def format_bps(x: float | None) -> str:
    if x is None:
        return "—"
    return f"{x:.2f} pp"  # yüzde puan (percentage points)

# -----------------------
# Veri çekimi
# -----------------------
st.markdown("### 🏦 NY Fed Reference Rates Dashboard — EFFR · OBFR · SOFR · BGCR · TGCR")

with st.spinner("Veriler çekiliyor..."):
    frames = []
    errors = []
    for name in SPECS.keys():
        try:
            # 500 gün: YoY ve yıllık grafik için güvenli aralık
            frames.append(fetch_rates_csv(name, last_n=500))
        except Exception as e:
            errors.append(f"{name}: {e}")
    if errors:
        st.warning("Bazı seriler çekilemedi:\n\n- " + "\n- ".join(errors))
    data = pd.concat(frames, ignore_index=True) if frames else pd.DataFrame(columns=["date","rate","series"])

if data.empty:
    st.stop()

# Son gün, YoY, YTD (01.01.2025)
today_last_dates = data.groupby("series")["date"].max()
latest_rows = []
ytd_anchor = date(2025, 1, 1)

for s in SPECS.keys():
    df_s = data[data["series"] == s].sort_values("date")
    last_date = df_s["date"].max()
    last_rate = df_s[df_s["date"] == last_date].iloc[0]["rate"]
    latest_rows.append({
        "Seri": s,
        "Son Gün": last_date.strftime("%Y-%m-%d"),
        "Son Değer (%)": round(last_rate, 4),
        "YoY (pp)": yoy_change(df_s),
        "01.01.2025'ten bu yana (pp)": ytd_change(df_s, ytd_anchor),
    })

latest_df = pd.DataFrame(latest_rows)
latest_df["YoY (pp)"] = latest_df["YoY (pp)"].map(lambda x: None if pd.isna(x) else x)
latest_df["01.01.2025'ten bu yana (pp)"] = latest_df["01.01.2025'ten bu yana (pp)"].map(lambda x: None if pd.isna(x) else x)

# -----------------------
# Üst Özet Kutuları
# -----------------------
st.markdown("#### 📌 Özet — Son Gün • Yıla Göre (YoY) • 01.01.2025'ten Bu Yana")
st.dataframe(
    latest_df.style.format({
        "Son Değer (%)": "{:.4f}",
        "YoY (pp)": lambda v: "—" if v is None else f"{v:.2f}",
        "01.01.2025'ten bu yana (pp)": lambda v: "—" if v is None else f"{v:.2f}",
    }),
    use_container_width=True
)

# -----------------------
# Görselleştirme Ayarları
# -----------------------
st.markdown("### 📈 Grafikler")
colA, colB = st.columns([1,1])

with colA:
    st.markdown("**Çizim modu**")
    draw_mode = st.radio(
        "Seriler birbirine çok yakın olduğu için farklı modlar sunduk:",
        options=["Düz oran (%)", "SOFR'a göre yayılım (pp)"],
        index=0,
        horizontal=True,
        label_visibility="collapsed"
    )

with colB:
    st.markdown("**Görünüm**")
    show_points = st.checkbox("Noktaları göster", value=False)

# Grafik verileri
pivot = data.pivot(index="date", columns="series", values="rate").sort_index()

if draw_mode == "SOFR'a göre yayılım (pp)":
    if "SOFR" in pivot.columns:
        pivot = pivot.apply(lambda col: col - pivot["SOFR"])
    else:
        st.info("SOFR bulunamadı, düz oran modu kullanılıyor.")
        draw_mode = "Düz oran (%)"

def to_long(df: pd.DataFrame) -> pd.DataFrame:
    out = df.reset_index().melt(id_vars="date", var_name="series", value_name="value").dropna()
    out["date"] = pd.to_datetime(out["date"])
    return out

# Son 7 gün & Son 365 gün
last_date_all = pivot.index.max()
last_7 = pivot[pivot.index >= last_date_all - timedelta(days=7)]
last_365 = pivot[pivot.index >= last_date_all - timedelta(days=365)]

def make_line_chart(df_long: pd.DataFrame, title: str):
    tooltip = [
        alt.Tooltip("date:T", title="Tarih"),
        alt.Tooltip("series:N", title="Seri"),
        alt.Tooltip("value:Q", title=("Oran (%)" if draw_mode=="Düz oran (%)" else "Yayılım (pp)"), format=".4f"),
    ]
    line = alt.Chart(df_long).mark_line(point=show_points).encode(
        x=alt.X("date:T", title="Tarih"),
        y=alt.Y("value:Q", title=("Oran (%)" if draw_mode=="Düz oran (%)" else "Yayılım (pp)")),
        color=alt.Color("series:N", title="Seri"),
        tooltip=tooltip
    ).properties(height=320, title=title)
    return line

st.markdown("#### ⏱️ Son 1 Hafta")
st.altair_chart(make_line_chart(to_long(last_7), "Son 7 Gün"), use_container_width=True)

st.markdown("#### 📅 Son 1 Yıl")
st.altair_chart(make_line_chart(to_long(last_365), "Son 365 Gün"), use_container_width=True)

# -----------------------
# Dipnot & Kaynak
# -----------------------
with st.expander("Kaynak & Notlar"):
    st.markdown(
        """
- Kaynak: Federal Reserve Bank of New York — Markets Data APIs (Reference Rates: EFFR, OBFR, SOFR, BGCR, TGCR).
- API örnek uç noktaları:
  - `.../api/rates/unsecured/effr/last/365.csv`
  - `.../api/rates/unsecured/obfr/last/365.csv`
  - `.../api/rates/secured/sofr/last/365.csv`
  - `.../api/rates/secured/bgcr/last/365.csv`
  - `.../api/rates/secured/tgcr/last/365.csv`
- YoY: Son gözlem ile bir yıl önceye en yakın iş günü karşılaştırması.
- 01.01.2025'ten bu yana: 2025-01-01 (dahil) sonrası ilk gözlem ile son gözlem farkı.
        """
    )

import streamlit as st
import pandas as pd
import requests
from bs4 import BeautifulSoup

URL = "https://www.investing.com/rates-bonds/usa-government-bonds"

@st.cache_data(ttl=300)
def fetch_investing_curve():
    headers = {
        "User-Agent": "Mozilla/5.0",
        "Accept-Language": "en-US,en;q=0.9",
    }
    html = requests.get(URL, headers=headers, timeout=20).text

    # Sayfadaki tabloları yakala (genelde ilk/ikinci tablo iş görür)
    tables = pd.read_html(html)
    # Bu sayfada “Name Yield …” başlıklı tabloyu seç
    df = next(t for t in tables if "Yield" in t.columns and "Name" in t.columns)

    # Name -> maturity label (U.S. 1M, U.S. 2Y ...)
    df = df[["Name", "Yield"]].copy()
    df["Yield"] = pd.to_numeric(df["Yield"], errors="coerce")
    df = df.dropna()

    # Maturity sırası (grafik düzeni için)
    order = ["U.S. 6M","U.S. 1Y","U.S. 2Y","U.S. 3Y","U.S. 5Y","U.S. 7Y","U.S. 10Y","U.S. 20Y","U.S. 30Y"]
    df = df[df["Name"].isin(order)]
    df["Name"] = pd.Categorical(df["Name"], categories=order, ordered=True)
    df = df.sort_values("Name")
    return df

st.title("US Treasury Yield Curve (from Investing table)")
df = fetch_investing_curve()
st.dataframe(df, use_container_width=True)

st.line_chart(data=df.set_index("Name")["Yield"])

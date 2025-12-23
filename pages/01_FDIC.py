# -----------------------------------------------------------------------------
# FDIC Reserve Dashboard  |  Reserves Page
# -----------------------------------------------------------------------------
import streamlit as st
import pandas as pd
import numpy as np
import requests
import altair as alt
import time
import re


# ---------------------------- Page config -----------------------------
st.set_page_config(page_title="FDIC Reserve Dashboard ", layout="wide")

# ---------------------------- Top nav (your template) -----------------
cols = st.columns(9)
with cols[0]:
    st.page_link("streamlit_app.py", label="🏠 Home")
with cols[1]:
    st.page_link("pages/01_Reserves.py", label="🌍 Reserves")
with cols[2]:
    st.page_link("pages/01_Repo.py", label="♻️ Repo")
with cols[3]:
    st.page_link("pages/01_Repo2.py", label="♻️ Repo 2")
with cols[4]:
    st.page_link("pages/01_TGA.py", label="🌐 TGA")
with cols[5]:
    st.page_link("pages/01_PublicBalance.py", label="💹 Public Balance")
with cols[6]:
    st.page_link("pages/01_Interest.py", label="✈️ Reference Rates")
with cols[7]:
    st.page_link("pages/01_Desk.py", label="📡 Desk")
with cols[8]:
    st.page_link("pages/01_Eurodollar.py", label="💡 Eurodollar")

st.markdown(
    """
<style>
    [data-testid="stSidebarNav"] {display: none;}
    section[data-testid="stSidebar"][aria-expanded="true"]{display: none;}
</style>
""",
    unsafe_allow_html=True,
)

# -----------------------------------------------------------------------------
# FDIC helpers
# -----------------------------------------------------------------------------
BASE_URL = "https://banks.data.fdic.gov/api"

def fdic_get(endpoint: str, params: dict) -> dict:
    """Call FDIC BankFind API and return JSON (or raise with raw error)."""
    url = f"{BASE_URL}/{endpoint}"
    r = requests.get(url, params=params, timeout=60)
    if r.status_code != 200:
        raise RuntimeError(f"STATUS: {r.status_code}\nRAW RESPONSE:\n{r.text}")
    return r.json()

def fetch_all(endpoint: str, params: dict, sleep_s: float = 0.08) -> pd.DataFrame:
    """
    Fetch all rows using offset+limit pagination.
    FDIC returns rows under json['data'][i]['data'].
    """
    limit = int(params.get("limit", 10000))
    offset = 0
    rows = []

    while True:
        p = dict(params)
        p["offset"] = offset
        js = fdic_get(endpoint, p)

        batch = js.get("data", [])
        if not batch:
            break

        rows.extend([x.get("data", {}) for x in batch])

        if len(batch) < limit:
            break

        offset += limit
        time.sleep(sleep_s)

    return pd.DataFrame(rows)

@st.cache_data(ttl=6 * 60 * 60, show_spinner=False)
def load_reserves(rep_dte: str) -> pd.DataFrame:
    """
    Returns bank-level table with:
    CERT, NAME, REPDTE, CHFRB, CHBALI, reserve_used, reserve_source
    (This is used for calculations; we won't display the full bank table.)
    """
    # 1) Institution names (ACTIVE banks)
    inst_params = {
        "filters": "ACTIVE:1",
        "fields": "CERT,NAME",
        "limit": 10000,
        "format": "json",
    }
    df_inst = fetch_all("institutions", inst_params)
    if df_inst.empty:
        return pd.DataFrame(columns=["CERT","NAME","REPDTE","CHFRB","CHBALI","reserve_used","reserve_source"])

    df_inst["CERT"] = pd.to_numeric(df_inst["CERT"], errors="coerce")

    # 2) Financials: CHFRB first-choice; if missing, use CHBALI as fallback
    fin_params = {
        "filters": f"ACTIVE:1 AND REPDTE:{rep_dte}",
        "fields": "CERT,REPDTE,CHFRB,CHBALI",
        "limit": 10000,
        "format": "json",
    }
    df_fin = fetch_all("financials", fin_params)
    if df_fin.empty:
        return pd.DataFrame(columns=["CERT","NAME","REPDTE","CHFRB","CHBALI","reserve_used","reserve_source"])

    df_fin["CERT"] = pd.to_numeric(df_fin["CERT"], errors="coerce")
    df_fin["CHFRB"] = pd.to_numeric(df_fin.get("CHFRB"), errors="coerce")   # keep NaN if missing
    df_fin["CHBALI"] = pd.to_numeric(df_fin.get("CHBALI"), errors="coerce") # keep NaN if missing

    # 3) Merge bank names onto financials
    df = df_fin.merge(df_inst[["CERT", "NAME"]], on="CERT", how="left")

    # 4) Reserve logic:
    # - Use CHFRB when available
    # - Otherwise use CHBALI
    df["reserve_used"] = df["CHFRB"].where(df["CHFRB"].notna(), df["CHBALI"])
    df["reserve_source"] = np.where(df["CHFRB"].notna(), "CHFRB", "CHBALI")

    # If BOTH are missing (rare), treat as 0
    df["reserve_used"] = pd.to_numeric(df["reserve_used"], errors="coerce").fillna(0)

    out = df[["CERT", "NAME", "REPDTE", "CHFRB", "CHBALI", "reserve_used", "reserve_source"]].copy()
    out.sort_values("reserve_used", ascending=False, inplace=True)
    out.reset_index(drop=True, inplace=True)
    return out

# -----------------------------------------------------------------------------
# Fed Table 4.30: Foreign bank branches reserves
# -----------------------------------------------------------------------------
FED_TABLE_430_URL = "https://www.federalreserve.gov/data/assetliab/current.htm"

@st.cache_data(ttl=6 * 60 * 60, show_spinner=False)
def fetch_foreign_bank_branches_reserves_musd() -> float:
    html = requests.get(
        "https://www.federalreserve.gov/data/assetliab/current.htm",
        timeout=30
    ).text

    pattern = (
        r'Balances with Federal Reserve Banks'   # satır adı
        r'.{0,500}?'                              # aradaki her şey (satır kırıkları dahil)
        r'<td[^>]*class="shadedata"[^>]*>'        # ilgili hücre
        r'\s*([\d,]+)\s*'                         # SAYI
        r'</td>'
    )

    m = re.search(pattern, html, re.I | re.S)
    if not m:
        raise RuntimeError("Table 4.30 value not found in HTML")

    return float(m.group(1).replace(",", ""))



# -----------------------------------------------------------------------------
# UI
# -----------------------------------------------------------------------------
st.title("🌍 Reserves (FDIC Call Reports)")
st.caption("FDIC reserve proxy: **CHFRB** (Balances due from Federal Reserve Banks). If missing, fallback to **CHBALI** (Interest-bearing balances).")

# Controls
c1, c2 = st.columns([1.2, 2.8])
with c1:
    repdte = st.text_input("REPDTE (YYYYMMDD)", value="20250930", help="Example: 20250930 for 2025 Q3")
with c2:
    refresh = st.button("🔄 Refresh (clear cache)", use_container_width=False)

if refresh:
    st.cache_data.clear()

# 1) First: FDIC data (publish this first)
with st.spinner("Fetching FDIC data..."):
    out = load_reserves(repdte)

if out.empty:
    st.error("No FDIC data returned. Check REPDTE or FDIC API availability.")
    st.stop()

total_reserves = out["reserve_used"].sum()
n_banks = len(out)

chfrb_mask = out["reserve_source"] == "CHFRB"
chbali_mask = out["reserve_source"] == "CHBALI"

chfrb_count = int(chfrb_mask.sum())
chbali_count = int(chbali_mask.sum())

chfrb_amount = out.loc[chfrb_mask, "reserve_used"].sum()
chbali_amount = out.loc[chbali_mask, "reserve_used"].sum()

m1, m2, m3 = st.columns(3)
m1.metric("REPDTE", repdte)
m2.metric("Number of banks", f"{n_banks:,}")
m3.metric("Total reserves (FDIC: CHFRB else CHBALI)", f"{total_reserves:,.0f}")

b1, b2 = st.columns(2)
with b1:
    st.metric("CHFRB used", f"{chfrb_count:,} banks", delta=f"{chfrb_amount:,.0f} USD")
with b2:
    st.metric("CHBALI used", f"{chbali_count:,} banks", delta=f"{chbali_amount:,.0f} USD")

st.divider()

# 2) Then: Foreign bank branches reserves (new row, separate from FDIC)
st.subheader("U.S. Branches and Agencies of Foreign Banks (Table 4.30)")
st.caption("Fed Table 4.30 item: **Balances with Federal Reserve Banks** (units: millions of dollars).")

try:
    foreign_musd = fetch_foreign_bank_branches_reserves_musd()
    foreign_busd = foreign_musd / 1000.0
    st.metric(
        "U.S. Branches and Agencies of Foreign Banks Reserves",
        f"{foreign_busd:,.1f}B USD",
        help="Source: federalreserve.gov/data/assetliab/current.htm (Table 4.30). Value pulled from the 'Balances with Federal Reserve Banks' row."
    )
except Exception as e:
    st.warning(f"Could not fetch Table 4.30 value right now: {e}")

st.divider()

# Concentration chart: Top 10/20/50 shares (Altair)
def top_share(df: pd.DataFrame, k: int) -> float:
    tot = df["reserve_used"].sum()
    if tot == 0:
        return 0.0
    return df.sort_values("reserve_used", ascending=False).head(k)["reserve_used"].sum() / tot * 100

plot_df = pd.DataFrame(
    {
        "Group": ["Top 10 banks", "Top 20 banks", "Top 50 banks"],
        "Share (%)": [
            top_share(out, 10),
            top_share(out, 20),
            top_share(out, 50),
        ],
    }
)

st.subheader("FDIC concentration (bank reserves are highly concentrated)")
chart = (
    alt.Chart(plot_df)
    .mark_bar()
    .encode(
        x=alt.X("Group:N", sort=None, title=""),
        y=alt.Y("Share (%):Q", title="Share of total reserves (%)", scale=alt.Scale(domain=[0, 100])),
        tooltip=["Group:N", alt.Tooltip("Share (%):Q", format=".2f")],
    )
)

labels = (
    alt.Chart(plot_df)
    .mark_text(dy=-8)
    .encode(
        x=alt.X("Group:N", sort=None),
        y=alt.Y("Share (%):Q"),
        text=alt.Text("Share (%):Q", format=".1f"),
    )
)

st.altair_chart((chart + labels).properties(height=320), use_container_width=True)

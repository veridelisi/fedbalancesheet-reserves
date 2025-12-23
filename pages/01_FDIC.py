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


cols = st.columns(10)
with cols[0]:
    st.page_link("streamlit_app.py", label="🏠 Home")
with cols[1]:
    st.page_link("pages/01_Reserves.py", label="🌍 Reserves")
with cols[2]:
    st.page_link("pages/01_FDIC.py", label="🏦 FDIC")
with cols[3]:
    st.page_link("pages/01_Repo.py", label="🔄 Repo")
with cols[4]:
    st.page_link("pages/01_Repo2.py", label="♻️ Repo 2")
with cols[5]:
    st.page_link("pages/01_TGA.py", label="🏛️ TGA")
with cols[6]:
    st.page_link("pages/01_PublicBalance.py", label="📊 Public Balance")
with cols[7]:
    st.page_link("pages/01_Interest.py", label="📈 Reference Rates")
with cols[8]:
    st.page_link("pages/01_Desk.py", label="🛰️ Desk")
with cols[9]:
    st.page_link("pages/01_Eurodollar.py", label="💡 Eurodollar")
st.markdown("""
<style>
/* Top nav page_link alignment fix */
a[data-testid="stPageLink-NavLink"] {
    display: inline-flex !important;
    align-items: center !important;
    justify-content: center !important;
    gap: 0.4rem !important;
    line-height: 1.2 !important;
    white-space: nowrap !important;
}
</style>
""", unsafe_allow_html=True)

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
def load_fdic_reserves(rep_dte: str) -> pd.DataFrame:
    """
    Returns bank-level reserves dataset used for aggregation (FDIC values are in thousand USD):
      CERT, NAME, REPDTE, CHFRB, CHBALI, reserve_used, reserve_source
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
# Fed Table 4.30: Foreign bank branches reserves (Balances with Federal Reserve Banks)
# -----------------------------------------------------------------------------
FED_TABLE_430_URL = "https://www.federalreserve.gov/data/assetliab/current.htm"

@st.cache_data(ttl=6 * 60 * 60, show_spinner=False)
def fetch_foreign_bank_branches_reserves_musd() -> float:
    """
    Extracts Table 4.30 'Balances with Federal Reserve Banks' value.
    Table units: million USD.
    Uses regex only (no bs4 dependency).
    """
    html = requests.get(FED_TABLE_430_URL, timeout=30).text

    pattern = (
        r'Balances with Federal Reserve Banks'
        r'.{0,500}?'
        r'<td[^>]*class="shadedata"[^>]*>\s*([\d,]+)\s*</td>'
    )
    m = re.search(pattern, html, re.I | re.S)
    if not m:
        raise RuntimeError("Table 4.30 value not found in HTML (Balances with Federal Reserve Banks).")

    return float(m.group(1).replace(",", ""))  # million USD

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
    refresh = st.button("🔄 Refresh (clear cache)")

if refresh:
    st.cache_data.clear()

# -----------------------------------------------------------------------------
# 1) FIRST: FDIC (insured U.S. banks) — publish this first
# -----------------------------------------------------------------------------
with st.spinner("Fetching FDIC data..."):
    out = load_fdic_reserves(repdte)

if out.empty:
    st.error("No FDIC data returned. Check REPDTE or FDIC API availability.")
    st.stop()

# FDIC values are in thousand USD
total_reserves_thousand_usd = out["reserve_used"].sum()
n_banks = len(out)

chfrb_mask = out["reserve_source"] == "CHFRB"
chbali_mask = out["reserve_source"] == "CHBALI"

chfrb_count = int(chfrb_mask.sum())
chbali_count = int(chbali_mask.sum())

chfrb_amount_thousand_usd = out.loc[chfrb_mask, "reserve_used"].sum()
chbali_amount_thousand_usd = out.loc[chbali_mask, "reserve_used"].sum()

m1, m2, m3 = st.columns(3)
m1.metric("REPDTE", repdte)
m2.metric("Number of banks", f"{n_banks:,}")
m3.metric("Total reserves (FDIC, thousand USD)", f"{total_reserves_thousand_usd:,.0f}")

b1, b2 = st.columns(2)
with b1:
    st.metric("CHFRB used", f"{chfrb_count:,} banks", delta=f"{chfrb_amount_thousand_usd:,.0f} (thousand USD)")
with b2:
    st.metric("CHBALI used", f"{chbali_count:,} banks", delta=f"{chbali_amount_thousand_usd:,.0f} (thousand USD)")



# -----------------------------------------------------------------------------
# 3) FDIC concentration chart (Top 10/20/50) — keep it, no bank table, no CSV
# -----------------------------------------------------------------------------
st.divider()
st.subheader("FDIC concentration (insured U.S. banks)")

def top_share(df: pd.DataFrame, k: int) -> float:
    tot = df["reserve_used"].sum()
    if tot == 0:
        return 0.0
    return df.sort_values("reserve_used", ascending=False).head(k)["reserve_used"].sum() / tot * 100

plot_df = pd.DataFrame(
    {
        "Group": ["Top 10 banks", "Top 20 banks", "Top 50 banks"],
        "Share (%)": [top_share(out, 10), top_share(out, 20), top_share(out, 50)],
    }
)

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

# -----------------------------------------------------------------------------
# 2) THEN: Fed Table 4.30 — separate section (as you requested)
# -----------------------------------------------------------------------------
st.divider()
st.subheader("U.S. Branches and Agencies of Foreign Banks (Table 4.30)")
st.caption("Fed Table 4.30 item: **Balances with Federal Reserve Banks** (units: **millions of dollars**).")

foreign_musd = None
try:
    foreign_musd = fetch_foreign_bank_branches_reserves_musd()
    # Display as trillion USD and also show the raw million USD in help
    foreign_trillion = (foreign_musd * 1e6) / 1e12
    st.metric(
        "U.S. Branches and Agencies of Foreign Banks Reserves",
        f"{foreign_trillion:,.3f}T USD",
        help=f"Raw table value: {foreign_musd:,.0f} (million USD). Converted to USD and then to trillion."
    )
except Exception as e:
    st.warning(f"Could not fetch Table 4.30 value right now: {e}")


# -----------------------------------------------------------------------------
# 4) FINAL SECTION (at the very end): Pie chart using TWO sources only
#    - FDIC (insured U.S. banks): thousand USD -> trillion USD
#    - Foreign banks (U.S. branches): million USD -> trillion USD
#    No Credit Unions.
# -----------------------------------------------------------------------------
# -----------------------------------------------------------------------------
# 4) FINAL SECTION (at the very end): Pie chart using TWO sources only
#    - FDIC (insured U.S. banks): thousand USD -> trillion USD
#    - Foreign banks (U.S. branches): million USD -> trillion USD
#    No Credit Unions.
# -----------------------------------------------------------------------------
st.divider()
st.subheader("Distribution of Bank Reserves (FDIC vs Foreign Banks)")

if foreign_musd is None:
    st.info("Pie chart requires the Fed Table 4.30 value. Once it loads, the chart will render here.")
else:
    # Convert both to trillion USD
    fdic_trillion = (total_reserves_thousand_usd * 1_000) / 1e12   # thousand -> USD -> trillion
    foreign_trillion = (foreign_musd * 1e6) / 1e12                 # million -> USD -> trillion

    total_trillion = fdic_trillion + foreign_trillion

    # Build display dataframe
    pie_df = pd.DataFrame({
        "Sector": ["Insured U.S. Banks", "Foreign Banks (U.S. Branches)"],
        "Reserves (Trillion USD)": [fdic_trillion, foreign_trillion],
    })
    pie_df["Share (%)"] = 100 * pie_df["Reserves (Trillion USD)"] / total_trillion

    # --- A nicer, more "polite" layout: numbers first, chart second ---
    k1, k2, k3 = st.columns([1.3, 1.3, 1.8])
    k1.metric("Insured U.S. Banks", f"{fdic_trillion:,.2f}T USD", delta=f"{pie_df.loc[0,'Share (%)']:.1f}%")
    k2.metric("Foreign Banks (U.S. Branches)", f"{foreign_trillion:,.2f}T USD", delta=f"{pie_df.loc[1,'Share (%)']:.1f}%")
    k3.metric("Total (two sources)", f"{total_trillion:,.2f}T USD")

    st.caption("Shares are computed using the two sources below only (no credit unions).")

    # --- Donut chart (cleaner than a solid pie) ---
    donut = (
        alt.Chart(pie_df)
        .mark_arc(innerRadius=70, outerRadius=150, cornerRadius=6)
        .encode(
            theta=alt.Theta("Reserves (Trillion USD):Q"),
            color=alt.Color("Sector:N", legend=alt.Legend(title="")),
            tooltip=[
                alt.Tooltip("Sector:N"),
                alt.Tooltip("Reserves (Trillion USD):Q", format=".2f"),
                alt.Tooltip("Share (%):Q", format=".1f"),
            ],
        )
        .properties(height=380)
    )

    # Percentage labels placed on the ring
    labels = (
        alt.Chart(pie_df)
        .mark_text(radius=130, size=14, color="white")
        .encode(
            theta=alt.Theta("Reserves (Trillion USD):Q"),
            text=alt.Text("Share (%):Q", format=".1f"),
        )
    )

    # Center text: Total
    center = (
        alt.Chart(pd.DataFrame({"text": [f"{total_trillion:,.2f}T"]}))
        .mark_text(size=26, fontWeight="bold")
        .encode(text="text:N")
    )

    center_sub = (
        alt.Chart(pd.DataFrame({"text": ["Total reserves"]}))
        .mark_text(size=12, dy=22)
        .encode(text="text:N")
    )

    st.altair_chart(donut + labels + center + center_sub, use_container_width=True)

    st.caption(
        "Unit notes: FDIC Call Report values are in **thousand USD**. "
        "Fed Table 4.30 values are in **million USD**. "
        "Both series are converted to **trillion USD** before computing shares."
    )



# ------------------------------ Methodology ------------------------------
st.markdown("### 📋 Methodology")

with st.expander("🔎 Click to expand methodology details", expanded=False):
    st.markdown("""
**What you’re seeing on this page (in plain English):**  
We combine **two official sources** to describe where U.S. reserve balances sit:  
- 🏦 **FDIC-insured U.S. banks** (bank-level, from FDIC Call Reports via API)  
- 🌍 **U.S. branches & agencies of foreign banks** (sector-level, from Fed Table 4.30)

---

### 1) 🏦 FDIC (Insured U.S. Banks): How reserves are measured
**Goal:** Build a bank-by-bank estimate of reserve balances held by **FDIC-insured banks**.

**Data source:** FDIC BankFind / Call Report API  
- 🌐 **Base URL:**  
  `https://banks.data.fdic.gov/api`

**API endpoints used:**
- 🏷️ **Institutions (bank identifiers & names)**  
Used to retrieve:
- `CERT` (bank certificate number)
- `NAME` (official bank name)

- 📊 **Financials (Call Report balance sheet items)**  

                Used to retrieve reserve-related fields by reporting date (`REPDTE`).

**Typical query logic (simplified):**
- Filter to **ACTIVE banks only**
- Filter by **REPDTE** (quarter-end date, e.g. `20250930`)
- Paginate using `limit` + `offset`

---

### 2) 🔑 FDIC variables used (priority + fallback)
- ✅ **CHFRB**  
*Balances due from Federal Reserve Banks*  
→ Preferred and most direct proxy for reserve balances

- ↪️ **CHBALI**  
*Interest-bearing balances*  
→ Used **only if CHFRB is missing**

**Rule applied in the code:**
- 🧠 If **CHFRB exists**, use CHFRB  
- 🪂 Else, fall back to CHBALI  
- 🧯 If both are missing (rare), treat as **0**

---

### 3) ⚠️ Unit convention (very important)
FDIC Call Report amounts are reported in **thousand USD**.

Example:
- `1,772,647,048`  
- = 1,772,647,048 **thousand USD**  
- ≈ **1.77 trillion USD**

All FDIC values are converted accordingly before comparison.

---

### 4) 🌍 Foreign banks: Fed Table 4.30
**Source:** Federal Reserve  
*Assets and Liabilities of U.S. Branches and Agencies of Foreign Banks (Table 4.30)*

**Item used:**  
- 🧾 *Balances with Federal Reserve Banks*

**Unit:** million USD

---

### 5) 🧮 Harmonizing units
To make the two sources comparable:
- 🏦 FDIC → thousand USD → USD → **trillion USD**
- 🌍 Fed Table 4.30 → million USD → USD → **trillion USD**

---

### 6) 🥧 Pie chart interpretation
The final pie chart includes **only two sectors**:
- 🏦 Insured U.S. Banks (FDIC)
- 🌍 Foreign Banks (U.S. Branches)

🚫 Credit unions are **intentionally excluded**.

---

### 7) 🔁 Caching & refresh
- ⚡ Data is cached using `@st.cache_data`
- 🔄 “Refresh” clears cache and re-fetches data from both sources

---

### 8) ⚖️ Interpretation caveat
- FDIC data: bank-level, insured institutions  
- Fed Table 4.30: sector-level totals  

Use results as a **high-level distribution view**, not a perfect reconciliation.

### 9) ⚖️ Note
             

- The sum of these two series does not exactly equal total reserve amounts because this analysis excludes credit unions.
- For a more detailed breakdown, see https://veridelisi.substack.com/p/who-holds-us-dollar-reserves
""")


 # --------------------------- Footer -------------------------------

st.markdown(
    """
    <div style="text-align:center;color:#64748b;font-size:0.95rem;padding:20px 0;">
        <a href="https://veridelisi.substack.com/">Veri Delisi</a>🚀 <br>
        <em>Engin Yılmaz • Amherst • September 2025 </em>
    </div>
    """,
    unsafe_allow_html=True
)   
import streamlit as st
import requests
import pandas as pd
import plotly.express as px
import plotly.graph_objects as go
from datetime import datetime, date
import numpy as np


# Page configuration
st.set_page_config(
    page_title="Fed Repo Operations Dashboard",
    page_icon="📊",
    layout="wide"
)

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
    st.page_link("pages/01_PublicBalance.py", label="📊 P.Balance")
with cols[7]:
    st.page_link("pages/01_Interest.py", label="📈 Rates")
with cols[8]:
    st.page_link("pages/01_Desk.py", label="🛰️ Desk")
with cols[9]:
    st.page_link("pages/01_Eurodollar.py", label="💡 Eurodollar")

# ---------------------------- STOP Expanded -----------------
st.markdown(
    """
<style>
    [data-testid="stSidebarNav"] {display: none;}
    section[data-testid="stSidebar"][aria-expanded="true"]{display: none;}
</style>
""",
    unsafe_allow_html=True,
)
# ---------------------------- CODE -----------------
@st.cache_data(ttl=3600)  # Cache for 1 hour
def fetch_fed_data(operation_type='repo'):
    """
    Fetch Federal Reserve repo/reverse repo operations data
    """
    base_url = "https://markets.newyorkfed.org/api/rp"
    
    # URLs to try in order of preference
    urls_to_try = [
        f"{base_url}/{operation_type}/all/results/last/500.json",
        f"{base_url}/{operation_type}/all/results/last/100.json",
        f"{base_url}/{operation_type}/all/results/last/50.json",
    ]
    
    headers = {
        'User-Agent': 'Mozilla/5.0 (Windows NT 10.0; Win64; x64) AppleWebKit/537.36 (KHTML, like Gecko) Chrome/91.0.4472.124 Safari/537.36',
        'Accept': 'application/json',
        'Accept-Language': 'en-US,en;q=0.9'
    }
    
    for url in urls_to_try:
        try:
            response = requests.get(url, headers=headers, timeout=30)
            response.raise_for_status()
            data = response.json()
            return data
        except requests.exceptions.RequestException as e:
            continue
    
    return None

def process_data(data, operation_type='repo'):
    """
    Process repo or reverse repo operations data
    """
    key = 'repo' if operation_type == 'repo' else 'repo'  # Both use 'repo' key in JSON
    
    if not data or key not in data or 'operations' not in data[key]:
        return pd.DataFrame()
    
    operations = data[key]['operations']
    results = []
    
    for operation in operations:
        op_date = datetime.strptime(operation['operationDate'], '%Y-%m-%d')
        total_accepted = operation['totalAmtAccepted']
        
        if total_accepted == 0:
            continue
            
        # Handle different rate fields for repo vs reverse repo
        if operation_type == 'repo':
            # For regular repo: use percentWeightedAverageRate
            total_weighted_rate = 0
            total_amount = 0
            
            for detail in operation['details']:
                if detail['amtAccepted'] > 0 and 'percentWeightedAverageRate' in detail:
                    amount = detail['amtAccepted']
                    rate = detail['percentWeightedAverageRate']
                    total_weighted_rate += rate * amount
                    total_amount += amount
            
            overall_rate = total_weighted_rate / total_amount if total_amount > 0 else None
        else:
            # For reverse repo: use percentAwardRate
            rates = []
            amounts = []
            
            for detail in operation['details']:
                if detail['amtAccepted'] > 0 and 'percentAwardRate' in detail:
                    rates.append(detail['percentAwardRate'])
                    amounts.append(detail['amtAccepted'])
            
            # Calculate weighted average
            if amounts:
                overall_rate = sum(r * a for r, a in zip(rates, amounts)) / sum(amounts)
            else:
                overall_rate = None
            
        results.append({
            'operation_date': op_date,
            'operation_id': operation['operationId'],
            'term': operation['term'],
            'total_accepted_amount': total_accepted,
            'rate': overall_rate,
            'amount_billions': total_accepted / 1_000_000_000
        })
    
    df = pd.DataFrame(results)
    
    if not df.empty:
        df = df.sort_values('operation_date', ascending=False)
        df = df.reset_index(drop=True)
    
    return df

def create_bar_chart(df_filtered, title_suffix=""):
    """
    Create bar chart for operations since 2025-01-01
    """
    if df_filtered.empty:
        return None
    
    # Group by date and sum amounts (in case multiple operations per day)
    daily_data = df_filtered.groupby('operation_date').agg({
        'rate': 'mean',
        'amount_billions': 'sum'
    }).reset_index()
    
    # Create simple bar chart (only amounts)
    fig = go.Figure()
    
    # Add bar chart for amounts only
    color = 'lightcoral' if 'Reverse' in title_suffix else 'lightblue'
    
    fig.add_trace(go.Bar(
        x=daily_data['operation_date'],
        y=daily_data['amount_billions'],
        name=f'Accepted Amount ($B){title_suffix}',
        marker_color=color,
        hovertemplate='Date: %{x}<br>Amount: $%{y:.2f}B<extra></extra>'
    ))
    
    # Update layout
    fig.update_layout(
        title=f'Fed {title_suffix} Operations Since January 1, 2025',
        xaxis_title='Date',
        yaxis=dict(
            title='Accepted Amount ($ Billions)',
            range=[0, daily_data['amount_billions'].max() * 1.1]
        ),
        hovermode='x',
        height=400,
        showlegend=False
    )
    
    return fig

# Main Streamlit App
def main():
    st.title("🏛️ Federal Reserve Operations Dashboard")
    
    # Add option to use sample data if API fails
    use_sample_data = st.sidebar.checkbox("Use Sample Data (if API fails)")
    
    # Fetch both repo and reverse repo data
    repo_data = None
    reverse_repo_data = None
    
    if use_sample_data:
        st.info("Using sample data")
        # Sample data would go here
        repo_data = {"repo": {"operations": []}}
        reverse_repo_data = {"repo": {"operations": []}}
    else:
        with st.spinner("Fetching Fed operations data..."):
            repo_data = fetch_fed_data('repo')
            reverse_repo_data = fetch_fed_data('reverserepo')
    
    # Process both datasets
    repo_df = process_data(repo_data, 'repo') if repo_data else pd.DataFrame()
    reverse_repo_df = process_data(reverse_repo_data, 'reverserepo') if reverse_repo_data else pd.DataFrame()
    
    # Filter for operations with rates
    repo_df_with_rates = repo_df[repo_df['rate'].notna()].copy() if not repo_df.empty else pd.DataFrame()
    reverse_repo_df_with_rates = reverse_repo_df[reverse_repo_df['rate'].notna()].copy() if not reverse_repo_df.empty else pd.DataFrame()
    
    # === REPO SECTION ===
    if not repo_df_with_rates.empty:
        st.header("📈 Latest Repo Operation")
        
        latest_repo = repo_df_with_rates.iloc[0]
        
        col1, col2, col3, col4 = st.columns(4)
        
        with col1:
            st.metric("Operation Date", latest_repo['operation_date'].strftime("%Y-%m-%d"))
        
        with col2:
            st.metric("Weighted Average Rate", f"{latest_repo['rate']:.3f}%")
        
        with col3:
            st.metric("Accepted Amount", f"${latest_repo['amount_billions']:.2f}B")
        
        with col4:
            st.metric("Term", latest_repo['term'])
        
        # Repo chart since 2025-01-01
        st.subheader("📊 Repo Operations Since January 1, 2025")
        
        start_date = datetime(2025, 1, 1)
        repo_2025 = repo_df_with_rates[repo_df_with_rates['operation_date'] >= start_date].copy()
        
        if not repo_2025.empty:
            fig_repo = create_bar_chart(repo_2025, "Repo")
            if fig_repo:
                st.plotly_chart(fig_repo, use_container_width=True)
        else:
            st.warning("No repo operations found since January 1, 2025")
    
    st.divider()
    
    # === REVERSE REPO SECTION ===
    if not reverse_repo_df_with_rates.empty:
        st.header("📉 Latest Reverse Repo Operation")
        
        latest_reverse_repo = reverse_repo_df_with_rates.iloc[0]
        
        col1, col2, col3, col4 = st.columns(4)
        
        with col1:
            st.metric("Operation Date", latest_reverse_repo['operation_date'].strftime("%Y-%m-%d"))
        
        with col2:
            st.metric("Award Rate", f"{latest_reverse_repo['rate']:.3f}%")
        
        with col3:
            st.metric("Accepted Amount", f"${latest_reverse_repo['amount_billions']:.2f}B")
        
        with col4:
            st.metric("Term", latest_reverse_repo['term'])
        
        # Reverse Repo chart since 2025-01-01
        st.subheader("📊 Reverse Repo Operations Since January 1, 2025")
        
        start_date = datetime(2025, 1, 1)
        reverse_repo_2025 = reverse_repo_df_with_rates[reverse_repo_df_with_rates['operation_date'] >= start_date].copy()
        
        if not reverse_repo_2025.empty:
            fig_reverse_repo = create_bar_chart(reverse_repo_2025, "Reverse Repo")
            if fig_reverse_repo:
                st.plotly_chart(fig_reverse_repo, use_container_width=True)
        else:
            st.warning("No reverse repo operations found since January 1, 2025")
    

    
    if repo_df_with_rates.empty and reverse_repo_df_with_rates.empty:
        st.error("No data available for either repo or reverse repo operations")

if __name__ == "__main__":
    main()

# ------------------------------ Methodology ------------------------------
st.markdown("### 📋 Methodology")
with st.expander("🔎 Click to expand methodology details", expanded=False):
    st.markdown("""
**What this page shows**  
- 🧰 Primary Dealer **Desk Operations** from the New York Fed: **Repo** and **Reverse Repo** (ON RRP).  
- 📅 Aggregated **by operation day**: accepted amounts and **weighted average rates**.

---

### 🗂️ Data source
- 🏦 Federal Reserve Bank of New York — **Primary Dealer Desk Operations** API  
  • Base: `https://markets.newyorkfed.org/api/`  
  • Endpoints:  
    - `rp/repo/all/results/last/{N}.json`  
    - `rp/reverserepo/all/results/last/{N}.json`  
- ⏱️ Update: business days; occasional intraday postings and revisions.

---

### 📦 What’s included
- 🔄 **Operations** (each may contain multiple **detail** rows).  
- 💵 **Accepted amounts**: `totalAmtAccepted` (USD).  
- 📈 **Rates**:  
  - **Repo**: weighted by `percentWeightedAverageRate` over `amtAccepted`.  
  - **Reverse Repo**: weighted by `percentAwardRate` over `amtAccepted`.

---

### 🧮 Transformations (in this dashboard)
- 🧹 Parse all operations; **drop zero-accepted** rows.  
- 🧷 Compute **operation-day weighted average rate**:  
  - Repo W.A. = Σ(rateᵢ × amtᵢ) / Σ(amtᵢ), using **percentWeightedAverageRate**.  
  - RRP W.A. = Σ(rateᵢ × amtᵢ) / Σ(amtᵢ), using **percentAwardRate**.  
- ➕ If multiple ops on the same day: **sum accepted** amounts, **re-weight** the rate.  
- 🔢 Convert amounts to **billions of dollars** (÷1,000).  
- 🗓️ Optional filter chips: e.g., **since 2025-01-01** → `operation_date ≥ 2025-01-01`.

---

### 🔢 Units & scales
- 💵 Amounts: **$ billions (B)**.  
- 📊 Rates: **percent (%)**, operation-day weighted averages.

---

### ⚠️ Caveats
- 📆 Multiple operations per day are common (AM/PM); we aggregate by **date**.  
- 🧮 Weighting uses only rows with valid **amount** and **rate**; missing fields are skipped.  
- 🚫 Weekends/holidays generally have **no operations**.  
- 🧊 Responses are **cached** (`@st.cache_data(ttl=3600)`), so recent updates may lag.

---

### 🗺️ Glossary
- **Repo**: Fed lends cash against collateral to dealers (adds reserves).  
- **Reverse Repo (RRP)**: Fed takes in cash against collateral (drains reserves).  
- **Accepted amount**: Final awarded cash volume for the operation.  
- **Weighted average rate**: Amount-weighted price of the operation for that day.
    """)


# --------------------------- Footer -------------------------------
st.markdown("---")
st.markdown(
    """
    <div style="text-align:center;color:#64748b;font-size:0.95rem;padding:20px 0;">
        <a href="https://veridelisi.substack.com/">Veri Delisi</a>🚀 <br>
        <em>Engin Yılmaz • Amherst • September 2025 </em>
    </div>
    """,
    unsafe_allow_html=True
)

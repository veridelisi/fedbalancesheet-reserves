import math
import requests
import pandas as pd
import numpy as np
import streamlit as st
import altair as alt
from datetime import date, datetime
from dateutil.relativedelta import relativedelta

# ========================= CONFIG =========================
st.set_page_config(
    page_title="TGA Dashboard", 
    layout="wide",
    initial_sidebar_state="collapsed"
)

# Constants
API_BASE = "https://api.fiscaldata.treasury.gov/services/api/fiscal_service/v1/accounting/dts/operating_cash_balance"
ACCOUNT_TYPES = {
    "opening": "Treasury General Account (TGA) Opening Balance",
    "deposits": "Total TGA Deposits (Table II)",
    "withdrawals": "Total TGA Withdrawals (Table II) (-)"
}

COLORS = {
    "deposits": "#10b981",
    "withdrawals": "#ef4444", 
    "closing": "#2563eb",
    "neutral": "#6b7280"
}

# ========================= UTILS =========================
@st.cache_data(ttl=1800)
def fetch_latest_date():
    """Get the most recent available date from the API"""
    try:
        response = requests.get(API_BASE, params={
            "fields": "record_date",
            "sort": "-record_date",
            "page[size]": 1
        }, timeout=30)
        response.raise_for_status()
        data = response.json().get("data", [])
        return data[0]["record_date"] if data else None
    except Exception as e:
        st.error(f"Failed to fetch latest date: {e}")
        return None

@st.cache_data(ttl=1800)
def fetch_tga_data(account_type, start_date, end_date=None):
    """Fetch TGA data for a specific account type and date range"""
    params = {
        "filter": f"account_type:eq:{account_type}",
        "sort": "record_date"
    }
    
    if end_date:
        params["filter"] += f",record_date:gte:{start_date},record_date:lte:{end_date}"
    else:
        params["filter"] += f",record_date:lte:{start_date}"
        params["page[size]"] = 1
        params["sort"] = "-record_date"
    
    try:
        response = requests.get(API_BASE, params=params, timeout=30)
        response.raise_for_status()
        data = response.json().get("data", [])
        
        if not data:
            return None if not end_date else pd.DataFrame()
            
        # Convert to DataFrame for date ranges, single value for point queries
        if end_date:
            df = pd.DataFrame(data)
            df["record_date"] = pd.to_datetime(df["record_date"])
            df["value"] = pd.to_numeric(df["today_amt"].fillna(df["open_today_bal"]), errors="coerce")
            return df[["record_date", "value"]].dropna()
        else:
            row = data[0]
            return float(str(row.get("today_amt") or row.get("open_today_bal", 0)).replace(",", ""))
            
    except Exception as e:
        st.error(f"API Error: {e}")
        return None if not end_date else pd.DataFrame()

def to_billions(millions):
    """Convert millions to billions"""
    return millions / 1000 if millions and not pd.isna(millions) else 0

def format_billions(value):
    """Format billions with 1 decimal place"""
    return f"${value:,.1f}B" if value else "$0.0B"

# ========================= UI COMPONENTS =========================
def create_navigation():
    """Create horizontal navigation bar"""
    st.markdown("""
    <style>
    .nav-container {
        background: linear-gradient(90deg, #f8fafc 0%, #e2e8f0 100%);
        padding: 1rem;
        border-radius: 10px;
        margin-bottom: 2rem;
        text-align: center;
    }
    .nav-title {
        font-size: 1.5rem;
        font-weight: bold;
        color: #1e293b;
        margin-bottom: 0.5rem;
    }
    </style>
    <div class="nav-container">
        <div class="nav-title">🏦 Treasury General Account (TGA) Dashboard</div>
    </div>
    """, unsafe_allow_html=True)

def create_summary_card(opening, deposits, withdrawals, closing, date_str):
    """Create the main summary card with the accounting equation"""
    st.markdown(f"""
    <style>
    .summary-card {{
        background: white;
        border: 2px solid #e2e8f0;
        border-radius: 15px;
        padding: 2rem;
        margin: 1rem 0;
        box-shadow: 0 4px 6px -1px rgba(0, 0, 0, 0.1);
    }}
    .date-badge {{
        background: {COLORS['neutral']};
        color: white;
        padding: 0.5rem 1rem;
        border-radius: 20px;
        font-size: 0.9rem;
        font-weight: 600;
        display: inline-block;
        margin-bottom: 1rem;
    }}
    .equation {{
        display: flex;
        align-items: center;
        justify-content: center;
        gap: 1rem;
        flex-wrap: wrap;
        margin: 1rem 0;
    }}
    .value-box {{
        padding: 1rem 1.5rem;
        border-radius: 10px;
        font-weight: bold;
        font-size: 1.2rem;
        text-align: center;
        min-width: 120px;
    }}
    .opening {{ background: {COLORS['closing']}; color: white; }}
    .deposits {{ background: {COLORS['deposits']}; color: white; }}
    .withdrawals {{ background: {COLORS['withdrawals']}; color: white; }}
    .closing {{ background: {COLORS['neutral']}; color: white; }}
    .operator {{
        font-size: 1.5rem;
        font-weight: bold;
        color: {COLORS['neutral']};
    }}
    @media (max-width: 768px) {{
        .equation {{ flex-direction: column; gap: 0.5rem; }}
        .value-box {{ font-size: 1rem; min-width: 100px; }}
    }}
    </style>
    
    <div class="summary-card">
        <div class="date-badge">📅 Latest Data: {date_str}</div>
        
        <div class="equation">
            <div class="value-box opening">
                <div style="font-size: 0.9rem; opacity: 0.9;">Opening</div>
                {format_billions(opening)}
            </div>
            <div class="operator">+</div>
            <div class="value-box deposits">
                <div style="font-size: 0.9rem; opacity: 0.9;">Deposits</div>
                {format_billions(deposits)}
            </div>
            <div class="operator">−</div>
            <div class="value-box withdrawals">
                <div style="font-size: 0.9rem; opacity: 0.9;">Withdrawals</div>
                {format_billions(withdrawals)}
            </div>
            <div class="operator">=</div>
            <div class="value-box closing">
                <div style="font-size: 0.9rem; opacity: 0.9;">Closing</div>
                {format_billions(closing)}
            </div>
        </div>
    </div>
    """, unsafe_allow_html=True)

def create_bar_chart(deposits, withdrawals):
    """Create a simple bar chart for deposits vs withdrawals"""
    df = pd.DataFrame({
        "Category": ["Deposits", "Withdrawals"],
        "Amount": [deposits, withdrawals],
        "Color": [COLORS["deposits"], COLORS["withdrawals"]]
    })
    
    chart = alt.Chart(df).mark_bar(size=80).encode(
        x=alt.X("Category:N", title=None, axis=alt.Axis(labelFontSize=14)),
        y=alt.Y("Amount:Q", title="Billions ($)", axis=alt.Axis(format=",.1f", titleFontSize=14)),
        color=alt.Color("Color:N", scale=None, legend=None),
        tooltip=[
            alt.Tooltip("Category:N"),
            alt.Tooltip("Amount:Q", format=",.1f", title="Amount (Billions)")
        ]
    ).properties(
        height=300,
        title=alt.TitleParams(
            text="Daily Deposits vs Withdrawals",
            fontSize=16,
            fontWeight="bold"
        )
    )
    
    # Add value labels on bars
    text = alt.Chart(df).mark_text(
        dy=-10,
        fontSize=12,
        fontWeight="bold"
    ).encode(
        x=alt.X("Category:N"),
        y=alt.Y("Amount:Q"),
        text=alt.Text("Amount:Q", format=",.1f")
    )
    
    return chart + text

def create_time_series_chart(data, title):
    """Create time series chart for closing balance"""
    if data.empty:
        return alt.Chart(pd.DataFrame()).mark_line()
    
    # Calculate trend
    data = data.sort_values("date")
    data["trend"] = data["closing"].rolling(window=7, center=True).mean()
    
    base = alt.Chart(data).encode(
        x=alt.X("date:T", title="Date", axis=alt.Axis(titleFontSize=14)),
        y=alt.Y("closing:Q", title="Closing Balance (Billions $)", axis=alt.Axis(format=",.1f", titleFontSize=14))
    )
    
    # Main line
    line = base.mark_line(
        color=COLORS["closing"],
        strokeWidth=2
    ).encode(
        tooltip=[
            alt.Tooltip("date:T", title="Date"),
            alt.Tooltip("closing:Q", format=",.1f", title="Closing Balance (Billions)")
        ]
    )
    
    # Trend line
    trend = base.mark_line(
        color=COLORS["neutral"],
        strokeWidth=1,
        strokeDash=[5, 5],
        opacity=0.7
    ).encode(
        y=alt.Y("trend:Q")
    )
    
    # Points for interaction
    points = base.mark_circle(
        size=30,
        color=COLORS["closing"]
    ).encode(
        tooltip=[
            alt.Tooltip("date:T", title="Date"),
            alt.Tooltip("closing:Q", format=",.1f", title="Closing Balance (Billions)")
        ]
    )
    
    return (line + trend + points).properties(
        height=400,
        title=alt.TitleParams(text=title, fontSize=16, fontWeight="bold")
    ).resolve_scale(y="independent")

# ========================= MAIN APP =========================
def main():
    # Hide sidebar and streamlit elements
    st.markdown("""
    <style>
    .stDeployButton {display: none;}
    #stDecoration {display: none;}
    [data-testid="stSidebarNav"] {display: none;}
    section[data-testid="stSidebar"] {display: none;}
    .main > div {padding-top: 1rem;}
    </style>
    """, unsafe_allow_html=True)
    
    # Navigation
    create_navigation()
    
    # Get latest date
    latest_date_str = fetch_latest_date()
    if not latest_date_str:
        st.error("❌ Unable to fetch data from Treasury API")
        st.stop()
    
    latest_date = pd.to_datetime(latest_date_str).date()
    
    # Date range selector
    st.markdown("### 📊 Analysis Period")
    col1, col2 = st.columns(2)
    
    with col1:
        period_option = st.selectbox(
            "Select time period:",
            ["Last 30 days", "Last 90 days", "Year to date", "Last year", "Custom range"],
            index=1
        )
    
    # Calculate date range based on selection
    if period_option == "Last 30 days":
        start_date = latest_date - relativedelta(days=30)
    elif period_option == "Last 90 days":
        start_date = latest_date - relativedelta(days=90)
    elif period_option == "Year to date":
        start_date = date(latest_date.year, 1, 1)
    elif period_option == "Last year":
        start_date = latest_date - relativedelta(years=1)
    else:  # Custom range
        with col2:
            start_date = st.date_input(
                "Start date:",
                value=latest_date - relativedelta(months=3),
                max_value=latest_date
            )
    
    # Fetch latest values
    with st.spinner("📥 Fetching latest TGA data..."):
        opening_val = fetch_tga_data(ACCOUNT_TYPES["opening"], latest_date_str)
        deposits_val = fetch_tga_data(ACCOUNT_TYPES["deposits"], latest_date_str)
        withdrawals_val = fetch_tga_data(ACCOUNT_TYPES["withdrawals"], latest_date_str)
    
    # Convert to billions
    opening_bn = to_billions(opening_val)
    deposits_bn = to_billions(deposits_val)
    withdrawals_bn = to_billions(withdrawals_val)
    closing_bn = opening_bn + deposits_bn - withdrawals_bn
    
    # Summary card
    create_summary_card(
        opening_bn, deposits_bn, withdrawals_bn, closing_bn,
        latest_date.strftime("%B %d, %Y")
    )
    
    # Charts section
    col1, col2 = st.columns(2)
    
    with col1:
        st.altair_chart(
            create_bar_chart(deposits_bn, withdrawals_bn),
            use_container_width=True
        )
    
    with col2:
        # Key metrics
        st.markdown("### 📈 Key Metrics")
        net_flow = deposits_bn - withdrawals_bn
        net_color = COLORS["deposits"] if net_flow >= 0 else COLORS["withdrawals"]
        
        st.markdown(f"""
        <div style="background: white; padding: 1.5rem; border-radius: 10px; border: 1px solid #e2e8f0;">
            <div style="display: flex; justify-content: space-between; margin-bottom: 1rem;">
                <span style="color: {COLORS['neutral']};">Net Daily Flow:</span>
                <span style="color: {net_color}; font-weight: bold;">{format_billions(net_flow)}</span>
            </div>
            <div style="display: flex; justify-content: space-between; margin-bottom: 1rem;">
                <span style="color: {COLORS['neutral']};">Cash Efficiency:</span>
                <span style="font-weight: bold;">{deposits_bn/(withdrawals_bn or 1):.2f}x</span>
            </div>
            <div style="display: flex; justify-content: space-between;">
                <span style="color: {COLORS['neutral']};">Balance Change:</span>
                <span style="color: {net_color}; font-weight: bold;">
                    {'↗️' if net_flow >= 0 else '↘️'} {abs(net_flow/opening_bn*100) if opening_bn else 0:.1f}%
                </span>
            </div>
        </div>
        """, unsafe_allow_html=True)
    
    # Time series chart
    st.markdown("### 📉 Historical Closing Balance")
    
    with st.spinner("📊 Loading historical data..."):
        # Fetch time series data
        opening_ts = fetch_tga_data(ACCOUNT_TYPES["opening"], start_date.isoformat(), latest_date_str)
        deposits_ts = fetch_tga_data(ACCOUNT_TYPES["deposits"], start_date.isoformat(), latest_date_str)
        withdrawals_ts = fetch_tga_data(ACCOUNT_TYPES["withdrawals"], start_date.isoformat(), latest_date_str)
    
    if not any(df.empty for df in [opening_ts, deposits_ts, withdrawals_ts]):
        # Merge and calculate closing balance
        ts_data = opening_ts.rename(columns={"value": "opening"}) \
            .merge(deposits_ts.rename(columns={"value": "deposits"}), on="record_date", how="outer") \
            .merge(withdrawals_ts.rename(columns={"value": "withdrawals"}), on="record_date", how="outer")
        
        ts_data = ts_data.fillna(method="ffill").fillna(0)
        ts_data["closing"] = (ts_data["opening"] + ts_data["deposits"] - ts_data["withdrawals"]) / 1000
        ts_data = ts_data.rename(columns={"record_date": "date"})
        
        st.altair_chart(
            create_time_series_chart(
                ts_data[["date", "closing"]],
                f"TGA Closing Balance ({start_date.strftime('%Y-%m-%d')} to {latest_date.strftime('%Y-%m-%d')})"
            ),
            use_container_width=True
        )
        
        # Summary statistics
        if len(ts_data) > 1:
            col1, col2, col3, col4 = st.columns(4)
            with col1:
                st.metric("Average Balance", format_billions(ts_data["closing"].mean()))
            with col2:
                st.metric("Maximum Balance", format_billions(ts_data["closing"].max()))
            with col3:
                st.metric("Minimum Balance", format_billions(ts_data["closing"].min()))
            with col4:
                volatility = ts_data["closing"].std()
                st.metric("Volatility (σ)", format_billions(volatility))
    
    # Footer
    st.markdown("---")
    st.markdown("""
    <div style="text-align: center; color: #6b7280; padding: 1rem;">
        <p><strong>Data Source:</strong> U.S. Treasury Fiscal Data API</p>
        <p><em>Treasury General Account (TGA) Daily Operating Cash Balance</em></p>
        <p>🔄 Data updates daily • Last refresh: {}</p>
    </div>
    """.format(datetime.now().strftime("%Y-%m-%d %H:%M UTC")), unsafe_allow_html=True)

if __name__ == "__main__":
    main()
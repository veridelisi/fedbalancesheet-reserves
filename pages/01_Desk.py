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

@st.cache_data(ttl=3600)  # Cache for 1 hour
def fetch_fed_repo_data():
    """
    Fetch Federal Reserve repo operations data
    """
    # Try multiple approaches to get data
    base_url = "https://markets.newyorkfed.org/api/rp"
    
    # URLs to try in order of preference
    urls_to_try = [
        f"{base_url}/repo/all/results/last/500.json",  # Reduced number
        f"{base_url}/repo/all/results/last/100.json",  # Even smaller
        f"{base_url}/repo/all/results/last/50.json",   # Smallest
    ]
    
    headers = {
        'User-Agent': 'Mozilla/5.0 (Windows NT 10.0; Win64; x64) AppleWebKit/537.36 (KHTML, like Gecko) Chrome/91.0.4472.124 Safari/537.36',
        'Accept': 'application/json',
        'Accept-Language': 'en-US,en;q=0.9'
    }
    
    for url in urls_to_try:
        try:
            st.info(f"Trying: {url}")
            response = requests.get(url, headers=headers, timeout=30)
            response.raise_for_status()
            data = response.json()
            st.success(f"Successfully fetched data from: {url}")
            return data
        except requests.exceptions.RequestException as e:
            st.warning(f"Failed to fetch from {url}: {e}")
            continue
    
    # If all URLs fail, try a fallback with different structure
    try:
        fallback_url = f"{base_url}/repo/all/results/last/50"  # Without .json
        st.info(f"Trying fallback: {fallback_url}")
        response = requests.get(fallback_url, headers=headers, timeout=30)
        response.raise_for_status()
        return response.json()
    except requests.exceptions.RequestException as e:
        st.error(f"All attempts failed. Last error: {e}")
        return None

def process_repo_data(data):
    """
    Process repo operations data
    """
    if not data or 'repo' not in data or 'operations' not in data['repo']:
        return pd.DataFrame()
    
    operations = data['repo']['operations']
    results = []
    
    for operation in operations:
        op_date = datetime.strptime(operation['operationDate'], '%Y-%m-%d')
        total_accepted = operation['totalAmtAccepted']
        
        if total_accepted == 0:
            continue
            
        # Calculate weighted average rate across all security types
        total_weighted_rate = 0
        total_amount = 0
        
        for detail in operation['details']:
            if detail['amtAccepted'] > 0 and 'percentWeightedAverageRate' in detail:
                amount = detail['amtAccepted']
                rate = detail['percentWeightedAverageRate']
                total_weighted_rate += rate * amount
                total_amount += amount
        
        # Calculate overall weighted average rate
        if total_amount > 0:
            overall_weighted_rate = total_weighted_rate / total_amount
        else:
            overall_weighted_rate = None
            
        results.append({
            'operation_date': op_date,
            'operation_id': operation['operationId'],
            'term': operation['term'],
            'total_accepted_amount': total_accepted,
            'weighted_average_rate': overall_weighted_rate,
            'amount_billions': total_accepted / 1_000_000_000
        })
    
    df = pd.DataFrame(results)
    
    if not df.empty:
        df = df.sort_values('operation_date', ascending=False)
        df = df.reset_index(drop=True)
    
    return df

def create_bar_chart(df_filtered):
    """
    Create bar chart for repo operations since 2025-01-01
    """
    if df_filtered.empty:
        return None
    
    # Group by date and sum amounts (in case multiple operations per day)
    daily_data = df_filtered.groupby('operation_date').agg({
        'weighted_average_rate': 'mean',
        'amount_billions': 'sum'
    }).reset_index()
    
    # Create bar chart
    fig = go.Figure()
    
    # Add bar chart for amounts
    fig.add_trace(go.Bar(
        x=daily_data['operation_date'],
        y=daily_data['amount_billions'],
        name='Accepted Amount ($B)',
        marker_color='lightblue',
        yaxis='y',
        hovertemplate='Date: %{x}<br>Amount: $%{y:.2f}B<br>Rate: %{customdata:.3f}%<extra></extra>',
        customdata=daily_data['weighted_average_rate']
    ))
    
    # Add line for rates on secondary y-axis
    fig.add_trace(go.Scatter(
        x=daily_data['operation_date'],
        y=daily_data['weighted_average_rate'],
        mode='lines+markers',
        name='Weighted Avg Rate (%)',
        line=dict(color='red', width=2),
        marker=dict(size=6),
        yaxis='y2',
        hovertemplate='Date: %{x}<br>Rate: %{y:.3f}%<br>Amount: $%{customdata:.2f}B<extra></extra>',
        customdata=daily_data['amount_billions']
    ))
    
    # Update layout
    fig.update_layout(
        title='Fed Repo Operations Since January 1, 2025',
        xaxis_title='Date',
        yaxis=dict(
            title='Accepted Amount ($ Billions)',
            side='left',
            range=[0, daily_data['amount_billions'].max() * 1.1]
        ),
        yaxis2=dict(
            title='Weighted Average Rate (%)',
            side='right',
            overlaying='y',
            range=[daily_data['weighted_average_rate'].min() * 0.95, 
                   daily_data['weighted_average_rate'].max() * 1.05]
        ),
        hovermode='x unified',
        height=500,
        showlegend=True,
        legend=dict(
            orientation="h",
            yanchor="bottom",
            y=1.02,
            xanchor="right",
            x=1
        )
    )
    
    return fig

# Main Streamlit App
def main():
    st.title("🏛️ Federal Reserve Repo Operations Dashboard")
    
    # Add option to use sample data if API fails
    use_sample_data = st.sidebar.checkbox("Use Sample Data (if API fails)")
    
    if use_sample_data:
        st.info("Using sample data from your original JSON file")
        # You can paste your JSON data here as fallback
        sample_data = {
            "repo": {
                "operations": [
                    # Sample operations from your original data
                    {
                        "operationId": "RP 091625 1",
                        "operationDate": "2025-09-16",
                        "term": "Overnight",
                        "totalAmtAccepted": 1500000000,
                        "details": [
                            {
                                "securityType": "Treasury",
                                "amtAccepted": 1500000000,
                                "percentWeightedAverageRate": 4.5
                            }
                        ]
                    }
                    # Add more sample operations here
                ]
            }
        }
        data = sample_data
    else:
        # Fetch data from API
        with st.spinner("Fetching latest Fed repo data..."):
            data = fetch_fed_repo_data()
    
    if data is None:
        st.error("Failed to fetch data from NY Fed API. Try enabling 'Use Sample Data' in the sidebar.")
        return
    
    # Process data
    df = process_repo_data(data)
    
    if df.empty:
        st.error("No repo operations data available")
        return
    
    # Filter for operations with rates
    df_with_rates = df[df['weighted_average_rate'].notna()].copy()
    
    if df_with_rates.empty:
        st.error("No repo operations with rates found")
        return
    
    # 1. Latest operation info (first row)
    st.header("📈 Latest Repo Operation")
    
    latest_operation = df_with_rates.iloc[0]
    
    col1, col2, col3, col4 = st.columns(4)
    
    with col1:
        st.metric(
            label="Operation Date",
            value=latest_operation['operation_date'].strftime("%Y-%m-%d")
        )
    
    with col2:
        st.metric(
            label="Weighted Average Rate",
            value=f"{latest_operation['weighted_average_rate']:.3f}%"
        )
    
    with col3:
        st.metric(
            label="Accepted Amount",
            value=f"${latest_operation['amount_billions']:.2f}B"
        )
    
    with col4:
        st.metric(
            label="Term",
            value=latest_operation['term']
        )
    
    st.divider()
    
    # 2. Chart since 2025-01-01 (second row)
    st.header("📊 Repo Operations Since January 1, 2025")
    
    # Filter data from 2025-01-01
    start_date = datetime(2025, 1, 1)
    df_2025 = df_with_rates[df_with_rates['operation_date'] >= start_date].copy()
    
    if df_2025.empty:
        st.warning("No repo operations found since January 1, 2025")
    else:
        # Create and display chart
        fig = create_bar_chart(df_2025)
        
        if fig:
            st.plotly_chart(fig, use_container_width=True)
            
            # Summary statistics for 2025
            st.subheader("📋 2025 Summary Statistics")
            col1, col2, col3, col4 = st.columns(4)
            
            with col1:
                st.metric(
                    label="Total Operations",
                    value=len(df_2025)
                )
            
            with col2:
                st.metric(
                    label="Average Rate",
                    value=f"{df_2025['weighted_average_rate'].mean():.3f}%"
                )
            
            with col3:
                st.metric(
                    label="Total Amount",
                    value=f"${df_2025['amount_billions'].sum():.2f}B"
                )
            
            with col4:
                st.metric(
                    label="Avg Amount/Operation",
                    value=f"${df_2025['amount_billions'].mean():.2f}B"
                )
        else:
            st.error("Could not create chart")
    
    # Optional: Show raw data table
    with st.expander("📋 View Recent Operations Data"):
        st.dataframe(
            df_2025[['operation_date', 'operation_id', 'term', 'weighted_average_rate', 'amount_billions']].head(10),
            column_config={
                'operation_date': 'Date',
                'operation_id': 'Operation ID',
                'term': 'Term',
                'weighted_average_rate': st.column_config.NumberColumn(
                    'Rate (%)',
                    format='%.3f'
                ),
                'amount_billions': st.column_config.NumberColumn(
                    'Amount ($B)',
                    format='%.2f'
                )
            },
            hide_index=True
        )

if __name__ == "__main__":
    main()
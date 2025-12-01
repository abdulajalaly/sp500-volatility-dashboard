import streamlit as st
import yfinance as yf
import pandas as pd
import numpy as np
import plotly.graph_objects as go
from datetime import datetime, timedelta

# --- Page Config ---
st.set_page_config(page_title="Tech Volatility Dashboard", layout="wide")

# --- Constants ---
# A representative list of major tech companies (expandable to 50)
TECH_TICKERS = [
    'AAPL', 'MSFT', 'NVDA', 'GOOGL', 'AMZN', 'META', 'TSLA', 
    'AMD', 'INTC', 'CRM', 'ORCL', 'ADBE', 'CSCO', 'NFLX', 'IBM'
]

# --- 1. Data Extraction ---
@st.cache_data
def load_data(tickers, period="5y"):
    """
    Fetches stock data for the provided tickers.
    Uses st.cache_data to avoid re-fetching on every interaction.
    """
    data = yf.download(tickers, period=period, group_by='ticker', auto_adjust=True)
    return data

# --- 2. Financial Calculations ---
def calculate_metrics(df, ticker):
    """
    Calculates Moving Averages and Volatility for a specific ticker.
    """
    # Handle MultiIndex if necessary, or select specific ticker data
    try:
        stock_df = df[ticker].copy()
    except KeyError:
        return None

    # Calculate Daily Returns
    stock_df['Daily Return'] = stock_df['Close'].pct_change()

    # Calculate 21-day Rolling Volatility (Annualized)
    # Formula: StDev of Returns * Sqrt(252 trading days)
    stock_df['Volatility'] = stock_df['Daily Return'].rolling(window=21).std() * np.sqrt(252)

    # Calculate Moving Averages
    stock_df['SMA_50'] = stock_df['Close'].rolling(window=50).mean()
    stock_df['SMA_200'] = stock_df['Close'].rolling(window=200).mean()

    return stock_df
def calculate_correlation(df, tickers):
    """
    Calculates the correlation matrix of daily returns for the list of tickers.
    """
    # Create a new DataFrame just for Close prices
    close_prices = pd.DataFrame()
    
    for ticker in tickers:
        try:
            # Handle the multi-level column structure from yfinance
            if ticker in df.columns:
                 # Calculate daily return immediately to normalize data
                close_prices[ticker] = df[ticker]['Close'].pct_change()
        except KeyError:
            continue
            
    # Drop the first row (NaNs from pct_change) and calculate correlation
    return close_prices.dropna().corr()

# --- 3. Dashboard Layout ---
def main():
    st.title("S&P 500 Tech Sector: Volatility Analysis")
    st.markdown("### Tracking Risk & Trends During Economic Shifts (2020-2024)")

    # Sidebar Controls
    st.sidebar.header("Configuration")
    selected_ticker = st.sidebar.selectbox("Select Tech Company", TECH_TICKERS)
    
    # Load Data
    with st.spinner('Loading 5 years of market data...'):
        raw_data = load_data(TECH_TICKERS)
    
    # Process Data for Selected Ticker
    processed_data = calculate_metrics(raw_data, selected_ticker)

    if processed_data is None:
        st.error("Error loading data for this ticker.")
        return

    # --- KPI Row ---
    latest_close = processed_data['Close'].iloc[-1]
    latest_volatility = processed_data['Volatility'].iloc[-1]
    ytd_return = ((processed_data['Close'].iloc[-1] / processed_data['Close'].iloc[-252]) - 1) * 100

    col1, col2, col3 = st.columns(3)
    col1.metric("Current Price", f"${latest_close:.2f}")
    col2.metric("Current Volatility (Risk)", f"{latest_volatility:.2%}")
    col3.metric("1-Year Return", f"{ytd_return:.2f}%")

    # --- Chart 1: Price & Moving Averages ---
    st.subheader(f"{selected_ticker} Price Trends & Moving Averages")
    
    fig_price = go.Figure()
    fig_price.add_trace(go.Scatter(x=processed_data.index, y=processed_data['Close'], mode='lines', name='Price'))
    fig_price.add_trace(go.Scatter(x=processed_data.index, y=processed_data['SMA_50'], mode='lines', name='50-Day SMA', line=dict(dash='dash')))
    fig_price.add_trace(go.Scatter(x=processed_data.index, y=processed_data['SMA_200'], mode='lines', name='200-Day SMA', line=dict(color='orange')))
    
    fig_price.update_layout(height=500, xaxis_title="Date", yaxis_title="Price (USD)")
    st.plotly_chart(fig_price, use_container_width=True)

    # --- Chart 2: Volatility Analysis ---
    st.subheader("Rolling Volatility (Risk Analysis)")
    st.caption("Spikes indicate periods of high market fear or uncertainty.")

    fig_vol = go.Figure()
    fig_vol.add_trace(go.Scatter(x=processed_data.index, y=processed_data['Volatility'], mode='lines', name='Volatility', line=dict(color='red')))
    
    # Highlight 2024 area if relevant
    fig_vol.add_vrect(
        x0=datetime(2024, 1, 1), x1=datetime.now(),
        annotation_text="2024 Economic Shift", annotation_position="top left",
        fillcolor="green", opacity=0.1, line_width=0
    )

    fig_vol.update_layout(height=400, xaxis_title="Date", yaxis_title="Annualized Volatility")
    st.plotly_chart(fig_vol, use_container_width=True)

    # --- Raw Data View ---
    with st.expander("View Underlying Data"):
        st.dataframe(processed_data.tail(50))
# --- Chart 3: Correlation Heatmap ---
    st.markdown("---")
    st.subheader("Sector Correlation Matrix")
    st.caption("Identify how closely these tech stocks move together. High correlation (near 1) means they move in sync.")

    # Calculate Correlation
    corr_matrix = calculate_correlation(raw_data, TECH_TICKERS)

    # Plot Heatmap
    fig_corr = go.Figure(data=go.Heatmap(
        z=corr_matrix.values,
        x=corr_matrix.columns,
        y=corr_matrix.index,
        colorscale='Viridis',
        zmin=-1, zmax=1,
        text=corr_matrix.values.round(2),
        texttemplate="%{text}"
    ))
    
    fig_corr.update_layout(height=600, width=800)
    st.plotly_chart(fig_corr, use_container_width=True)
if __name__ == "__main__":
    main()
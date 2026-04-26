"""Streamlit dashboard for monitoring"""
import streamlit as st
import pandas as pd
import plotly.graph_objects as go
from plotly.subplots import make_subplots
from datetime import datetime, timedelta

from ...core.rabbitmq_client import RabbitMQClient
from ...notifications.reports import ReportGenerator
from ...agents.registry import AgentRegistry
from ...config.base import BaseConfig


def main():
    st.set_page_config(
        page_title="Forex Bot Dashboard",
        page_icon="📈",
        layout="wide"
    )

    st.title("📈 Forex Trading Bot Dashboard")

    # Sidebar
    with st.sidebar:
        st.header("Controls")
        if st.button("Refresh Data"):
            st.rerun()

        st.subheader("Bot Status")
        status_placeholder = st.empty()

    # Main content
    col1, col2, col3 = st.columns(3)

    with col1:
        st.metric("Total Equity", "$10,450", delta="$450")
    with col2:
        st.metric("Daily P&L", "+$125", delta="+1.2%")
    with col3:
        st.metric("Active Agents", "5 / 5")

    # Tabs
    tab1, tab2, tab3 = st.tabs(["Overview", "Agents", "Trades"])

    with tab1:
        st.subheader("Equity Curve")
        # Placeholder chart
        chart_placeholder = st.empty()

    with tab2:
        st.subheader("Agent Performance")
        agent_table = st.empty()

    with tab3:
        st.subheader("Recent Trades")
        trades_table = st.empty()

    # Simulate data (would connect to RabbitMQ/DB)
    render_demo_content(chart_placeholder, agent_table, trades_table, status_placeholder)


def render_demo_content(chart_ph, agent_ph, trades_ph, status_ph):
    """Render demo placeholder content"""
    # Equity curve
    dates = pd.date_range(datetime.now() - timedelta(days=30), periods=30)
    equity = [10000 + i*50 + (i%5)*20 for i in range(30)]

    fig = go.Figure()
    fig.add_trace(go.Scatter(x=dates, y=equity, mode='lines', name='Equity'))
    fig.update_layout(title="Equity Over Time", xaxis_title="Date", yaxis_title="USD")
    chart_ph.plotly_chart(fig, use_container_width=True)

    # Agent table
    agents_data = [
        {"ID": 1, "Symbol": "EURUSD", "State": "TRADING", "Equity": 2100, "Win Rate": "58%"},
        {"ID": 2, "Symbol": "GBPUSD", "State": "READY", "Equity": 2050, "Win Rate": "52%"},
        {"ID": 3, "Symbol": "XAUUSD", "State": "TRADING", "Equity": 2150, "Win Rate": "61%"},
    ]
    agent_ph.dataframe(pd.DataFrame(agents_data), use_container_width=True)

    # Trades table
    trades_data = [
        {"Time": "10:30:15", "Agent": 1, "Symbol": "EURUSD", "Side": "BUY", "PnL": "+$45.20"},
        {"Time": "10:15:42", "Agent": 3, "Symbol": "XAUUSD", "Side": "SELL", "PnL": "-$22.10"},
        {"Time": "09:45:11", "Agent": 2, "Symbol": "GBPUSD", "Side": "BUY", "PnL": "+$33.50"},
    ]
    trades_ph.dataframe(pd.DataFrame(trades_data), use_container_width=True)

    # Status
    status_ph.success("● Bot Running")


if __name__ == "__main__":
    main()

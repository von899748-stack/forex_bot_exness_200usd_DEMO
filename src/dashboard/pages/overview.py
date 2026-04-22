"""Overview page"""
import streamlit as st
import pandas as pd
import plotly.graph_objects as go
from datetime import datetime, timedelta


def render():
    st.header("Portfolio Overview")

    # Placeholder metrics
    col1, col2, col3, col4 = st.columns(4)
    with col1:
        st.metric("Total Equity", "$20,350", delta="$350 (1.7%)")
    with col2:
        st.metric("Daily P&L", "+$125", delta="+0.6%")
    with col3:
        st.metric("Win Rate", "56%", delta="+2%")
    with col4:
        st.metric("Active Agents", "5 / 5", delta="")

    # Equity curve
    dates = pd.date_range(datetime.now() - timedelta(days=30), periods=30)
    equity = [20000 + i*80 + (i%7)*50 for i in range(30)]

    fig = go.Figure()
    fig.add_trace(go.Scatter(x=dates, y=equity, mode='lines', name='Equity', line=dict(color='green')))
    fig.update_layout(
        title="30-Day Equity Curve",
        xaxis_title="Date",
        yaxis_title="Equity ($)",
        height=400
    )
    st.plotly_chart(fig, use_container_width=True)

    # Recent alerts
    st.subheader("Recent Alerts")
    st.info("All systems operational")

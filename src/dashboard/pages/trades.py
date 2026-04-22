"""Trades page - shows recent trade history"""
import streamlit as st
import pandas as pd
from datetime import datetime, timedelta


def render():
    st.header("Trade History")

    # Placeholder trades
    trades = [
        {"Time": "10:30:15", "Agent": 1, "Symbol": "EURUSD", "Side": "BUY", "Entry": 1.0850, "Exit": 1.0870,
         "SL": 1.0820, "TP": 1.0900, "PnL": "+$45.20", "Reason": "signal_BUY"},
        {"Time": "10:15:42", "Agent": 3, "Symbol": "XAUUSD", "Side": "SELL", "Entry": 2330.5, "Exit": 2328.2,
         "SL": 2333.0, "TP": 2325.0, "PnL": "-$22.10", "Reason": "signal_SELL"},
        {"Time": "09:45:11", "Agent": 2, "Symbol": "GBPUSD", "Side": "BUY", "Entry": 1.2705, "Exit": 1.2725,
         "SL": 1.2680, "TP": 1.2750, "PnL": "+$33.50", "Reason": "signal_BUY"},
        {"Time": "09:20:08", "Agent": 1, "Symbol": "EURUSD", "Side": "SELL", "Entry": 1.0845, "Exit": 1.0830,
         "SL": 1.0870, "TP": 1.0800, "PnL": "+$25.00", "Reason": "signal_SELL"},
        {"Time": "08:55:33", "Agent": 4, "Symbol": "EURUSD", "Side": "BUY", "Entry": 1.0840, "Exit": 1.0835,
         "SL": 1.0810, "TP": 1.0880, "PnL": "-$8.50", "Reason": "signal_BUY"},
    ]

    df = pd.DataFrame(trades)
    st.dataframe(df, use_container_width=True)

    # Filters
    with st.expander("Filters"):
        col1, col2 = st.columns(2)
        with col1:
            st.selectbox("Symbol", ["All", "EURUSD", "GBPUSD", "XAUUSD"])
        with col2:
            st.selectbox("Agent", ["All", "1", "2", "3", "4", "5"])

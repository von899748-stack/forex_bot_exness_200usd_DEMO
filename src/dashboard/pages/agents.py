"""Agents page - shows individual agent performance"""
import streamlit as st
import pandas as pd


def render():
    st.header("Agent Performance")

    # Placeholder data
    data = [
        {"ID": 1, "Symbol": "EURUSD", "State": "🟢 Trading", "Equity": "$2,150", "P&L": "+$150", "Win Rate": "58%", "Losses": 1},
        {"ID": 2, "Symbol": "GBPUSD", "State": "🟢 Trading", "Equity": "$2,080", "P&L": "+$80", "Win Rate": "52%", "Losses": 0},
        {"ID": 3, "Symbol": "XAUUSD", "State": "🟡 Paused", "Equity": "$2,050", "P&L": "+$50", "Win Rate": "55%", "Losses": 2},
        {"ID": 4, "Symbol": "EURUSD", "State": "🟢 Trading", "Equity": "$2,120", "P&L": "+$120", "Win Rate": "60%", "Losses": 0},
        {"ID": 5, "Symbol": "GBPUSD", "State": "🔴 Stopped", "Equity": "$1,950", "P&L": "-$50", "Win Rate": "45%", "Losses": 3},
    ]

    df = pd.DataFrame(data)
    st.dataframe(df, use_container_width=True)

    st.subheader("Agent Details")
    st.info("Select an agent to view detailed performance metrics (not implemented)")

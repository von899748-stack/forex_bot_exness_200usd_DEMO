"""Backtest configuration"""
from .base import BaseConfig, RiskConfig
import os


class BacktestConfig(BaseConfig):
    """Configuration for backtesting"""
    mode: str = "backtest"
    broker_mode: str = "backtest"

    def __init__(self, **kwargs):
        super().__init__(**kwargs)
        # Set backtest date range
        self.backtest_start = os.getenv("BACKTEST_START", "2024-01-01")
        self.backtest_end = os.getenv("BACKTEST_END", "2024-12-31")
        # Backtest-specific settings
        self.initial_balance = 200.0
        self.commission_per_lot = 7.0
        self.slippage_pips = 0.5

        # Override risk settings
        self.risk = RiskConfig(
            total_capital=self.initial_balance,
            max_agents=5,
            risk_base=0.01,
            dynamic_risk=True,
            max_risk=0.02,
            min_risk=0.005,
            max_consecutive_losses=3,
            drawdown_limit=0.10,
        )

"""Live trading configuration - extends base with real MT5 account"""
import os
from .base import BaseConfig, RiskConfig, MT5Config


class LiveConfig(BaseConfig):
    """Configuration for live trading with real money"""
    mode: str = "live"
    broker_mode: str = "live"

    def __init__(self, **kwargs):
        super().__init__(**kwargs)
        # Override with live-specific risk settings
        self.risk = RiskConfig(
            total_capital=self.risk.total_capital,
            max_agents=3,  # Fewer agents for live
            risk_base=0.005,  # More conservative (0.5%)
            dynamic_risk=True,
            max_risk=0.01,
            min_risk=0.0025,
            max_consecutive_losses=2,  # Tighter stop
            drawdown_limit=0.05,
        )
        # Use real MT5 credentials
        self.mt5 = MT5Config(
            login=int(os.getenv("MT5_LOGIN", "0")),
            password=os.getenv("MT5_PASSWORD", ""),
            server=os.getenv("MT5_SERVER", "Exness-Real"),
            path=os.getenv("MT5_PATH", ""),
        )

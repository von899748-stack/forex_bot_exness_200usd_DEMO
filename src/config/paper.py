"""Paper trading configuration - demo mode using simulated broker"""
from .base import BaseConfig, RiskConfig


class PaperConfig(BaseConfig):
    """Configuration for paper trading (demo)"""
    mode: str = "demo"
    broker_mode: str = "demo"

    def __post_init__(self):
        # Demo uses base risk settings but with demo account
        # Can be more aggressive since no real money
        self.risk = RiskConfig(
            total_capital=200,
            max_agents=5,
            risk_base=0.01,  # 1% risk per trade
            dynamic_risk=True,
            max_risk=0.02,
            min_risk=0.005,
            max_consecutive_losses=3,
            drawdown_limit=0.10,
        )

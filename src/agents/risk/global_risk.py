"""Global risk manager - portfolio-level risk controls"""
from typing import List, Optional
from dataclasses import dataclass, field
from ...core.logger import get_agent_logger
from ...core.types import AgentStatus
from ...config.base import BaseConfig


@dataclass
class GlobalRiskState:
    """Global portfolio state"""
    total_equity: float
    total_peak: float
    total_drawdown: float
    max_total_drawdown: float
    max_concurrent_trades: int
    current_trades: int
    agents_in_drawdown: int
    is_paused: bool
    reason: str = ""


class GlobalRiskManager:
    """
    Enforces portfolio-level risk limits.
    Monitors aggregate drawdown and can pause all trading.
    """

    def __init__(self, config: BaseConfig):
        self.config = config
        self.logger = get_agent_logger(0)
        self.state = GlobalRiskState(
            total_equity=config.risk.total_capital,
            total_peak=config.risk.total_capital,
            total_drawdown=0.0,
            max_total_drawdown=0.20,  # 20% max portfolio drawdown
            max_concurrent_trades=10,
            current_trades=0,
            agents_in_drawdown=0,
            is_paused=False,
        )
        self.agent_statuses: List[AgentStatus] = []

    def update_agent_status(self, status: AgentStatus):
        """Update agent status and recalc global state"""
        self.agent_statuses.append(status)
        # Recalculate aggregate metrics
        total_eq = sum(s.equity for s in self.agent_statuses if s.equity)
        total_peak = max(s.peak_equity for s in self.agent_statuses if s.peak_equity)
        self.state.total_equity = total_eq
        self.state.total_peak = total_peak
        if total_peak > 0:
            self.state.total_drawdown = (total_peak - total_eq) / total_peak
        self.state.current_trades = sum(
            1 for s in self.agent_statuses if s.current_trade is not None
        )
        self.state.agents_in_drawdown = sum(
            1 for s in self.agent_statuses if s.drawdown > 0.1
        )

    def check_global_limits(self) -> tuple[bool, str]:
        """
        Check if any global risk limit is breached

        Returns:
            (should_pause, reason)
        """
        # Check max drawdown
        if self.state.total_drawdown >= self.state.max_total_drawdown:
            return True, f"Portfolio drawdown {self.state.total_drawdown:.2%} exceeds limit"

        # Check too many concurrent trades
        if self.state.current_trades >= self.state.max_concurrent_trades:
            return True, f"Max concurrent trades {self.state.max_concurrent_trades} reached"

        # Many agents in drawdown
        if self.state.agents_in_drawdown >= len(self.agent_statuses) * 0.5:
            return True, "Many agents in drawdown - global stop"

        return False, ""

    def should_pause_new_trades(self) -> bool:
        """Decide if new trades should be paused globally"""
        should_pause, reason = self.check_global_limits()
        if should_pause:
            self.state.is_paused = True
            self.state.reason = reason
            self.logger.warning(f"Global risk pause: {reason}")
        return should_pause

    def resume_trading(self):
        """Manually resume trading after pause"""
        self.state.is_paused = False
        self.state.reason = ""
        self.logger.info("Global trading resumed")

    def get_state(self) -> GlobalRiskState:
        return self.state

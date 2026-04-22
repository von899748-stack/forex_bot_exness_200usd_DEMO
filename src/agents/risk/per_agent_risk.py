"""Per-agent risk manager with dynamic risk adjustment"""
from typing import Optional
from ...core.logger import get_agent_logger
from ...core.utils import calculate_dynamic_risk, calculate_lot_size
from ...config.base import BaseConfig


class PerAgentRiskManager:
    """
    Manages risk for a single agent using dynamic risk scaling.
    """

    def __init__(self, config: BaseConfig):
        self.config = config
        self.logger = get_agent_logger(0)

    def calculate_risk(
        self,
        equity: float,
        peak_equity: float,
        consecutive_losses: int,
        signal_confidence: float = 0.5
    ) -> float:
        """
        Calculate risk percentage for next trade

        Returns:
            Risk as decimal (e.g., 0.01 = 1%)
        """
        if not self.config.risk.dynamic_risk:
            return self.config.risk.base_risk

        # Base risk from config
        base = self.config.risk.base_risk

        # Using utility function
        risk = calculate_dynamic_risk(
            current_equity=equity,
            peak_equity=peak_equity,
            drawdown_limit=self.config.risk.drawdown_limit,
            base_risk=base,
            min_risk=self.config.risk.min_risk,
            max_risk=self.config.risk.max_risk,
            consecutive_losses=consecutive_losses
        )

        # Adjust by signal confidence (optional)
        risk *= (0.5 + 0.5 * signal_confidence)  # scale by confidence

        self.logger.debug(f"Calculated risk: {risk:.4f} (equity={equity:.2f}, dd={equity/peak_equity if peak_equity>0 else 0:.2%})")
        return risk

    def calculate_lot_size(
        self,
        capital: float,
        risk_percent: float,
        sl_pips: float,
        pip_value: float,
        symbol: str = "EURUSD"
    ) -> float:
        """
        Calculate lot size based on risk parameters

        Args:
            capital: Account capital
            risk_percent: Risk per trade as decimal
            sl_pips: Stop loss in pips
            pip_value: Value per pip per standard lot
            symbol: Trading symbol

        Returns:
            Lot size
        """
        if sl_pips <= 0 or pip_value <= 0:
            return 0.01

        lot = calculate_lot_size(
            capital=capital,
            risk_percent=risk_percent,
            sl_pips=sl_pips,
            pip_value_per_lot=pip_value,
            min_lot=self.config.symbols.default_min_lot,
            max_lot=self.config.symbols.default_max_lot,
            lot_step=self.config.symbols.default_lot_step
        )

        self.logger.debug(f"Calculated lot size: {lot:.2f} lots (capital={capital}, risk={risk_percent:.2%}, SL={sl_pips} pips)")
        return lot

    def validate_risk(self, risk: float) -> bool:
        """Validate risk is within allowed bounds"""
        return self.config.risk.min_risk <= risk <= self.config.risk.max_risk

    def clamp_risk(self, risk: float) -> float:
        """Clamp risk to configured limits"""
        return max(self.config.risk.min_risk, min(self.config.risk.max_risk, risk))

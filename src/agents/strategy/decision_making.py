"""Decision making - final trading decision"""
from typing import Dict, Any, Optional
from ...core.types import Signal, SignalType, MarketData
from ...core.logger import get_agent_logger


class DecisionMaking:
    """Makes final trading decisions from fused signals and analysis"""

    def __init__(self, min_confidence: float = 0.6):
        self.min_confidence = min_confidence
        self.logger = get_agent_logger(0)

    async def decide(
        self,
        analysis: Dict[str, Any],
        signal: Signal
    ) -> Optional[Signal]:
        """
        Make final go/no-go decision

        Args:
            analysis: Full analysis dict from perception
            signal: Fused signal

        Returns:
            Adjusted signal or None if no trade
        """
        if signal.confidence < self.min_confidence:
            return None

        # Additional sanity checks
        if not self._validate_signal(signal, analysis):
            return None

        # Ensure risk-reward ratio
        if signal.take_profit_pips <= signal.stop_loss_pips:
            # TP should be at least 1.5x SL
            signal.take_profit_pips = signal.stop_loss_pips * 1.5

        return signal

    def _validate_signal(self, signal: Signal, analysis: Dict[str, Any]) -> bool:
        """Validate signal against market conditions"""
        # Check for extreme volatility
        atr = analysis.get("atr")
        if atr is not None and atr > 0.002:  # 20 pips ATR for EURUSD is high
            self.logger.debug("High volatility - skipping")
            return False

        # Check that trend aligns with signal
        trend = analysis.get("trend", "sideways")
        if signal.is_bullish and trend == "downtrend":
            self.logger.debug("Bullish signal in downtrend - skipping")
            return False
        if signal.is_bearish and trend == "uptrend":
            self.logger.debug("Bearish signal in uptrend - skipping")
            return False

        return True

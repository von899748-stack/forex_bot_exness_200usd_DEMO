"""Self-correction - adjusts strategy based on past mistakes"""
from typing import Dict, Any, Optional
from dataclasses import dataclass
from datetime import datetime, timedelta
import math

from ...core.logger import get_agent_logger
from ...config.base import LearningConfig


@dataclass
class CorrectionRule:
    """A rule to correct a specific mistake"""
    condition: str  # e.g., "session_asian && side_buy"
    action: str    # e.g., "reduce_risk_by", "skip_if"
    value: float   # parameter value
    confidence: float = 0.5


class SelfCorrector:
    """
    Learns from mistakes and applies corrections to future trades.
    """

    def __init__(self, config: LearningConfig):
        self.config = config
        self.logger = get_agent_logger(0)
        self.rules: Dict[str, CorrectionRule] = {}
        self.correction_history = []

    async def analyze_trade(self, trade: Dict[str, Any]) -> Optional[CorrectionRule]:
        """Analyze a failed trade and generate a correction rule"""
        if trade.get('pnl', 0) >= 0:
            return None

        # Extract context
        session = self._get_session(trade['entry_time'])
        reason = trade.get('reason', '')
        symbol = trade.get('symbol', '')

        # Simple rule generation - in real system use ML
        condition = f"session_{session}"
        action = "reduce_risk_by"
        value = 0.5  # cut risk in half for this session

        rule = CorrectionRule(
            condition=condition,
            action=action,
            value=value,
            confidence=0.3
        )
        self.rules[condition] = rule
        self.logger.info(f"Generated correction rule: {condition} -> {action} {value}")
        return rule

    def apply_corrections(self, features: Dict[str, Any]) -> Dict[str, Any]:
        """
        Apply relevant corrections to trade features.

        Returns:
            Adjusted features dict
        """
        adjusted = features.copy()
        session = features.get('session', 'unknown')
        condition = f"session_{session}"

        if condition in self.rules:
            rule = self.rules[condition]
            if rule.action == "reduce_risk_by":
                adjusted['risk_multiplier'] = rule.value
            elif rule.action == "skip_if":
                adjusted['skip'] = True
            self.logger.debug(f"Applied correction: {rule.condition}")

        return adjusted

    def _get_session(self, time: datetime) -> str:
        hour = time.hour
        if 0 <= hour < 8:
            return "asian"
        elif 8 <= hour < 16:
            return "european"
        else:
            return "american"

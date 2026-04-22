"""Loss minimizer - learns from losses to avoid similar future trades"""
from typing import Dict, Any, Optional
from dataclasses import dataclass
from datetime import datetime
import hashlib
import json

from ...core.logger import get_agent_logger
from ...core.types import Trade
from ...agents.memory.loss_memory import LossMemory, LossPattern
from ...config.base import LearningConfig


class LossMinimizer:
    """
    Learns from losing trades to minimize future losses.
    Uses loss memory repository to identify patterns.
    """

    def __init__(self, config: LearningConfig):
        self.config = config
        self.logger = get_agent_logger(0)
        self.loss_memory = LossMemory(config)
        self.pattern_weights: Dict[str, float] = {}  # pattern -> penalty weight

    async def process_trade(self, trade: Trade):
        """Process a completed trade for learning"""
        if trade.pnl is None:
            return

        if trade.pnl < 0:
            # Extract loss pattern
            pattern = self._extract_pattern(trade)
            self.loss_memory.record_loss(trade, pattern.get("regime", ""), pattern.get("spread", 0.0))
            self._update_weights(trade, pattern)

    def _extract_pattern(self, trade: Trade) -> Dict[str, Any]:
        """Extract features from losing trade"""
        pattern = {
            "symbol": trade.symbol,
            "side": trade.side.value,
            "reason": trade.reason,
            "regime": "unknown",
            "spread": trade.metadata.get("spread", 0.0),
            "slippage": trade.metadata.get("slippage_pips", 0.0),
            "session": self._get_session(trade.entry_time),
        }
        return pattern

    def _get_session(self, time: datetime) -> str:
        """Get trading session from time"""
        hour = time.hour
        if 0 <= hour < 8:
            return "asian"
        elif 8 <= hour < 16:
            return "european"
        else:
            return "american"

    def _update_weights(self, trade: Trade, pattern: Dict[str, Any]):
        """Update penalty weights for similar patterns"""
        key = self._pattern_key(pattern)
        current = self.pattern_weights.get(key, 0.0)
        # Increase penalty for this pattern
        self.pattern_weights[key] = min(1.0, current + 0.1)
        self.logger.debug(f"Updated pattern weight: {key} -> {self.pattern_weights[key]:.2f}")

    def _pattern_key(self, pattern: Dict[str, Any]) -> str:
        """Create hash key for pattern"""
        content = f"{pattern['symbol']}_{pattern['side']}_{pattern['reason']}_{pattern['session']}"
        return hashlib.md5(content.encode()).hexdigest()[:8]

    def get_penalty(self, features: Dict[str, Any]) -> float:
        """
        Get penalty factor for given features (reduce confidence)

        Returns:
            Multiplier in [0.5, 1.0] where <1 reduces confidence
        """
        key = self._pattern_key(features)
        weight = self.pattern_weights.get(key, 0.0)
        # Linear penalty: weight 0 -> 1.0, weight 1 -> 0.5
        return 1.0 - 0.5 * weight

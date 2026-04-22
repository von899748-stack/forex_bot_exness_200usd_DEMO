"""Noise filter - identifies trades that should not be learned from"""
from typing import Dict, Any, Tuple
from datetime import datetime
from dataclasses import dataclass

from ...core.types import Trade
from ...core.logger import get_agent_logger
from ...config.base import LearningConfig


class NoiseFilter:
    """
    Filters out losing trades caused by market noise.
    These trades are not used for learning.
    """

    def __init__(self, config: LearningConfig):
        self.config = config
        self.logger = get_agent_logger(0)

    def is_noise(self, trade: Trade, market_context: Dict[str, Any]) -> Tuple[bool, str]:
        """
        Check if a loss is due to noise

        Returns:
            (is_noise, reason)
        """
        if trade.pnl is None or trade.pnl >= 0:
            return False, ""

        reasons = []

        # Check spread
        spread_at_entry = market_context.get('spread', 0)
        normal_spread = market_context.get('normal_spread', 0.0001)
        if spread_at_entry > normal_spread * self.config.noise_spread_threshold:
            reasons.append(f"High spread: {spread_at_entry}")

        # Check slippage
        slippage = trade.metadata.get('slippage_pips', 0)
        if slippage > self.config.noise_slippage_threshold:
            reasons.append(f"High slippage: {slippage} pips")

        # Check if trade was very short-lived (< 10 seconds) and lost
        if trade.exit_time and trade.exit_time != trade.entry_time:
            duration = (trade.exit_time - trade.entry_time).total_seconds()
            if duration < 10 and trade.pnl < 0:
                reasons.append(f"Very short duration: {duration:.1f}s")

        # Check if stop was hit exactly (possible noise)
        if trade.exit_price and trade.stop_loss:
            if abs(trade.exit_price - trade.stop_loss) < 0.00001:
                reasons.append("Stop hit exactly")

        is_noise = len(reasons) > 0
        reason = "; ".join(reasons) if is_noise else ""
        return is_noise, reason

    def filter_losses(self, trades: list[Trade], market_contexts: list[Dict]) -> list[Trade]:
        """
        Filter a list of trades, returning only non-noise losses
        """
        filtered = []
        for trade, ctx in zip(trades, market_contexts):
            is_noise, _ = self.is_noise(trade, ctx)
            if not is_noise:
                filtered.append(trade)
        return filtered

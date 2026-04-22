"""Loss memory - tracks losing trades for learning"""
from typing import List, Dict, Any, Optional
from datetime import datetime, timedelta
from dataclasses import dataclass, field
import numpy as np

from ...core.types import Trade
from ...core.logger import get_agent_logger
from ...config.base import LearningConfig


@dataclass
class LossPattern:
    """Pattern extracted from a losing trade"""
    trade_id: str
    symbol: str
    entry_time: datetime
    exit_time: datetime
    pnl: float
    pnl_pct: float
    entry_price: float
    exit_price: float
    stop_loss: float
    take_profit: float
    market_regime: str = ""  # 'trending', 'ranging', 'volatile'
    spread_at_entry: float = 0.0
    slippage: float = 0.0
    reason: str = ""
    features: Dict[str, Any] = field(default_factory=dict)
    # Derived analysis
    was_stop_hit: bool = False
    was_noise: bool = False  # Filtered as noise
    noise_reason: str = ""


class LossMemory:
    """
    Stores and analyzes losing trades for learning.
    Only stores losses that pass the noise filter.
    """

    def __init__(
        self,
        config: LearningConfig,
        window_size: int = 100,
        correlation_threshold: float = 0.7
    ):
        self.config = config
        self.window_size = window_size
        self.correlation_threshold = correlation_threshold
        self.logger = get_agent_logger(0)

        self._losses: List[LossPattern] = []
        self._by_symbol: Dict[str, List[LossPattern]] = {}
        self._by_reason: Dict[str, List[LossPattern]] = {}

    def record_loss(self, trade: Trade, market_regime: str = "", spread: float = 0.0):
        """
        Record a losing trade if not filtered as noise

        Args:
            trade: The completed losing trade
            market_regime: Detected market regime
            spread: Spread at entry
        """
        if trade.pnl is None or trade.pnl >= 0:
            return

        # Check noise filter
        is_noise, noise_reason = self._check_noise(trade, spread)

        pattern = LossPattern(
            trade_id=str(trade.id),
            symbol=trade.symbol,
            entry_time=trade.entry_time,
            exit_time=trade.exit_time or datetime.utcnow(),
            pnl=trade.pnl,
            pnl_pct=trade.pnl_pct or 0.0,
            entry_price=trade.entry_price,
            exit_price=trade.exit_price or 0.0,
            stop_loss=trade.stop_loss,
            take_profit=trade.take_profit,
            market_regime=market_regime,
            spread_at_entry=spread,
            reason=trade.reason,
            features=trade.metadata or {},
            was_noise=is_noise,
            noise_reason=noise_reason,
        )

        self._losses.append(pattern)
        self._by_symbol.setdefault(trade.symbol, []).append(pattern)
        self._by_reason.setdefault(trade.reason, []).append(pattern)

        # Trim old entries
        if len(self._losses) > self.window_size:
            old = self._losses.pop(0)
            self._by_symbol[old.symbol].remove(old)
            if old.reason in self._by_reason:
                try:
                    self._by_reason[old.reason].remove(old)
                except ValueError:
                    pass

        self.logger.debug(f"Recorded loss: {trade.symbol} {trade.pnl:.2f} (noise: {is_noise})")

    def _check_noise(self, trade: Trade, spread: float) -> tuple[bool, str]:
        """
        Check if loss is due to market noise

        Returns:
            (is_noise, reason)
        """
        # Check spread
        if spread > trade.entry_price * 0.001:  # 0.1% spread is high
            return True, f"High spread: {spread}"

        # Check if stop was hit by minimal margin (typical of noise)
        if trade.exit_price and trade.stop_loss:
            if abs(trade.exit_price - trade.stop_loss) < 0.0001:  # Hit exactly
                return True, "Stop hit exactly (possible noise)"

        # Check for extreme slippage (would need to be stored in trade)
        # If trade has slippage metadata
        slippage = trade.metadata.get("slippage_pips", 0) if trade.metadata else 0
        if slippage > self.config.noise_slippage_threshold:
            return True, f"High slippage: {slippage} pips"

        return False, ""

    def get_recent_losses(self, n: int = 10) -> List[LossPattern]:
        """Get most recent n losses"""
        return self._losses[-n:]

    def get_losses_by_symbol(self, symbol: str) -> List[LossPattern]:
        """Get losses for a symbol"""
        return self._by_symbol.get(symbol, [])

    def get_losses_by_reason(self, reason: str) -> List[LossPattern]:
        """Get losses by reason"""
        return self._by_reason.get(reason, [])

    def count_losses(self, symbol: Optional[str] = None) -> int:
        """Count total losses (filtered, not noise)"""
        if symbol:
            return len([l for l in self._by_symbol.get(symbol, []) if not l.was_noise])
        return len([l for l in self._losses if not l.was_noise])

    def get_average_loss(self, symbol: Optional[str] = None) -> float:
        """Get average loss amount"""
        losses = self._losses if symbol is None else self._by_symbol.get(symbol, [])
        losses = [l for l in losses if not l.was_noise and l.pnl is not None]
        if not losses:
            return 0.0
        return sum(l.pnl for l in losses) / len(losses)

    def extract_patterns(self) -> Dict[str, Any]:
        """
        Analyze loss patterns to extract insights

        Returns:
            Dictionary with pattern statistics
        """
        if len(self._losses) < 5:
            return {"message": "Insufficient data"}

        losses = [l for l in self._losses if not l.was_noise]

        # Group by reason
        reason_counts: Dict[str, int] = {}
        for loss in losses:
            reason_counts[loss.reason] = reason_counts.get(loss.reason, 0) + 1

        # Group by symbol
        symbol_counts: Dict[str, int] = {}
        for loss in losses:
            symbol_counts[loss.symbol] = symbol_counts.get(loss.symbol, 0) + 1

        # Average loss by symbol
        avg_by_symbol: Dict[str, float] = {}
        for symbol in symbol_counts:
            sym_losses = [l.pnl for l in losses if l.symbol == symbol]
            avg_by_symbol[symbol] = sum(sym_losses) / len(sym_losses)

        return {
            "total_losses": len(losses),
            "noise_ratio": sum(1 for l in self._losses if l.was_noise) / len(self._losses) if self._losses else 0,
            "top_reasons": sorted(reason_counts.items(), key=lambda x: -x[1])[:5],
            "losses_by_symbol": symbol_counts,
            "avg_loss_by_symbol": avg_by_symbol,
        }

"""Error analyzer - analyzes errors for improvement"""
from typing import Dict, Any, List
from datetime import datetime
from dataclasses import dataclass

from ...core.logger import get_agent_logger
from ...core.types import Trade
from ...agents.memory.agent_memory import MemoryEntry


@dataclass
class ErrorAnalysis:
    """Analysis of an error"""
    error_type: str
    severity: int  # 1-5
    description: str
    suggested_fix: str
    timestamp: datetime


class ErrorAnalyzer:
    """
    Analyzes errors and mistakes to improve future performance.
    """

    def __init__(self):
        self.logger = get_agent_logger(0)
        self.error_history: List[ErrorAnalysis] = []

    def analyze_trade_error(self, trade: Trade, memory_entry: MemoryEntry) -> ErrorAnalysis:
        """
        Analyze a failed trade to determine cause.

        Returns:
            ErrorAnalysis object
        """
        errors = []

        # Check if SL was too tight
        if trade.pnl and trade.pnl < 0:
            sl_pips = abs(trade.entry_price - trade.stop_loss) / 0.0001
            if sl_pips < 20:  # less than 20 pips
                errors.append("stop_loss_too_tight")

            # Check if TP was too far
            tp_pips = abs(trade.take_profit - trade.entry_price) / 0.0001
            if tp_pips > 100:
                errors.append("take_profit_too_far")

            # Check market direction vs trade direction
            # Need market data - placeholder

        error_type = ",".join(errors) if errors else "unknown"
        analysis = ErrorAnalysis(
            error_type=error_type,
            severity=3,
            description=f"Trade lost {trade.pnl:.2f}",
            suggested_fix=self._get_suggestion(error_type),
            timestamp=datetime.utcnow()
        )
        self.error_history.append(analysis)
        return analysis

    def _get_suggestion(self, error_type: str) -> str:
        """Get suggested fix for error type"""
        suggestions = {
            "stop_loss_too_tight": "Increase stop loss distance to at least 30 pips",
            "take_profit_too_far": "Reduce take profit to more realistic levels (50-80 pips)",
            "unknown": "Review market conditions before entry"
        }
        return suggestions.get(error_type, "Monitor and adjust parameters")

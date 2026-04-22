"""Momentum strategy - based on RSI and MACD"""
from typing import Dict, Any, Optional
from datetime import datetime

from ...core.types import Signal, SignalType
from .base_strategy import BaseStrategy


class MomentumStrategy(BaseStrategy):
    """Momentum-based signal generator"""

    def __init__(self, symbol: str):
        self.symbol = symbol

    async def generate_signal(self, analysis: Dict[str, Any]) -> Optional[Signal]:
        rsi = analysis.get('rsi', 50)
        macd = analysis.get('macd', 0)
        macd_signal = analysis.get('macd_signal', 0)
        trend = analysis.get('trend', 'sideways')

        confidence = 0.5
        signal_type = SignalType.HOLD

        # Bullish: RSI > 50 and rising, MACD above signal
        if rsi > 55 and macd > macd_signal and trend != "downtrend":
            signal_type = SignalType.BUY
            confidence = min(1.0, (rsi - 50) / 50 * 0.5 + 0.5)
        # Bearish: RSI < 45 and MACD below signal
        elif rsi < 45 and macd < macd_signal and trend != "uptrend":
            signal_type = SignalType.SELL
            confidence = min(1.0, (50 - rsi) / 50 * 0.5 + 0.5)

        if signal_type == SignalType.HOLD:
            return None

        # Dynamic SL/TP based on ATR
        atr = analysis.get('atr', 0.001)
        sl_pips = max(20, int(atr / 0.0001 * 1.5))
        tp_pips = int(sl_pips * 1.5)

        return Signal(
            agent_id=0,
            symbol=self.symbol,
            type=signal_type,
            confidence=confidence,
            stop_loss_pips=sl_pips,
            take_profit_pips=tp_pips,
            metadata={"strategy": "momentum"}
        )

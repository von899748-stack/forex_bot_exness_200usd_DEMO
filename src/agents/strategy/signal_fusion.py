"""Signal fusion module - combines multiple signal sources"""
from typing import Dict, Any, List
from dataclasses import dataclass
from ...core.types import Signal, SignalType
from ...core.logger import get_agent_logger


@dataclass
class WeightedSignal:
    """Signal with weight for fusion"""
    signal: Signal
    weight: float  # 0-1
    source: str


class SignalFusion:
    """Combines multiple signals into a single decision"""

    def __init__(self, strategy_type: str = "weighted_average"):
        self.strategy_type = strategy_type
        self.logger = get_agent_logger(0)

    def fuse(self, signals: List[WeightedSignal]) -> Signal:
        """
        Fuse multiple signals into one

        Args:
            signals: List of weighted signals from different sources

        Returns:
            Combined signal
        """
        if not signals:
            # Return neutral hold signal
            return Signal(
                agent_id=0,
                symbol="",
                type=SignalType.HOLD,
                confidence=0.0,
                stop_loss_pips=0,
                take_profit_pips=0,
            )

        if self.strategy_type == "weighted_average":
            return self._weighted_average(signals)
        elif self.strategy_type == "majority_vote":
            return self._majority_vote(signals)
        elif self.strategy_type == "max_confidence":
            return self._max_confidence(signals)
        else:
            return self._weighted_average(signals)

    def _weighted_average(self, signals: List[WeightedSignal]) -> Signal:
        """Combine by averaging signal strengths weighted by confidence and source weight"""
        total_weight = sum(s.weight for s in signals)
        if total_weight == 0:
            avg_signal = signals[0].signal
        else:
            # Compute weighted average of numeric signal values
            # Map signal types to numeric: STRONG_BUY=3, BUY=2, WEAK_BUY=1, HOLD=0, etc.
            signal_map = {
                SignalType.STRONG_BUY: 3,
                SignalType.BUY: 2,
                SignalType.WEAK_BUY: 1,
                SignalType.HOLD: 0,
                SignalType.WEAK_SELL: -1,
                SignalType.SELL: -2,
                SignalType.STRONG_SELL: -3,
            }
            reverse_map = {v: k for k, v in signal_map.items()}

            weighted_sum = 0.0
            total_conf = 0.0
            for ws in signals:
                numeric = signal_map.get(ws.signal.type, 0)
                weight = ws.weight * ws.signal.confidence
                weighted_sum += numeric * weight
                total_conf += weight

            if total_conf > 0:
                avg_numeric = weighted_sum / total_conf
                # Round to nearest signal type
                closest = min(reverse_map.keys(), key=lambda x: abs(x - avg_numeric))
                signal_type = reverse_map[closest]
            else:
                signal_type = SignalType.HOLD

            # Average confidence
            avg_confidence = sum(s.signal.confidence for s in signals) / len(signals)

            # Average SL/TP (use median or weighted)
            avg_sl = sum(s.signal.stop_loss_pips for s in signals) / len(signals)
            avg_tp = sum(s.signal.take_profit_pips for s in signals) / len(signals)

            return Signal(
                agent_id=signals[0].signal.agent_id,
                symbol=signals[0].signal.symbol,
                type=signal_type,
                confidence=avg_confidence,
                stop_loss_pips=avg_sl,
                take_profit_pips=avg_tp,
                metadata={"sources": [s.source for s in signals]}
            )

    def _majority_vote(self, signals: List[WeightedSignal]) -> Signal:
        """Simple majority vote among signals with >0.5 confidence"""
        valid = [s for s in signals if s.signal.confidence > 0.5]
        if not valid:
            return signals[0].signal  # return neutral

        counts = {}
        for ws in valid:
            st = ws.signal.type
            counts[st] = counts.get(st, 0) + 1

        winner = max(counts, key=counts.get)
        # Pick highest confidence signal of winner type
        winner_signals = [ws.signal for ws in valid if ws.signal.type == winner]
        best = max(winner_signals, key=lambda s: s.confidence)

        return best

    def _max_confidence(self, signals: List[WeightedSignal]) -> Signal:
        """Return signal with highest weighted confidence"""
        best = max(signals, key=lambda ws: ws.weight * ws.signal.confidence)
        return best.signal

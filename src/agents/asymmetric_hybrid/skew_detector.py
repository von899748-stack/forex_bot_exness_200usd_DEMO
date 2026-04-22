"""Skew detector - detects market regime asymmetry"""
from typing import Dict, Any, Optional
import numpy as np
from dataclasses import dataclass
from ...core.logger import get_agent_logger


@dataclass
class MarketSkew:
    """Market skew information"""
    skewness: float  # -1 to 1, positive = bullish bias
    kurtosis: float  # Tail risk
    is_asymmetric: bool
    regime: str  # 'trending_up', 'trending_down', 'ranging', 'volatile'
    confidence: float


class SkewDetector:
    """Detects market asymmetry and regime"""

    def __init__(self, lookback: int = 100):
        self.lookback = lookback
        self.logger = get_agent_logger(0)

    def detect(self, returns: np.ndarray) -> MarketSkew:
        """
        Detect market skew from return series

        Args:
            returns: Array of price returns (log or pct)

        Returns:
            MarketSkew object
        """
        if len(returns) < 20:
            return MarketSkew(0.0, 0.0, False, "unknown", 0.0)

        # Calculate statistics
        mean_ret = np.mean(returns)
        std_ret = np.std(returns)
        skew = float(np.mean(((returns - mean_ret) / std_ret) ** 3)) if std_ret > 0 else 0.0
        kurt = float(np.mean(((returns - mean_ret) / std_ret) ** 4)) if std_ret > 0 else 0.0

        # Determine regime
        if abs(mean_ret) > 0.001:  # Trending
            regime = "trending_up" if mean_ret > 0 else "trending_down"
        elif np.std(returns) > 0.002:  # Volatile
            regime = "volatile"
        else:
            regime = "ranging"

        is_skewed = abs(skew) > 0.5  # threshold
        confidence = min(1.0, abs(skew))

        return MarketSkew(
            skewness=skew,
            kurtosis=kurt,
            is_asymmetric=is_skewed,
            regime=regime,
            confidence=confidence
        )

    def adjust_signal_for_skew(
        self,
        base_signal_strength: float,
        skew: MarketSkew,
        signal_direction: int  # 1 for long, -1 for short
    ) -> float:
        """
        Adjust signal strength based on market skew

        If market is skewed opposite to signal direction, reduce confidence.
        """
        if not skew.is_asymmetric:
            return base_signal_strength

        # Skew in same direction as signal -> increase confidence
        if (skew.skewness > 0 and signal_direction > 0) or (skew.skewness < 0 and signal_direction < 0):
            adjusted = base_signal_strength * (1 + 0.2 * skew.confidence)
        else:
            adjusted = base_signal_strength * (1 - 0.3 * skew.confidence)

        return max(0.0, min(1.0, adjusted))

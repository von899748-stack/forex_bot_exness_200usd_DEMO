"""Adaptive mixing - combines strategies with regime adaptation"""
from typing import Dict, Any, Optional
from dataclasses import dataclass
import numpy as np
from .skew_detector import SkewDetector, MarketSkew
from .weight_allocator import WeightAllocator, StrategyWeight
from ...core.logger import get_agent_logger


@dataclass
class MixConfig:
    """Configuration for adaptive mixing"""
    regime_weights: Dict[str, Dict[str, float]]  # regime -> strategy -> weight
    rebalance_threshold: float = 0.1  # 10% change triggers rebalance
    min_weight: float = 0.1  # min allocation per strategy


class AdaptiveMixer:
    """
    Adaptively mixes multiple strategies based on market regime
    and recent performance.
    """

    def __init__(self, config: MixConfig, allocator: WeightAllocator):
        self.config = config
        self.allocator = allocator
        self.skew_detector = SkewDetector()
        self.logger = get_agent_logger(0)
        self.current_regime = "ranging"
        self.return_history = []

    def update_regime(self, returns: np.ndarray):
        """Detect and update current market regime"""
        skew = self.skew_detector.detect(returns)
        self.current_regime = skew.regime
        return skew

    def mix_signals(
        self,
        signals: Dict[str, Any],  # strategy_name -> signal features
        analysis: Dict[str, Any]
    ) -> Dict[str, float]:
        """
        Generate final weights for each strategy's signal

        Returns:
            Dict of strategy_name -> final weight (0-1)
        """
        # Get base allocations from allocator
        base_weights = self.allocator.get_weights_dict()

        # Get regime-specific adjustments
        regime_adj = self.config.regime_weights.get(
            self.current_regime,
            {name: 1.0 for name in base_weights}
        )

        # Combine
        final_weights = {}
        for name, base_w in base_weights.items():
            adj_factor = regime_adj.get(name, 1.0)
            final_w = base_w * adj_factor
            final_weights[name] = final_w

        # Normalize to sum to 1
        total = sum(final_weights.values())
        if total > 0:
            final_weights = {k: v / total for k, v in final_weights.items()}

        return final_weights

    def apply_skew_adjustment(
        self,
        signal_confidence: float,
        direction: int
    ) -> float:
        """Adjust signal confidence based on detected skew"""
        if not self.return_history:
            return signal_confidence

        skew = self.skew_detector.detect(np.array(self.return_history))
        return self.skew_detector.adjust_signal_for_skew(signal_confidence, skew, direction)

    def record_return(self, ret: float):
        """Record a return for regime detection"""
        self.return_history.append(ret)
        if len(self.return_history) > 200:
            self.return_history = self.return_history[-200:]

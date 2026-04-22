"""Hybrid core - integrates asymmetric hybrid components"""
from typing import Dict, Any, Optional
import numpy as np
from dataclasses import dataclass
from ...core.types import Signal, SignalType
from ...core.logger import get_agent_logger
from .weight_allocator import WeightAllocator
from .skew_detector import SkewDetector, MarketSkew
from .adaptive_mixing import AdaptiveMixer, MixConfig
from ..strategy.signal_fusion import SignalFusion, WeightedSignal


@dataclass
class HybridConfig:
    """Configuration for hybrid strategy"""
    enable_skew_adjustment: bool = True
    enable_regime_adaptation: bool = True
    num_strategies: int = 3


class HybridCore:
    """
    Core component for asymmetric hybrid strategy.
    Combines multiple sub-strategies with dynamic weighting.
    """

    def __init__(self, config: HybridConfig):
        self.config = config
        self.logger = get_agent_logger(0)
        self.allocator = WeightAllocator(num_strategies=config.num_strategies)
        self.skew_detector = SkewDetector()
        self.adaptive_mixer = AdaptiveMixer(
            config=MixConfig(regime_weights={}),
            allocator=self.allocator
        )
        self.return_history = []

    async def combine(
        self,
        sub_signals: Dict[str, Signal],  # strategy_name -> signal
        market_returns: Optional[np.ndarray] = None
    ) -> Signal:
        """
        Combine sub-strategy signals into final signal

        Args:
            sub_signals: Signals from each sub-strategy
            market_returns: Recent returns for regime detection

        Returns:
            Fused signal
        """
        # Detect regime if returns provided
        skew = None
        if market_returns is not None and len(market_returns) > 20:
            skew = self.skew_detector.detect(market_returns)
            self.adaptive_mixer.current_regime = skew.regime

        # Get weights from adaptive mixer
        weights = self.adaptive_mixer.mix_signals(sub_signals, {})

        # Fuse signals
        fusion = SignalFusion()

        weighted_signals = []
        for name, signal in sub_signals.items():
            weight = weights.get(name, 1.0 / len(sub_signals))
            # Apply skew adjustment if enabled
            if self.config.enable_skew_adjustment and skew:
                direction = 1 if signal.is_bullish else -1
                adjusted_conf = self.skew_detector.adjust_signal_for_skew(
                    signal.confidence, skew, direction
                )
                signal.confidence = adjusted_conf

            weighted_signals.append(WeightedSignal(
                signal=signal,
                weight=weight,
                source=name
            ))

        final_signal = fusion.fuse(weighted_signals)
        return final_signal

    def record_outcome(self, profit: float, strategy_name: str):
        """Record strategy outcome for weight updating"""
        self.allocator.update_performance(strategy_name, profit)
        self.return_history.append(profit)
        if len(self.return_history) > 200:
            self.return_history = self.return_history[-200:]

"""Weight allocator - allocates capital weights to different strategies/modules"""
from typing import Dict, List, Tuple, Optional
import numpy as np
from dataclasses import dataclass
from ...core.logger import get_agent_logger
from ...config.base import LearningConfig


@dataclass
class StrategyWeight:
    """Weight for a strategy component"""
    name: str
    weight: float  # 0-1
    performance_score: float = 0.5
    recent_win_rate: float = 0.5


class WeightAllocator:
    """Dynamically allocates weights to strategy components based on performance"""

    def __init__(self, config: Optional[LearningConfig] = None, num_strategies: int = 3):
        self.config = config or LearningConfig()
        self.num_strategies = num_strategies
        self.logger = get_agent_logger(0)
        self.strategies: Dict[str, StrategyWeight] = {}
        self.performance_history: Dict[str, List[float]] = {}

        # Initialize equal weights
        equal_weight = 1.0 / num_strategies
        for i in range(num_strategies):
            name = f"strategy_{i+1}"
            self.strategies[name] = StrategyWeight(name=name, weight=equal_weight)

    def update_performance(self, strategy_name: str, profit: float):
        """Update strategy performance and rebalance weights"""
        if strategy_name not in self.strategies:
            return

        hist = self.performance_history.get(strategy_name, [])
        hist.append(profit)
        # Keep last 50 trades
        if len(hist) > 50:
            hist = hist[-50:]
        self.performance_history[strategy_name] = hist

        # Recalculate weights
        self._rebalance_weights()

    def _rebalance_weights(self):
        """Rebalance weights based on recent performance"""
        scores = {}
        for name, strat in self.strategies.items():
            hist = self.performance_history.get(name, [])
            if len(hist) >= 5:
                # Sharpe-like score: mean(returns) / std
                returns = np.array(hist)
                mean_ret = np.mean(returns)
                std_ret = np.std(returns)
                score = mean_ret / (std_ret + 1e-6)
                scores[name] = max(0.1, score + 0.5)  # Ensure positive
            else:
                scores[name] = 0.5  # default

        total_score = sum(scores.values())
        if total_score > 0:
            for name, score in scores.items():
                self.strategies[name].weight = score / total_score
                self.strategies[name].performance_score = score

    def get_allocation(self, strategy_name: Optional[str] = None) -> float:
        """Get weight for a strategy (or total sum)"""
        if strategy_name:
            return self.strategies.get(strategy_name, StrategyWeight(strategy_name, 0.0)).weight
        return sum(s.weight for s in self.strategies.values())

    def get_weights_dict(self) -> Dict[str, float]:
        """Get all strategy weights"""
        return {name: sw.weight for name, sw in self.strategies.items()}

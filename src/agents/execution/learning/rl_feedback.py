"""RL Feedback - reinforcement learning for strategy adaptation (placeholder)"""
from typing import Dict, Any, Optional
from ...core.logger import get_agent_logger
from ...config.base import LearningConfig


class RLFeedback:
    """
    Reinforcement learning feedback loop.
    Adjusts agent strategy based on rewards (PnL) via policy gradient.
    Placeholder for full RL implementation.
    """

    def __init__(self, config: LearningConfig):
        self.config = config
        self.logger = get_agent_logger(0)
        self.rewards: list[float] = []

    async def process_trade(self, trade):
        """Process trade outcome as reward signal"""
        if trade.pnl is not None:
            reward = trade.pnl / 10.0  # Scale reward
            self.rewards.append(reward)
            self.logger.debug(f"RL reward: {reward:.4f}")

    def get_average_reward(self, window: int = 100) -> float:
        """Get average recent reward"""
        if not self.rewards:
            return 0.0
        recent = self.rewards[-window:]
        return sum(recent) / len(recent)

    def should_explore(self) -> bool:
        """Decide if agent should explore (epsilon-greedy)"""
        # Decaying epsilon
        epsilon = 0.1
        return len(self.rewards) % 100 < (epsilon * 100)

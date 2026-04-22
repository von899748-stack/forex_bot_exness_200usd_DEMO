"""Agent factory for creating agents"""
from typing import Dict, Type, Optional
import importlib
from .base import BaseAgent
from ..config.base import BaseConfig


class AgentFactory:
    """Factory for creating agent instances"""

    def __init__(self):
        self._registry: Dict[str, Type[BaseAgent]] = {}

    def register(self, agent_type: str, agent_class: Type[BaseAgent]):
        """Register an agent class"""
        self._registry[agent_type] = agent_class

    def create(
        self,
        agent_type: str,
        agent_id: int,
        config: BaseConfig,
        symbol: str,
        **kwargs
    ) -> Optional[BaseAgent]:
        """Create an agent instance"""
        if agent_type not in self._registry:
            # Try dynamic import
            try:
                module = importlib.import_module(f"..agents.{agent_type}", __package__)
                agent_class = getattr(module, f"{agent_type.capitalize()}Agent")
                self.register(agent_type, agent_class)
            except Exception as e:
                print(f"Failed to import agent {agent_type}: {e}")
                return None
        else:
            agent_class = self._registry[agent_type]

        return agent_class(agent_id, config, symbol, **kwargs)

    def create_standard_agents(
        self,
        config: BaseConfig,
        symbols: list
    ) -> list:
        """Create 5 standard agents (2 technical, 2 hybrid, 1 macro)"""
        agents = []
        agent_id = 1

        agent_types = [
            ("technical_momentum", "EURUSD"),
            ("technical_meanrev", "GBPUSD"),
            ("hybrid_asymmetric", "EURUSD"),
            ("hybrid_adaptive", "XAUUSD"),
            ("macro", "GBPUSD"),
        ]

        for agent_type, symbol in agent_types[:config.risk.max_agents]:
            if symbol in symbols:
                agent = self.create(agent_type, agent_id, config, symbol)
                if agent:
                    agents.append(agent)
                    agent_id += 1

        return agents


# Global factory instance
agent_factory = AgentFactory()

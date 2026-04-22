"""Agent registry for tracking all agents"""
import threading
from typing import Dict, List, Optional
from .base import BaseAgent
from ..core.types import AgentStatus


class AgentRegistry:
    """Singleton registry for all agents"""

    _instance = None
    _lock = threading.Lock()

    def __new__(cls):
        if cls._instance is None:
            with cls._lock:
                if cls._instance is None:
                    cls._instance = super().__new__(cls)
        return cls._instance

    def __init__(self):
        if not hasattr(self, "_agents"):
            self._agents: Dict[int, BaseAgent] = {}
            self._symbols: Dict[str, List[int]] = {}  # symbol -> [agent_ids]

    def register(self, agent: BaseAgent):
        """Register an agent"""
        self._agents[agent.agent_id] = agent
        if agent.symbol not in self._symbols:
            self._symbols[agent.symbol] = []
        self._symbols[agent.symbol].append(agent.agent_id)

    def unregister(self, agent_id: int):
        """Unregister an agent"""
        if agent_id in self._agents:
            agent = self._agents[agent_id]
            symbol = agent.symbol
            self._symbols[symbol].remove(agent_id)
            if not self._symbols[symbol]:
                del self._symbols[symbol]
            del self._agents[agent_id]

    def get_agent(self, agent_id: int) -> Optional[BaseAgent]:
        return self._agents.get(agent_id)

    def get_agents_by_symbol(self, symbol: str) -> List[BaseAgent]:
        ids = self._symbols.get(symbol, [])
        return [self._agents[aid] for aid in ids if aid in self._agents]

    def get_all_agents(self) -> List[BaseAgent]:
        return list(self._agents.values())

    def get_all_statuses(self) -> List[AgentStatus]:
        return [agent.get_status() for agent in self._agents.values()]

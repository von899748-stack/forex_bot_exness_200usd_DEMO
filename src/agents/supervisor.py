"""Agent supervisor - monitors and manages agent lifecycle"""
import asyncio
from typing import List, Dict, Any
from datetime import datetime

from .base import BaseAgent
from .registry import AgentRegistry
from ..core.event_bus import EventBus, EventType
from ..core.logger import get_agent_logger
from ..config.base import BaseConfig


class AgentSupervisor:
    """Manages a group of agents"""

    def __init__(self, config: BaseConfig, event_bus: EventBus):
        self.config = config
        self.event_bus = event_bus
        self.registry = AgentRegistry()
        self.logger = get_agent_logger(0)
        self.running = False
        self._tasks: List[asyncio.Task] = []

    async def start_agents(self, symbols: List[str]) -> bool:
        """Create and start agents for each symbol"""
        try:
            from .factory import AgentFactory
            factory = AgentFactory()

            # Distribute symbols among agents
            agents_to_create = min(self.config.risk.max_agents, len(symbols))
            for i in range(agents_to_create):
                symbol = symbols[i % len(symbols)]
                agent = factory.create(
                    agent_type=self._get_agent_type(i),
                    agent_id=i + 1,
                    config=self.config,
                    symbol=symbol,
                    event_bus=self.event_bus
                )
                if agent:
                    self.registry.register(agent)
                    task = asyncio.create_task(agent.run())
                    self._tasks.append(task)
                    self.logger.info(f"Started agent {i+1} for {symbol}")

            # Subscribe to events
            await self.event_bus.subscribe(EventType.CONSECUTIVE_LOSSES, self._handle_consecutive_losses)
            await self.event_bus.subscribe(EventType.TRADE_CLOSED, self._handle_trade_closed)

            self.running = True
            return True
        except Exception as e:
            self.logger.error(f"Failed to start agents: {e}")
            return False

    def _get_agent_type(self, index: int) -> str:
        """Get agent type by index"""
        types = ["technical", "technical", "hybrid_asymmetric", "hybrid_adaptive", "macro"]
        if index < len(types):
            return types[index]
        return "technical"

    async def stop_all(self):
        """Stop all agents"""
        self.running = False
        agents = self.registry.get_all_agents()
        for agent in agents:
            await agent.stop()
        for task in self._tasks:
            task.cancel()
        self.logger.info("All agents stopped")

    async def _handle_consecutive_losses(self, event):
        """React to consecutive losses"""
        self.logger.warning(f"Agent hit consecutive losses: {event.data}")
        # Could trigger global stop if too many agents hitting losses

    async def _handle_trade_closed(self, event):
        """Handle trade close event"""
        # Update global metrics, notify, etc.
        pass

    def get_status_summary(self) -> Dict[str, Any]:
        """Get overview of all agents"""
        agents = self.registry.get_all_agents()
        return {
            "total_agents": len(agents),
            "running": self.running,
            "agents": [a.get_status().__dict__ for a in agents]
        }

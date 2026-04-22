"""Hybrid flow - orchestrates multiple agents with hybrid allocation"""
import asyncio
from typing import List, Dict, Any, Optional
from dataclasses import dataclass, field
from datetime import datetime

from ...core.types import AgentStatus
from ...core.logger import get_agent_logger
from ...agents.supervisor import AgentSupervisor
from ...agents.registry import AgentRegistry
from ...core.event_bus import EventBus
from ...agents.risk.global_risk import GlobalRiskManager
from ...agents.risk.loss_controller import LossController
from ...config.base import BaseConfig


@dataclass
class HybridFlowConfig:
    """Configuration for hybrid flow"""
    rebalance_interval: int = 3600  # seconds
    max_agents_per_symbol: int = 2
    enable_cross_hedging: bool = True


class HybridFlow:
    """
    Orchestrates multiple agents and manages hybrid allocation.
    """

    def __init__(
        self,
        config: BaseConfig,
        symbols: List[str],
        event_bus: Optional[EventBus] = None
    ):
        self.config = config
        self.symbols = symbols
        self.event_bus = event_bus or EventBus()
        self.logger = get_agent_logger(0)

        # Components
        self.supervisor = AgentSupervisor(config, self.event_bus)
        self.registry = self.supervisor.registry
        self.global_risk = GlobalRiskManager(config)
        self.loss_controller = LossController(config, self.event_bus)

        self.config_flow = HybridFlowConfig()
        self.running = False
        self._tasks: List[asyncio.Task] = []

    async def start(self):
        """Start the hybrid flow orchestrator"""
        self.logger.info("Starting Hybrid Flow Orchestrator")

        # Start agents
        await self.supervisor.start_agents(self.symbols)

        # Subscribe to events
        await self.event_bus.subscribe("trade.closed", self._on_trade_close)
        await self.event_bus.subscribe("agent.started", self._on_agent_start)

        self.running = True
        self.logger.info("Hybrid Flow started")

    async def stop(self):
        """Stop all agents and shutdown"""
        self.running = False
        await self.supervisor.stop_all()
        self.logger.info("Hybrid Flow stopped")

    async def _on_trade_close(self, event):
        """Handle trade close event"""
        agent_id = event.data.get('agent_id')
        pnl = event.data.get('pnl', 0)
        is_loss = pnl < 0
        self.loss_controller.record_trade_result(is_loss)

        # Update global risk
        statuses = self.registry.get_all_statuses()
        for status in statuses:
            self.global_risk.update_agent_status(status)

        if self.global_risk.should_pause_new_trades():
            self.logger.warning("Global risk limit hit - pausing new trades")

    async def _on_agent_start(self, event):
        """Handle agent start event"""
        self.logger.info(f"Agent started: {event.source}")

    def get_status(self) -> Dict[str, Any]:
        """Get overall orchestration status"""
        return {
            "running": self.running,
            "agents": self.registry.get_all_statuses(),
            "global_risk": self.global_risk.get_state().__dict__,
            "consecutive_losses": self.loss_controller.consecutive_losses,
        }

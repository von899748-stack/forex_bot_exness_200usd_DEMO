"""Demo trading orchestrator"""
import asyncio
from typing import List
import pandas as pd

from .hybrid_flow import HybridFlow
from ...core.logger import get_agent_logger
from ...config.paper import PaperConfig
from ...execution.broker.demo_broker import DemoBroker


class DemoOrchestrator(HybridFlow):
    """
    Orchestrator for demo/paper trading.
    """

    def __init__(self, config: PaperConfig, symbols: List[str]):
        super().__init__(config, symbols)
        self.config = config
        self.logger = get_agent_logger(0)
        self.broker = DemoBroker(config)

    async def start(self):
        """Start demo trading"""
        self.logger.info("Starting Demo Orchestrator")
        await super().start()

        self.logger.info("Demo mode ready - no real trades will be executed")

        # Simple demo loop
        while self.running:
            try:
                # Periodically log status
                status = self.get_status()
                self.logger.debug(f"Agents: {len(status['agents'])}")
                await asyncio.sleep(10)
            except Exception as e:
                self.logger.error(f"Demo error: {e}")
                await asyncio.sleep(5)

"""Backtest orchestrator"""
from typing import List
import pandas as pd

from .hybrid_flow import HybridFlow
from ...core.logger import get_agent_logger
from ...config.backtest import BacktestConfig
from ...execution.broker.backtest_broker import BacktestBroker
from ...agents.execution.learning.backtest_engine import BacktestEngine
from ...data.storage.timescaledb import TimescaleDBClient
from ...data.storage.trade_records import TradeRecorder


class BacktestOrchestrator(HybridFlow):
    """
    Orchestrator for backtesting.
    """

    def __init__(
        self,
        config: BacktestConfig,
        symbols: List[str],
        data: pd.DataFrame,
        db_client: Optional[TimescaleDBClient] = None
    ):
        super().__init__(config, symbols)
        self.config = config
        self.data = data
        self.db = db_client
        self.logger = get_agent_logger(0)
        # Backtest uses per-agent engine instead of broker directly
        self.engines = []

    async def start(self):
        """Run the backtest"""
        self.logger.info("Starting Backtest Orchestrator")
        await super().start()

        # Create an engine per agent
        for agent in self.registry.get_all_agents():
            engine = BacktestEngine(
                config=self.config,
                agent=agent,
                data=self.data[self.data['symbol'] == agent.symbol],
                db_client=self.db
            )
            self.engines.append(engine)

        # Run all engines concurrently
        results = await asyncio.gather(*[e.run() for e in self.engines])

        # Aggregate results
        total_trades = sum(len(r) for r in results)
        self.logger.info(f"Backtest completed: {total_trades} total trades")

        # Stop
        await self.stop()

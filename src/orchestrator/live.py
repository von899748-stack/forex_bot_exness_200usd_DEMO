"""Live trading orchestrator"""
import asyncio
from typing import List, Optional
from datetime import datetime

from .hybrid_flow import HybridFlow
from ...core.logger import get_agent_logger
from ...config.live import LiveConfig
from ...data.sources.mt5 import MT5DataHandler
from ...notifications.telegram import TelegramNotifier
from ...execution.broker.exness_mt5_broker import ExnessMT5Broker


class LiveOrchestrator(HybridFlow):
    """
    Orchestrator for live trading with Exness MT5.
    """

    def __init__(self, config: LiveConfig, symbols: List[str]):
        super().__init__(config, symbols)
        self.config = config
        self.logger = get_agent_logger(0)

        # Live-specific components
        self.mt5_handler = MT5DataHandler()
        self.telegram = TelegramNotifier(config.telegram)
        self.broker = ExnessMT5Broker(config)

    async def start(self):
        """Start live trading"""
        self.logger.info("Starting Live Orchestrator")
        await super().start()

        # Connect to MT5
        await self.broker.connect()

        # Notify start
        await self.telegram.send_message(
            f"🚀 Forex Bot started in LIVE mode\n"
            f"Symbols: {', '.join(self.symbols)}\n"
            f"Capital: ${self.config.risk.total_capital}"
        )

        # Main loop
        while self.running:
            try:
                # Check trading hours
                if not self._is_trading_time():
                    await asyncio.sleep(60)
                    continue

                # Sync agent equity with account
                account = await self.broker.get_account_info()
                await self._update_equities(account.get('equity', 0))

                # Check global risk
                if self.global_risk.should_pause_new_trades():
                    await asyncio.sleep(10)
                    continue

                await asyncio.sleep(1)

            except Exception as e:
                self.logger.error(f"Live orchestrator error: {e}")
                await asyncio.sleep(5)

    async def stop(self):
        """Stop live trading"""
        await super().stop()
        await self.broker.disconnect()
        await self.telegram.send_message("🛑 Forex Bot stopped")

    def _is_trading_time(self) -> bool:
        """Check if within trading hours"""
        now = datetime.utcnow()
        start = self.config.trading_hours.start_hour
        end = self.config.trading_hours.end_hour
        return start <= now.hour < end

    async def _update_equities(self, account_equity: float):
        """Distribute account equity across agents"""
        num_agents = len(self.registry.get_all_agents())
        if num_agents == 0:
            return
        per_agent = account_equity / num_agents
        for agent in self.registry.get_all_agents():
            agent.equity = per_agent

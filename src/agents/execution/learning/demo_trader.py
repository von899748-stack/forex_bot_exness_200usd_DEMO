"""Demo trader - simulates trading for testing agents"""
from typing import List, Dict, Any
import pandas as pd
from datetime import datetime, timedelta
import random

from ...core.types import Trade, Signal, MarketData, Side
from ...core.logger import get_agent_logger
from ...execution.broker.demo_broker import DemoBroker
from ...config.base import BaseConfig


class DemoTrader:
    """
    Simulates trading using historical data for agent testing.
    """

    def __init__(self, config: BaseConfig, data: pd.DataFrame, agent):
        self.config = config
        self.data = data
        self.agent = agent
        self.broker = DemoBroker(config)
        self.logger = get_agent_logger(0)
        self.trades: List[Trade] = []

    async def run_simulation(self) -> List[Trade]:
        """
        Run simulation over historical data.

        Returns:
            List of completed trades
        """
        self.logger.info("Starting demo simulation")

        for idx, row in self.data.iterrows():
            market = MarketData(
                symbol=self.agent.symbol,
                timestamp=row['timestamp'],
                open=row['open'],
                high=row['high'],
                low=row['low'],
                close=row['close'],
                volume=row.get('volume', 0),
                spread=row.get('spread', 0.0001),
                bid=row.get('bid', row['close'] - 0.00005),
                ask=row.get('ask', row['close'] + 0.00005),
            )

            # Agent makes decision
            analysis = await self.agent.perception.analyze(market)
            signal = await self.agent.strategy.generate_signal(analysis)

            # Decide to trade
            if signal and signal.confidence > 0.6 and self.agent.current_trade is None:
                risk = 0.01
                await self.agent._execute_signal(signal, risk)

            # Manage open position
            if self.agent.current_trade:
                # Check TP/SL
                current = market.close
                trade = self.agent.current_trade

                # Simplified exit logic
                if trade.side == Side.BUY:
                    if current >= trade.take_profit:
                        trade.close(current)
                        self.trades.append(trade)
                        self.agent.record_win()
                        self.agent.current_trade = None
                    elif current <= trade.stop_loss:
                        trade.close(current)
                        self.trades.append(trade)
                        self.agent.record_loss()
                        self.agent.current_trade = None
                else:
                    if current <= trade.take_profit:
                        trade.close(current)
                        self.trades.append(trade)
                        self.agent.record_win()
                        self.agent.current_trade = None
                    elif current >= trade.stop_loss:
                        trade.close(current)
                        self.trades.append(trade)
                        self.agent.record_loss()
                        self.agent.current_trade = None

        self.logger.info(f"Demo simulation finished: {len(self.trades)} trades")
        return self.trades

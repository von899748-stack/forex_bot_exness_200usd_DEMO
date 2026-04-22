"""Backtest engine - runs strategies against historical data"""
from typing import List, Dict, Any, Optional
import pandas as pd
import asyncio
from datetime import datetime

from ...core.types import MarketData, Trade, AgentStatus, Signal
from ...core.logger import get_agent_logger
from ...config.base import BacktestConfig
from ..base import BaseAgent
from ...data.storage.trade_records import TradeRecorder
from ...data.storage.timescaledb import TimescaleDBClient


class BacktestEngine:
    """
    Engine for running backtests on historical data.
    """

    def __init__(
        self,
        config: BacktestConfig,
        agent: BaseAgent,
        data: pd.DataFrame,
        db_client: Optional[TimescaleDBClient] = None
    ):
        self.config = config
        self.agent = agent
        self.data = data
        self.db = db_client
        self.logger = get_agent_logger(0)
        self.trade_recorder = TradeRecorder(db_client) if db_client else None
        self.results: List[Trade] = []
        self.current_index = 0

    async def run(self) -> List[Trade]:
        """
        Run the backtest from start to end.

        Returns:
            List of completed trades
        """
        self.logger.info(f"Starting backtest from {self.config.backtest_start} to {self.config.backtest_end}")

        # Initialize agent
        await self.agent.initialize()
        self.agent.state = AgentState.TRADING

        # Iterate through data
        for idx, row in self.data.iterrows():
            self.current_index = idx
            current_time = row['timestamp']

            # Check trading hours
            if not self._is_trading_time(current_time):
                continue

            # Create MarketData object
            market_data = MarketData(
                symbol=self.agent.symbol,
                timestamp=current_time,
                open=row['open'],
                high=row['high'],
                low=row['low'],
                close=row['close'],
                volume=row.get('volume', 0),
                spread=row.get('spread', 0.0001),
                bid=row.get('bid', row['close'] - row.get('spread', 0.0001)/2),
                ask=row.get('ask', row['close'] + row.get('spread', 0.0001)/2),
            )

            # Update agent equity from P&L if in position
            await self._update_equity()

            # Agent processes market data
            try:
                analysis = await self.agent.perception.analyze(market_data)
                signal = await self.agent.strategy.generate_signal(analysis)

                if signal and signal.confidence > 0.5:
                    risk = self.agent.risk_manager.calculate_risk(
                        equity=self.agent.equity,
                        peak_equity=self.agent.peak_equity,
                        consecutive_losses=self.agent.consecutive_losses,
                        signal_confidence=signal.confidence
                    )
                    await self.agent._execute_signal(signal, risk)

            except Exception as e:
                self.logger.error(f"Error at {current_time}: {e}")

        # Close any open positions at end
        await self._close_all_positions(final_price=self.data.iloc[-1]['close'])

        # Save results
        if self.trade_recorder:
            for trade in self.results:
                self.trade_recorder.record_trade(trade)

        self.logger.info(f"Backtest completed: {len(self.results)} trades")
        return self.results

    def _is_trading_time(self, timestamp: datetime) -> bool:
        """Check if timestamp is within trading hours"""
        from ...core.utils import is_trading_time
        return is_trading_time(
            timestamp,
            start_hour=self.config.trading_hours.start_hour,
            end_hour=self.config.trading_hours.end_hour
        )

    async def _update_equity(self):
        """Update agent equity from open positions"""
        # Simplified: agent updates internally
        pass

    async def _close_all_positions(self, final_price: float):
        """Close all open positions at final price"""
        if self.agent.current_trade:
            trade = self.agent.current_trade
            trade.close(final_price)
            self.agent.memory.record_trade(trade)
            self.results.append(trade)
            self.agent.current_trade = None

    def get_performance_metrics(self) -> Dict[str, Any]:
        """Calculate performance metrics from results"""
        if not self.results:
            return {}

        pnls = [t.pnl for t in self.results if t.pnl is not None]
        wins = [p for p in pnls if p > 0]
        losses = [p for p in pnls if p <= 0]

        total_pnl = sum(pnls)
        win_rate = len(wins) / len(pnls) if pnls else 0.0
        avg_win = sum(wins) / len(wins) if wins else 0.0
        avg_loss = sum(losses) / len(losses) if losses else 0.0
        profit_factor = (sum(wins) / abs(sum(losses))) if losses else float('inf')

        return {
            "total_pnl": total_pnl,
            "win_rate": win_rate,
            "avg_win": avg_win,
            "avg_loss": avg_loss,
            "profit_factor": profit_factor,
            "total_trades": len(self.results),
        }

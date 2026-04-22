"""Trade recording and persistence"""
from datetime import datetime
from typing import Optional, Dict, Any, List
import pandas as pd
import numpy as np
from .timescaledb import TimescaleDBClient
from ...core.types import Trade, AgentStatus, PerformanceMetrics
from ...core.logger import get_agent_logger
from ...config.base import BaseConfig


class TradeRecorder:
    """Records trades to database and maintains performance metrics"""

    def __init__(self, db_client: TimescaleDBClient):
        self.db = db_client
        self.logger = get_agent_logger(0)  # System logger
        self._ensure_tables()

    def _ensure_tables(self):
        """Create required tables if not exist"""
        # Trades table
        trades_table = """
        CREATE TABLE IF NOT EXISTS trades (
            id UUID PRIMARY KEY,
            agent_id INTEGER NOT NULL,
            symbol VARCHAR(32) NOT NULL,
            side VARCHAR(4) NOT NULL,
            quantity DOUBLE PRECISION NOT NULL,
            entry_price DOUBLE PRECISION NOT NULL,
            exit_price DOUBLE PRECISION,
            stop_loss DOUBLE PRECISION NOT NULL,
            take_profit DOUBLE PRECISION NOT NULL,
            entry_time TIMESTAMP NOT NULL,
            exit_time TIMESTAMP,
            pnl DOUBLE PRECISION,
            pnl_pct DOUBLE PRECISION,
            commission DOUBLE PRECISION DEFAULT 0,
            swap DOUBLE PRECISION DEFAULT 0,
            reason TEXT,
            is_win BOOLEAN,
            is_noise_filtered BOOLEAN DEFAULT FALSE,
            metadata JSONB DEFAULT '{}',
            created_at TIMESTAMP DEFAULT NOW()
       );
        """

        # Create hypertable for time-series queries
        trades_hypertable = """
        SELECT create_hypertable('trades', 'entry_time', if_not_exists => TRUE);
        """

        # Agent status table
        status_table = """
        CREATE TABLE IF NOT EXISTS agent_status (
            id SERIAL PRIMARY KEY,
            agent_id INTEGER NOT NULL,
            state VARCHAR(32) NOT NULL,
            equity DOUBLE PRECISION NOT NULL,
            peak_equity DOUBLE PRECISION NOT NULL,
            drawdown DOUBLE PRECISION NOT NULL,
            consecutive_losses INTEGER DEFAULT 0,
            last_signal_time TIMESTAMP,
            error_message TEXT,
            metrics JSONB DEFAULT '{}',
            updated_at TIMESTAMP DEFAULT NOW()
        );
        """

        # Equity curve table
        equity_table = """
        CREATE TABLE IF NOT EXISTS equity_curve (
            time TIMESTAMP NOT NULL,
            equity DOUBLE PRECISION NOT NULL,
            peak DOUBLE PRECISION NOT NULL,
            drawdown DOUBLE PRECISION NOT NULL,
            trade_count INTEGER DEFAULT 0,
            PRIMARY KEY (time)
        );
        SELECT create_hypertable('equity_curve', 'time', if_not_exists => TRUE);
        """

        try:
            self.db.execute(trades_table)
            self.db.execute(trades_hypertable)
            self.db.execute(status_table)
            self.db.execute(equity_table)
        except Exception as e:
            self.logger.error(f"Failed to create tables: {e}")

    def record_trade(self, trade: Trade) -> bool:
        """Record a completed or open trade"""
        data = {
            "id": str(trade.id),
            "agent_id": trade.agent_id,
            "symbol": trade.symbol,
            "side": trade.side.value,
            "quantity": trade.quantity,
            "entry_price": trade.entry_price,
            "exit_price": trade.exit_price,
            "stop_loss": trade.stop_loss,
            "take_profit": trade.take_profit,
            "entry_time": trade.entry_time,
            "exit_time": trade.exit_time,
            "pnl": trade.pnl,
            "pnl_pct": trade.pnl_pct,
            "commission": trade.commission,
            "swap": trade.swap,
            "reason": trade.reason,
            "is_win": trade.is_win,
            "is_noise_filtered": trade.is_noise_filtered,
            "metadata": str(trade.metadata) if trade.metadata else "{}",
        }
        return self.db.insert("trades", data)

    def update_agent_status(self, status: AgentStatus):
        """Update agent performance status"""
        # Upsert into agent_status
        query = """
        INSERT INTO agent_status (
            agent_id, state, equity, peak_equity, drawdown,
            consecutive_losses, last_signal_time, error_message, metrics, updated_at
        ) VALUES (%s, %s, %s, %s, %s, %s, %s, %s, %s, NOW())
        ON CONFLICT (agent_id) DO UPDATE SET
            state = EXCLUDED.state,
            equity = EXCLUDED.equity,
            peak_equity = EXCLUDED.peak_equity,
            drawdown = EXCLUDED.drawdown,
            consecutive_losses = EXCLUDED.consecutive_losses,
            last_signal_time = EXCLUDED.last_signal_time,
            error_message = EXCLUDED.error_message,
            metrics = EXCLUDED.metrics,
            updated_at = NOW();
        """
        self.db.execute(query, (
            status.agent_id,
            status.state.value,
            status.equity,
            status.peak_equity,
            status.drawdown,
            status.consecutive_losses,
            status.last_signal_time,
            status.error_message,
            str(status.metrics) if status.metrics else "{}",
        ))

    def record_equity_point(
        self,
        equity: float,
        peak: float,
        drawdown: float,
        trade_count: int = 0
    ):
        """Record an equity curve point"""
        self.db.insert("equity_curve", {
            "time": datetime.utcnow(),
            "equity": equity,
            "peak": peak,
            "drawdown": drawdown,
            "trade_count": trade_count,
        })

    def get_agent_trades(self, agent_id: int, limit: int = 100) -> List[Dict]:
        """Get trades for an agent"""
        query = """
        SELECT * FROM trades
        WHERE agent_id = %s
        ORDER BY entry_time DESC
        LIMIT %s
        """
        return self.db.execute(query, (agent_id, limit)) or []

    def get_performance_metrics(self, agent_id: int) -> PerformanceMetrics:
        """Calculate performance metrics for an agent"""
        trades = self.get_agent_trades(agent_id, limit=1000)
        closed_trades = [t for t in trades if t.get('exit_time')]

        metrics = PerformanceMetrics()
        metrics.total_trades = len(closed_trades)

        if metrics.total_trades == 0:
            return metrics

        wins = [t for t in closed_trades if t.get('pnl', 0) > 0]
        losses = [t for t in closed_trades if t.get('pnl', 0) <= 0]

        metrics.winning_trades = len(wins)
        metrics.losing_trades = len(losses)
        metrics.win_rate = metrics.winning_trades / metrics.total_trades

        pnls = [t['pnl'] for t in closed_trades if t.get('pnl') is not None]
        metrics.total_pnl = sum(pnls)

        win_pnls = [t['pnl'] for t in wins]
        loss_pnls = [abs(t['pnl']) for t in losses]

        metrics.avg_win = np.mean(win_pnls) if win_pnls else 0.0
        metrics.avg_loss = np.mean(loss_pnls) if loss_pnls else 0.0

        if metrics.avg_loss > 0:
            metrics.profit_factor = (metrics.win_rate * metrics.avg_win) / ((1 - metrics.win_rate) * metrics.avg_loss)

        metrics.expectancy = (metrics.win_rate * metrics.avg_win) - ((1 - metrics.win_rate) * metrics.avg_loss)

        return metrics

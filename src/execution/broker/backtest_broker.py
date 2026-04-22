"""Backtest broker - simulates trading on historical data"""
import pandas as pd
from typing import Optional, Dict, Any, List
from datetime import datetime

from .base_broker import BaseBroker
from ...core.types import OrderRequest, OrderResponse, Position, Side
from ...core.exceptions import OrderRejectedError
from ...core.logger import get_agent_logger


class BacktestBroker(BaseBroker):
    """
    Broker for backtesting. Reads historical data and simulates trades.
    """

    def __init__(self, config: BaseConfig, data: pd.DataFrame):
        super().__init__(config)
        self.data = data.sort_values('timestamp').reset_index(drop=True)
        self.current_index = 0
        self.positions: List[Position] = []
        self.balance = config.risk.total_capital
        self.equity = config.risk.total_capital
        self.trades: List[Trade] = []
        self.logger = get_agent_logger(0)
        self.commission_per_lot = getattr(config, 'commission_per_lot', 7.0)
        self.slippage_pips = getattr(config, 'slippage_pips', 0.5)

    async def connect(self) -> bool:
        self.connected = True
        return True

    def set_current_time(self, timestamp: datetime):
        """Set current backtest time stamp (used by orchestrator)"""
        # Advance to nearest bar
        while self.current_index < len(self.data):
            bar_time = self.data.iloc[self.current_index]['timestamp']
            if bar_time >= timestamp:
                break
            self.current_index += 1

    def get_current_price(self, symbol: str) -> float:
        """Get current price for symbol"""
        if self.current_index >= len(self.data):
            return 0.0
        row = self.data.iloc[self.current_index]
        # Use close as mid price
        return (row['bid'] + row['ask']) / 2 if 'bid' in row else row['close']

    async def send_order(self, order: OrderRequest) -> OrderResponse:
        """Send order - filled at current price + slippage"""
        if self.current_index >= len(self.data):
            raise OrderRejectedError("No more data")

        row = self.data.iloc[self.current_index]
        price = (row['bid'] + row['ask']) / 2 if 'bid' in row else row['close']

        # Apply slippage in pips
        symbol = order.symbol
        pip_size = 0.0001 if not symbol.endswith('JPY') else 0.01
        slippage = self.slippage_pips * pip_size

        if order.side == Side.BUY:
            fill_price = price + slippage
        else:
            fill_price = price - slippage

        pos_id = f"backtest_{len(self.trades)}"
        position = Position(
            id=pos_id,
            symbol=order.symbol,
            side=order.side,
            quantity=order.quantity,
            entry_price=fill_price,
            current_price=fill_price,
            stop_loss=order.stop_loss or 0.0,
            take_profit=order.take_profit or 0.0,
            unrealized_pnl=0.0,
            unrealized_pnl_pct=0.0,
            entry_time=row['timestamp']
        )
        self.positions.append(position)

        commission = order.quantity * self.commission_per_lot / 100000
        self.balance -= commission

        return OrderResponse(
            order_id=pos_id,
            status="filled",
            filled_quantity=order.quantity,
            avg_fill_price=fill_price,
            commission=commission,
            message="Backtest fill"
        )

    async def get_positions(self) -> List[Position]:
        """Get current positions (update unrealized P&L)"""
        self._mark_to_market()
        return self.positions

    async def close_position(self, position_id: str, volume: Optional[float] = None) -> OrderResponse:
        """Close a position"""
        for i, pos in enumerate(self.positions):
            if pos.id == position_id:
                close_qty = volume or pos.quantity
                row = self.data.iloc[self.current_index]
                exit_price = (row['bid'] + row['ask']) / 2 if 'bid' in row else row['close']
                # Add slippage
                symbol = pos.symbol
                pip_size = 0.0001 if not symbol.endswith('JPY') else 0.01
                slippage = self.slippage_pips * pip_size
                if pos.side == Side.BUY:
                    exit_price -= slippage
                else:
                    exit_price += slippage

                # P&L
                if pos.side == Side.BUY:
                    pnl = (exit_price - pos.entry_price) * close_qty
                else:
                    pnl = (pos.entry_price - exit_price) * close_qty

                self.balance += pnl

                if close_qty >= pos.quantity:
                    self.positions.pop(i)
                else:
                    pos.quantity -= close_qty

                self.logger.debug(f"Closed {position_id}, P&L: {pnl:.2f}")
                return OrderResponse(
                    order_id=f"close_{self._order_counter}",
                    status="filled",
                    filled_quantity=close_qty,
                    avg_fill_price=exit_price,
                    commission=0,
                    message="Closed"
                )
        raise OrderRejectedError(f"Position {position_id} not found")

    async def get_account_info(self) -> Dict[str, Any]:
        """Get account info"""
        self._mark_to_market()
        return {
            "balance": self.balance,
            "equity": self.equity,
            "margin": 0.0,
            "free_margin": self.equity,
            "margin_level": 100.0,
        }

    def _mark_to_market(self):
        """Mark positions to current market price"""
        row = self.data.iloc[self.current_index] if self.current_index < len(self.data) else None
        if row is None:
            return
        price = (row['bid'] + row['ask']) / 2 if 'bid' in row else row['close']
        total_unrealized = 0.0
        for pos in self.positions:
            if pos.side == Side.BUY:
                pos.unrealized_pnl = (price - pos.entry_price) * pos.quantity
            else:
                pos.unrealized_pnl = (pos.entry_price - price) * pos.quantity
            total_unrealized += pos.unrealized_pnl
        self.equity = self.balance + total_unrealized

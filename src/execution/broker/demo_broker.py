"""Demo broker - simulated trading for testing"""
import random
import asyncio
from typing import Optional, Dict, Any, List
from datetime import datetime

from .base_broker import BaseBroker
from ...core.types import OrderRequest, OrderResponse, Position, Trade, Side, OrderRequest
from ...core.exceptions import OrderRejectedError, InsufficientFundsError


class DemoBroker(BaseBroker):
    """
    Simulated broker for demo/paper trading.
    Fills orders instantly with some slippage.
    """

    def __init__(self, config: BaseConfig):
        super().__init__(config)
        self.positions: List[Position] = []
        self.trade_history: List[Trade] = []
        self.balance = config.risk.total_capital
        self.equity = config.risk.total_capital
        self._price_cache: Dict[str, float] = {}
        self._order_counter = 1000

    async def connect(self) -> bool:
        """Connect demo broker (always succeeds)"""
        self.connected = True
        return True

    async def send_order(self, order: OrderRequest) -> OrderResponse:
        """Simulate order placement"""
        if not self.connected:
            raise OrderRejectedError("Broker not connected")

        # Simulate price with spread and slippage
        base_price = self._get_mock_price(order.symbol)
        spread = 0.0002  # 2 pips spread for EURUSD

        if order.side == Side.BUY:
            fill_price = base_price + spread / 2
        else:
            fill_price = base_price - spread / 2

        # Add random slippage
        slippage = random.uniform(-0.0001, 0.0001)
        fill_price += slippage

        # Create position
        pos_id = str(self._order_counter)
        self._order_counter += 1

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
            entry_time=datetime.utcnow()
        )
        self.positions.append(position)

        self.logger.info(f"Demo order filled: {order.side} {order.quantity} {order.symbol} @ {fill_price}")

        return OrderResponse(
            order_id=pos_id,
            status="filled",
            filled_quantity=order.quantity,
            avg_fill_price=fill_price,
            commission=order.quantity * 7 / 100000,  # $7 per standard lot
            message="Demo fill"
        )

    def _get_mock_price(self, symbol: str) -> float:
        """Generate a mock price (walking randomly)"""
        if symbol not in self._price_cache:
            self._price_cache[symbol] = 1.0800 if symbol == "EURUSD" else 1.2700 if symbol == "GBPUSD" else 2000.0
        # Random walk
        self._price_cache[symbol] += random.uniform(-0.0010, 0.0010)
        return self._price_cache[symbol]

    async def get_positions(self) -> List[Position]:
        """Get open positions"""
        self._update_position_unrealized_pnl()
        return self.positions

    async def close_position(self, position_id: str, volume: Optional[float] = None) -> OrderResponse:
        """Close a position"""
        for i, pos in enumerate(self.positions):
            if pos.id == position_id:
                close_qty = volume or pos.quantity
                if close_qty < pos.quantity:
                    # Partial close - keep remainder
                    pos.quantity -= close_qty
                else:
                    # Full close
                    self.positions.pop(i)

                # Simulate exit price
                exit_price = self._get_mock_price(pos.symbol)
                # Calculate P&L
                if pos.side == Side.BUY:
                    pnl = (exit_price - pos.entry_price) * close_qty
                else:
                    pnl = (pos.entry_price - exit_price) * close_qty

                self.equity += pnl
                if pnl > 0:
                    self.balance += pnl

                self.logger.info(f"Demo position closed: {position_id}, P&L: {pnl:.2f}")

                return OrderResponse(
                    order_id=str(self._order_counter),
                    status="filled",
                    filled_quantity=close_qty,
                    avg_fill_price=exit_price,
                    commission=0,
                    message="Closed"
                )
        raise OrderRejectedError(f"Position {position_id} not found")

    async def get_account_info(self) -> Dict[str, Any]:
        """Get mock account info"""
        return {
            "balance": self.balance,
            "equity": self.equity,
            "margin": 0.0,
            "free_margin": self.equity,
            "margin_level": 100.0,
            "currency": "USD"
        }

    def _update_position_unrealized_pnl(self):
        """Mark positions to market"""
        for pos in self.positions:
            current = self._get_mock_price(pos.symbol)
            pos.current_price = current
            if pos.side == Side.BUY:
                pos.unrealized_pnl = (current - pos.entry_price) * pos.quantity
            else:
                pos.unrealized_pnl = (pos.entry_price - current) * pos.quantity
            pos.unrealized_pnl_pct = (pos.unrealized_pnl / (pos.entry_price * pos.quantity)) * 100 if pos.quantity > 0 else 0

        self.equity = self.balance + sum(p.unrealized_pnl for p in self.positions)

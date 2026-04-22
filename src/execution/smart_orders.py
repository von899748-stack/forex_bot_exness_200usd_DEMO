"""Smart order router - splits and manages orders"""
from typing import List, Optional
from dataclasses import dataclass
from ...core.types import OrderRequest, OrderResponse, Side
from ...core.logger import get_agent_logger
from ...execution.broker.base_broker import BaseBroker


@dataclass
class OrderSlice:
    """Order slice for TWAP/VWAP"""
    quantity: float
    delay_seconds: float = 0.0


class SmartOrderRouter:
    """
    Smart order routing with TWAP, Iceberg, and other algos.
    """

    def __init__(self, broker: BaseBroker):
        self.broker = broker
        self.logger = get_agent_logger(0)

    async def execute_twap(
        self,
        order: OrderRequest,
        slices: int = 5,
        interval_seconds: float = 10.0
    ) -> OrderResponse:
        """
        Execute order using Time-Weighted Average Price (TWAP)

        Splits order into equal slices over time.
        """
        slice_qty = order.quantity / slices
        total_filled = 0.0
        avg_price = 0.0
        total_commission = 0.0

        for i in range(slices):
            slice_order = OrderRequest(
                symbol=order.symbol,
                side=order.side,
                order_type=order.order_type,
                quantity=slice_qty,
                stop_loss=order.stop_loss,
                take_profit=order.take_profit,
            )
            result = await self.broker.send_order(slice_order)
            total_filled += result.filled_quantity
            avg_price = (avg_price * i + result.avg_fill_price * result.filled_quantity) / (i + result.filled_quantity + 1e-9)
            total_commission += result.commission

            if i < slices - 1:
                await asyncio.sleep(interval_seconds)

        return OrderResponse(
            order_id=f"twap_{order.symbol}_{id(order)}",
            status="filled",
            filled_quantity=total_filled,
            avg_fill_price=avg_price,
            commission=total_commission,
            message="TWAP executed"
        )

    async def execute_iceberg(
        self,
        order: OrderRequest,
        visible_size: float,
        refresh_offset: float = 0.1
    ) -> OrderResponse:
        """
        Execute order using Iceberg (hidden volume)
        Only visible_size shown at a time; replenishes as fills occur.
        """
        remaining = order.quantity
        total_filled = 0.0
        avg_price = 0.0

        while remaining > 0:
            slice_qty = min(visible_size, remaining)
            slice_order = OrderRequest(
                symbol=order.symbol,
                side=order.side,
                order_type=order.order_type,
                quantity=slice_qty,
                stop_loss=order.stop_loss,
                take_profit=order.take_profit,
            )
            result = await self.broker.send_order(slice_order)
            total_filled += result.filled_quantity
            remaining -= result.filled_quantity
            avg_price = (avg_price + result.avg_fill_price) / 2
            await asyncio.sleep(0.1)

        return OrderResponse(
            order_id=f"iceberg_{order.symbol}_{id(order)}",
            status="filled",
            filled_quantity=total_filled,
            avg_fill_price=avg_price,
            commission=0,
            message="Iceberg executed"
        )

    async def execute_market(self, order: OrderRequest) -> OrderResponse:
        """Simple market order"""
        return await self.broker.send_order(order)

"""Exness MT5 broker for live trading"""
import asyncio
from typing import Optional, Dict, Any, List
from datetime import datetime

from ..mt5 import MT5Connector
from .base_broker import BaseBroker
from ...core.types import OrderRequest, OrderResponse, Position, Side, Trade
from ...core.logger import get_agent_logger
from ...config.base import BaseConfig


class ExnessMT5Broker(BaseBroker):
    """
    Broker implementation using MT5 for Exness accounts.
    """

    def __init__(self, config: BaseConfig):
        super().__init__(config)
        self.mt5_connector = MT5Connector(config.mt5)
        self.logger = get_agent_logger(0)

    async def connect(self) -> bool:
        """Connect to MT5"""
        try:
            self.mt5_connector.connect()
            self.connected = True
            self.logger.info("Connected to MT5")
            return True
        except Exception as e:
            self.logger.error(f"MT5 connection failed: {e}")
            return False

    async def disconnect(self):
        """Disconnect from MT5"""
        self.mt5_connector.disconnect()
        self.connected = False

    async def send_order(self, order: OrderRequest) -> OrderResponse:
        """Send order via MT5"""
        if not self.connected:
            raise Exception("Not connected")

        # Convert OrderRequest to MT5 format
        mt5_order = order  # placeholder; would adapt

        try:
            result = self.mt5_connector.place_order(mt5_order)
            return OrderResponse(
                order_id=str(result.order_id),
                status=result.status,
                filled_quantity=result.filled_quantity,
                avg_fill_price=result.avg_fill_price,
                commission=result.commission,
                message=result.message
            )
        except Exception as e:
            self.logger.error(f"Order failed: {e}")
            raise

    async def get_positions(self) -> List[Position]:
        """Get open positions"""
        if not self.connected:
            return []
        mt5_positions = self.mt5_connector.get_positions()
        return mt5_positions

    async def close_position(self, position_id: str, volume: Optional[float] = None) -> OrderResponse:
        """Close position"""
        if not self.connected:
            raise Exception("Not connected")
        return self.mt5_connector.close_position(position_id, volume)

    async def get_account_info(self) -> Dict[str, Any]:
        """Get account info"""
        if not self.connected:
            return {}
        return self.mt5_connector.get_account_info()

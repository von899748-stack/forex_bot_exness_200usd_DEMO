"""Base broker interface"""
from abc import ABC, abstractmethod
from typing import Optional, Dict, Any, List
import asyncio

from ...core.types import OrderRequest, OrderResponse, Position, Trade
from ...core.logger import get_agent_logger
from ...config.base import BaseConfig


class BaseBroker(ABC):
    """Abstract base class for all brokers"""

    def __init__(self, config: BaseConfig):
        self.config = config
        self.logger = get_agent_logger(0)
        self.connected = False

    async def connect(self) -> bool:
        """Connect to broker"""
        self.connected = True
        return True

    async def disconnect(self):
        """Disconnect from broker"""
        self.connected = False

    @abstractmethod
    async def send_order(self, order: OrderRequest) -> OrderResponse:
        """Send an order to the broker"""
        pass

    @abstractmethod
    async def get_positions(self) -> List[Position]:
        """Get open positions"""
        pass

    @abstractmethod
    async def close_position(self, position_id: str, volume: Optional[float] = None) -> OrderResponse:
        """Close a position"""
        pass

    @abstractmethod
    async def get_account_info(self) -> Dict[str, Any]:
        """Get account balance, equity, etc."""
        pass

    async def modify_position(
        self,
        position_id: str,
        stop_loss: Optional[float] = None,
        take_profit: Optional[float] = None
    ) -> bool:
        """Modify SL/TP of open position"""
        raise NotImplementedError("Modify not supported")

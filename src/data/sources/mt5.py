"""MT5/Exness connector for live and demo trading"""
import MetaTrader5 as mt5
import threading
from typing import Optional, List, Dict, Any, Tuple
from datetime import datetime, timedelta
import pandas as pd
import numpy as np

from ..core.types import (
    MarketData, Trade, Side, OrderType, OrderRequest,
    OrderResponse, Position, Signal, AgentStatus
)
from ..core.exceptions import (
    ConnectionError, OrderRejectedError, SymbolNotFoundError,
    InsufficientFundsError, MarketClosedError
)
from ..core.logger import get_agent_logger
from ..config.base import MT5Config


class MT5Connector:
    """Singleton MT5 connection manager"""

    _instance = None
    _lock = threading.Lock()

    def __new__(cls, config: MT5Config):
        if cls._instance is None:
            with cls._lock:
                if cls._instance is None:
                    cls._instance = super().__new__(cls)
        return cls._instance

    def __init__(self, config: MT5Config):
        if not hasattr(self, "_initialized"):
            self.config = config
            self.connected = False
            self._initialized = True

    def connect(self) -> bool:
        """Establish connection to MT5"""
        if self.connected:
            return True

        if not self.config.path:
            # Initialize without path if running on server
            initialized = mt5.initialize()
        else:
            initialized = mt5.initialize(self.config.path)

        if not initialized:
            raise ConnectionError(f"Failed to initialize MT5: {mt5.last_error()}")

        # Login if credentials provided
        if self.config.login and self.config.password:
            login_result = mt5.login(
                login=self.config.login,
                password=self.config.password,
                server=self.config.server
            )
            if not login_result:
                raise ConnectionError(f"MT5 login failed: {mt5.last_error()}")

        self.connected = True
        return True

    def disconnect(self):
        """Disconnect from MT5"""
        if self.connected:
            mt5.shutdown()
            self.connected = False

    def get_symbols(self) -> List[str]:
        """Get all available symbols"""
        if not self.connected:
            self.connect()
        symbols = mt5.symbols_get()
        return [s.name for s in symbols] if symbols else []

    def get_symbol_info(self, symbol: str) -> Optional[Dict[str, Any]]:
        """Get symbol information"""
        if not self.connected:
            self.connect()
        info = mt5.symbol_info(symbol)
        if info is None:
            return None
        return info._asdict()

    def get_symbol_info_tick(self, symbol: str) -> Optional[Dict[str, Any]]:
        """Get current tick for symbol"""
        if not self.connected:
            self.connect()
        tick = mt5.symbol_info_tick(symbol)
        if tick is None:
            return None
        return tick._asdict()

    def get_rates(
        self,
        symbol: str,
        timeframe: int = mt5.TIMEFRAME_M5,
        days: int = 1
    ) -> pd.DataFrame:
        """
        Get historical OHLCV data

        Args:
            symbol: Trading symbol
            timeframe: MT5 timeframe constant
            days: Number of days to fetch

        Returns:
            DataFrame with columns: time, open, high, low, close, tick_volume, spreads
        """
        if not self.connected:
            self.connect()

        from_date = datetime.now() - timedelta(days=days)
        to_date = datetime.now()

        rates = mt5.copy_rates_range(symbol, timeframe, from_date, to_date)
        if rates is None or len(rates) == 0:
            return pd.DataFrame()

        df = pd.DataFrame(rates)
        df['time'] = pd.to_datetime(df['time'], unit='s')
        df.rename(columns={
            'open': 'open',
            'high': 'high',
            'low': 'low',
            'close': 'close',
            'tick_volume': 'volume',
            'spread': 'spread'
        }, inplace=True)

        return df

    def place_order(self, request: OrderRequest) -> OrderResponse:
        """Place a trade order"""
        if not self.connected:
            self.connect()

        # Build MT5 order request
        action = mt5.TRADE_ACTION_DEAL if request.order_type == OrderType.MARKET else mt5.TRADE_ACTION_PENDING
        order_type_map = {
            OrderType.MARKET: mt5.ORDER_TYPE_BUY if request.side == Side.BUY else mt5.ORDER_TYPE_SELL,
            OrderType.LIMIT: mt5.ORDER_TYPE_BUY_LIMIT if request.side == Side.BUY else mt5.ORDER_TYPE_SELL_LIMIT,
            OrderType.STOP: mt5.ORDER_TYPE_BUY_STOP if request.side == Side.BUY else mt5.ORDER_TYPE_SELL_STOP,
        }

        mt5_request = {
            "action": action,
            "symbol": request.symbol,
            "volume": request.quantity,
            "type": order_type_map.get(request.order_type, mt5.ORDER_TYPE_BUY),
            "price": request.price or self.get_current_price(request.symbol, request.side),
            "sl": request.stop_loss,
            "tp": request.take_profit,
            "deviation": 10,  # Slippage tolerance in points
            "magic": request.agent_id,  # Use agent ID as magic number
            "comment": request.metadata.get("comment", "Forex Bot"),
            "type_time": mt5.ORDER_TIME_GTC,
            "type_filling": mt5.ORDER_FILLING_IOC,
        }

        result = mt5.order_send(mt5_request)
        if result is None:
            raise OrderRejectedError(f"Order send returned None: {mt5.last_error()}")

        if result.retcode != mt5.TRADE_RETCODE_DONE:
            raise OrderRejectedError(f"Order rejected: {result.retcode}, {result.comment}")

        return OrderResponse(
            order_id=str(result.order),
            status="filled",
            filled_quantity=result.volume,
            avg_fill_price=result.price,
            commission=result.commission,
            message=result.comment
        )

    def get_current_price(self, symbol: str, side: Side) -> float:
        """Get current market price for order"""
        tick = self.get_symbol_info_tick(symbol)
        if not tick:
            raise MarketClosedError(f"Cannot get price for {symbol}")
        return tick['ask'] if side == Side.BUY else tick['bid']

    def get_positions(self, symbol: Optional[str] = None) -> List[Position]:
        """Get open positions"""
        if not self.connected:
            self.connect()

        positions = mt5.positions_get(symbol=symbol) if symbol else mt5.positions_get()
        if positions is None:
            return []

        result = []
        for pos in positions:
            result.append(Position(
                id=pos.identifier,
                symbol=pos.symbol,
                side=Side.BUY if pos.type == mt5.POSITION_TYPE_BUY else Side.SELL,
                quantity=pos.volume,
                entry_price=pos.price_open,
                current_price=pos.price_current,
                stop_loss=pos.sl,
                take_profit=pos.tp,
                unrealized_pnl=pos.profit,
                unrealized_pnl_pct=(pos.profit / (pos.volume * pos.price_open)) * 100 if pos.volume * pos.price_open != 0 else 0,
                entry_time=datetime.fromtimestamp(pos.time)
            ))

        return result

    def close_position(self, position_id: str, volume: Optional[float] = None) -> OrderResponse:
        """Close an open position"""
        if not self.connected:
            self.connect()

        positions = mt5.positions_get(ticket=int(position_id))
        if not positions:
            raise OrderRejectedError(f"Position {position_id} not found")

        pos = positions[0]
        close_volume = volume or pos.volume

        request = {
            "action": mt5.TRADE_ACTION_DEAL,
            "symbol": pos.symbol,
            "volume": close_volume,
            "type": mt5.ORDER_TYPE_SELL if pos.type == mt5.POSITION_TYPE_BUY else mt5.ORDER_TYPE_BUY,
            "position": int(position_id),
            "price": self.get_current_price(pos.symbol, Side.SELL if pos.type == mt5.POSITION_TYPE_BUY else Side.BUY),
            "deviation": 10,
            "magic": 0,
            "comment": "Close by bot",
            "type_time": mt5.ORDER_TIME_GTC,
            "type_filling": mt5.ORDER_FILLING_IOC,
        }

        result = mt5.order_send(request)
        if result.retcode != mt5.TRADE_RETCODE_DONE:
            raise OrderRejectedError(f"Close failed: {result.retcode}")

        return OrderResponse(
            order_id=str(result.order),
            status="filled",
            filled_quantity=result.volume,
            avg_fill_price=result.price,
            commission=result.commission,
            message=result.comment
        )

    def modify_position(
        self,
        position_id: str,
        stop_loss: Optional[float] = None,
        take_profit: Optional[float] = None
    ) -> bool:
        """Modify stop loss or take profit of open position"""
        if not self.connected:
            self.connect()

        positions = mt5.positions_get(ticket=int(position_id))
        if not positions:
            return False

        pos = positions[0]
        request = {
            "action": mt5.TRADE_ACTION_SLTP,
            "position": int(position_id),
            "sl": stop_loss or pos.sl,
            "tp": take_profit or pos.tp,
        }

        result = mt5.order_send(request)
        return result.retcode == mt5.TRADE_RETCODE_DONE

    def get_account_info(self) -> Dict[str, Any]:
        """Get account information"""
        if not self.connected:
            self.connect()
        info = mt5.account_info()
        if info is None:
            return {}
        return info._asdict()

    def get_balance(self) -> float:
        """Get account balance"""
        return self.get_account_info().get("balance", 0.0)

    def get_equity(self) -> float:
        """Get account equity"""
        return self.get_account_info().get("equity", 0.0)


class MT5DataHandler:
    """Handles data streaming for MT5"""

    def __init__(self, connector: MT5Connector):
        self.connector = connector
        self.subscribers = {}
        self.running = False

    def subscribe_symbol(self, symbol: str, callback, timeframe=mt5.TIMEFRAME_M5):
        """Subscribe to real-time updates for a symbol"""
        # In a real implementation, use a thread to poll for new bars
        pass

    def unsubscribe_symbol(self, symbol: str):
        """Stop receiving updates for a symbol"""
        if symbol in self.subscribers:
            del self.subscribers[symbol]

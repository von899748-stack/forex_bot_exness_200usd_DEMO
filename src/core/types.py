from datetime import datetime
from decimal import Decimal
from enum import Enum
from typing import Optional, Dict, Any, List
from dataclasses import dataclass, field
from uuid import UUID, uuid4


class Side(str, Enum):
    BUY = "BUY"
    SELL = "SELL"


class OrderType(str, Enum):
    MARKET = "MARKET"
    LIMIT = "LIMIT"
    STOP = "STOP"


class TimeInForce(str, Enum):
    GTC = "GTC"  # Good Till Cancelled
    IOC = "IOC"  # Immediate or Cancel
    FOK = "FOK"  # Fill or Kill


class SignalType(str, Enum):
    STRONG_BUY = "STRONG_BUY"
    BUY = "BUY"
    WEAK_BUY = "WEAK_BUY"
    HOLD = "HOLD"
    WEAK_SELL = "WEAK_SELL"
    SELL = "SELL"
    STRONG_SELL = "STRONG_SELL"


class AgentState(str, Enum):
    INITIALIZING = "INITIALIZING"
    READY = "READY"
    TRADING = "TRADING"
    STOPPED = "STOPPED"
    ERROR = "ERROR"
    PAUSED = "PAUSED"


@dataclass
class Symbol:
    """Trading symbol configuration"""
    name: str
    pip_value: float
    min_lot: float
    max_lot: float
    lot_step: float
    spread_normal: float
    spread_wide: float
    midnight_cutoff: int  # hour when spread becomes wide


@dataclass
class Trade:
    """Represents a completed or open trade"""
    # Required fields (no defaults) first
    agent_id: int
    symbol: str
    side: Side
    quantity: float
    entry_price: float
    stop_loss: float
    take_profit: float
    # Optional fields with defaults after
    id: UUID = field(default_factory=uuid4)
    entry_time: datetime = field(default_factory=datetime.utcnow)
    exit_price: Optional[float] = None
    exit_time: Optional[datetime] = None
    pnl: Optional[float] = None
    pnl_pct: Optional[float] = None
    commission: float = 0.0
    swap: float = 0.0
    reason: str = ""
    is_win: Optional[bool] = None
    is_noise_filtered: bool = False
    metadata: Dict[str, Any] = field(default_factory=dict)

    def close(self, exit_price: float, exit_time: Optional[datetime] = None):
        self.exit_price = exit_price
        self.exit_time = exit_time or datetime.utcnow()
        self.pnl = self.calculate_pnl(exit_price)
        self.pnl_pct = self.calculate_pnl_pct()
        self.is_win = self.pnl > 0

    def calculate_pnl(self, exit_price: float) -> float:
        """Calculate P&L in account currency"""
        if self.side == Side.BUY:
            return (exit_price - self.entry_price) * self.quantity
        else:
            return (self.entry_price - exit_price) * self.quantity

    def calculate_pnl_pct(self) -> float:
        """Calculate P&L as percentage of entry value"""
        if self.pnl is None or self.entry_price == 0:
            return 0.0
        entry_value = self.entry_price * self.quantity
        return (self.pnl / entry_value) * 100


@dataclass
class Signal:
    """Trading signal from an agent or strategy"""
    agent_id: int
    symbol: str
    type: SignalType
    confidence: float  # 0.0 to 1.0
    stop_loss_pips: float
    take_profit_pips: float
    timestamp: datetime = field(default_factory=datetime.utcnow)
    metadata: Dict[str, Any] = field(default_factory=dict)

    @property
    def is_bullish(self) -> bool:
        return self.type in [SignalType.STRONG_BUY, SignalType.BUY, SignalType.WEAK_BUY]

    @property
    def is_bearish(self) -> bool:
        return self.type in [SignalType.STRONG_SELL, SignalType.SELL, SignalType.WEAK_SELL]


@dataclass
class AgentStatus:
    """Current status of an agent"""
    agent_id: int
    state: AgentState
    current_trade: Optional[Trade] = None
    equity: float = 0.0
    peak_equity: float = 0.0
    drawdown: float = 0.0
    consecutive_losses: int = 0
    last_signal_time: Optional[datetime] = None
    error_message: Optional[str] = None
    metrics: Dict[str, Any] = field(default_factory=dict)


@dataclass
class OrderRequest:
    """Request to place an order"""
    symbol: str
    side: Side
    order_type: OrderType
    quantity: float
    price: Optional[float] = None
    stop_loss: Optional[float] = None
    take_profit: Optional[float] = None
    time_in_force: TimeInForce = TimeInForce.GTC
    agent_id: int = 0
    metadata: Dict[str, Any] = field(default_factory=dict)


@dataclass
class OrderResponse:
    """Response from broker after order placement"""
    order_id: str
    status: str
    filled_quantity: float
    avg_fill_price: float
    commission: float
    timestamp: datetime = field(default_factory=datetime.utcnow)
    message: str = ""


@dataclass
class MarketData:
    """Market data snapshot"""
    symbol: str
    timestamp: datetime
    open: float
    high: float
    low: float
    close: float
    volume: float
    spread: float
    bid: float
    ask: float


@dataclass
class Position:
    """Open position"""
    id: str
    symbol: str
    side: Side
    quantity: float
    entry_price: float
    current_price: float
    stop_loss: float
    take_profit: float
    unrealized_pnl: float
    unrealized_pnl_pct: float
    entry_time: datetime = field(default_factory=datetime.utcnow)


@dataclass
class EquityCurvePoint:
    """Point on equity curve"""
    timestamp: datetime
    equity: float
    peak: float
    drawdown: float
    trade_count: int = 0


@dataclass
class PerformanceMetrics:
    """Performance metrics for an agent or portfolio"""
    total_trades: int = 0
    winning_trades: int = 0
    losing_trades: int = 0
    win_rate: float = 0.0
    total_pnl: float = 0.0
    avg_win: float = 0.0
    avg_loss: float = 0.0
    profit_factor: float = 0.0
    max_drawdown: float = 0.0
    sharpe_ratio: float = 0.0
    sortino_ratio: float = 0.0
    calmar_ratio: float = 0.0
    expectancy: float = 0.0
    risk_adjusted_return: float = 0.0

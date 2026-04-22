"""Agent memory - stores trade history and state"""
from typing import List, Optional, Dict, Any
from datetime import datetime
from dataclasses import dataclass, field
import json

from ...core.types import Trade


@dataclass
class MemoryEntry:
    """Entry in agent memory"""
    trade_id: str
    symbol: str
    entry_time: datetime
    exit_time: Optional[datetime] = None
    side: str = ""
    quantity: float = 0.0
    entry_price: float = 0.0
    exit_price: float = 0.0
    pnl: Optional[float] = None
    pnl_pct: Optional[float] = None
    reason: str = ""
    outcome: Optional[str] = None  # "win", "loss", "breakeven"
    features: Dict[str, Any] = field(default_factory=dict)  # Market conditions at entry
    lessons: List[str] = field(default_factory=list)  # Learned lessons


class AgentMemory:
    """In-memory storage for agent's recent trades and patterns"""

    def __init__(self, agent_id: int, capacity: int = 1000):
        self.agent_id = agent_id
        self.capacity = capacity
        self._entries: List[MemoryEntry] = []
        self._by_symbol: Dict[str, List[MemoryEntry]] = {}
        self._by_outcome: Dict[str, List[MemoryEntry]] = {"win": [], "loss": [], "breakeven": []}

    def record_trade(self, trade: Trade):
        """Record a new trade"""
        entry = MemoryEntry(
            trade_id=str(trade.id),
            symbol=trade.symbol,
            entry_time=trade.entry_time,
            side=trade.side.value,
            quantity=trade.quantity,
            entry_price=trade.entry_price,
            stop_loss=trade.stop_loss,
            take_profit=trade.take_profit,
            reason=trade.reason,
        )
        self._entries.append(entry)
        self._by_symbol.setdefault(trade.symbol, []).append(entry)

        # Enforce capacity
        if len(self._entries) > self.capacity:
            old = self._entries.pop(0)
            if old.trade_id:
                self._by_symbol[old.symbol].remove(old)

    def update_trade_outcome(self, trade_id: str, pnl: float, pnl_pct: float):
        """Update trade with outcome after close"""
        for entry in self._entries:
            if entry.trade_id == trade_id:
                entry.exit_time = datetime.utcnow()
                entry.exit_price = entry.exit_price  # Will be set separately
                entry.pnl = pnl
                entry.pnl_pct = pnl_pct
                entry.outcome = "win" if pnl > 0 else "loss" if pnl < 0 else "breakeven"
                self._by_outcome[entry.outcome].append(entry)
                break

    def get_recent_trades(self, n: int = 10) -> List[MemoryEntry]:
        """Get most recent N trades"""
        return self._entries[-n:]

    def get_trades_by_symbol(self, symbol: str) -> List[MemoryEntry]:
        """Get all trades for a symbol"""
        return self._by_symbol.get(symbol, [])

    def get_win_rate(self, symbol: Optional[str] = None) -> float:
        """Calculate win rate for all trades or specific symbol"""
        trades = self._entries if symbol is None else self._by_symbol.get(symbol, [])
        if not trades:
            return 0.0
        wins = sum(1 for t in trades if t.outcome == "win")
        return wins / len(trades)

    def get_avg_pnl(self, symbol: Optional[str] = None) -> float:
        """Get average P&L"""
        trades = self._entries if symbol is None else self._by_symbol.get(symbol, [])
        pnls = [t.pnl for t in trades if t.pnl is not None]
        return sum(pnls) / len(pnls) if pnls else 0.0

    def get_consecutive_losses(self) -> int:
        """Count recent consecutive losses"""
        count = 0
        for entry in reversed(self._entries):
            if entry.outcome == "loss":
                count += 1
            elif entry.outcome == "win":
                break
        return count

    def to_dict(self) -> Dict[str, Any]:
        """Serialize memory to dict"""
        return {
            "agent_id": self.agent_id,
            "total_trades": len(self._entries),
            "win_rate": self.get_win_rate(),
            "consecutive_losses": self.get_consecutive_losses(),
            "recent_trades": [
                {
                    "trade_id": e.trade_id,
                    "symbol": e.symbol,
                    "outcome": e.outcome,
                    "pnl": e.pnl,
                    "entry_time": e.entry_time.isoformat() if e.entry_time else None,
                }
                for e in self._entries[-10:]
            ]
        }

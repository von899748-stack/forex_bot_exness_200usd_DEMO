"""Trade recorder for learning module"""
from typing import List
from datetime import datetime
import json

from ...core.types import Trade
from ...core.logger import get_agent_logger


class TradeRecorder:
    """Records trades to file/DB for analysis and learning"""

    def __init__(self, filepath: str = "data/trades.json"):
        self.filepath = filepath
        self.logger = get_agent_logger(0)
        self.trades: List[Dict] = []

    def record(self, trade: Trade):
        """Record a trade"""
        record = {
            "id": str(trade.id),
            "agent_id": trade.agent_id,
            "symbol": trade.symbol,
            "side": trade.side.value,
            "quantity": trade.quantity,
            "entry_price": trade.entry_price,
            "exit_price": trade.exit_price,
            "pnl": trade.pnl,
            "entry_time": trade.entry_time.isoformat() if trade.entry_time else None,
            "exit_time": trade.exit_time.isoformat() if trade.exit_time else None,
            "reason": trade.reason,
        }
        self.trades.append(record)

        # Persist to disk periodically
        if len(self.trades) % 10 == 0:
            self.save()

    def save(self):
        """Save trades to disk"""
        import os
        os.makedirs(os.path.dirname(self.filepath), exist_ok=True)
        with open(self.filepath, 'w') as f:
            json.dump(self.trades, f, indent=2, default=str)

    def load(self):
        """Load trades from disk"""
        import os
        if os.path.exists(self.filepath):
            with open(self.filepath, 'r') as f:
                self.trades = json.load(f)

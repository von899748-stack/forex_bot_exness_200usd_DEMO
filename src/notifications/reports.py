"""Report generator - creates performance reports"""
from typing import Dict, Any, List
from datetime import datetime, timedelta
from dataclasses import dataclass
import json

from ...core.logger import get_agent_logger
from ...data.storage.trade_records import TradeRecorder
from ...agents.registry import AgentRegistry
from ...core.types import PerformanceMetrics


@dataclass
class DailyReport:
    """Daily performance report"""
    date: datetime
    total_trades: int
    win_rate: float
    total_pnl: float
    avg_win: float
    avg_loss: float
    max_drawdown: float
    agent_breakdown: List[Dict[str, Any]]


class ReportGenerator:
    """Generates various reports"""

    def __init__(self, recorder: TradeRecorder, registry: AgentRegistry):
        self.recorder = recorder
        self.registry = registry
        self.logger = get_agent_logger(0)

    def generate_daily_report(self, date: datetime) -> DailyReport:
        """Generate daily report for a specific date"""
        # Query trades for that day from DB
        all_trades = self.recorder.get_all_trades(limit=10000)  # fetch many
        date_start = date.replace(hour=0, minute=0, second=0, microsecond=0)
        date_end = date_start + timedelta(days=1)

        day_trades = [
            t for t in all_trades
            if t.get('entry_time') and date_start <= datetime.fromisoformat(t['entry_time']) < date_end
        ]

        # Calculate metrics
        wins = [t for t in day_trades if t.get('pnl', 0) > 0]
        total_pnl = sum(t.get('pnl', 0) for t in day_trades)
        win_rate = len(wins) / len(day_trades) if day_trades else 0.0

        # Per-agent breakdown
        agents = self.registry.get_all_agents()
        agent_breakdown = []
        for agent in agents:
            status = agent.get_status()
            agent_breakdown.append({
                "agent_id": agent.agent_id,
                "symbol": agent.symbol,
                "equity": status.equity,
                "pnl": status.equity - (status.peak_equity - status.equity if status.peak_equity else 0),
                "trades": len([t for t in day_trades if t.get('agent_id') == agent.agent_id]),
            })

        return DailyReport(
            date=date,
            total_trades=len(day_trades),
            win_rate=win_rate,
            total_pnl=total_pnl,
            avg_win=0.0,  # compute
            avg_loss=0.0,
            max_drawdown=0.0,
            agent_breakdown=agent_breakdown,
        )

    def generate_summary(self) -> Dict[str, Any]:
        """Generate high-level summary for dashboard"""
        agents = self.registry.get_all_agents()
        total_equity = sum(a.equity for a in agents)
        total_peak = sum(a.peak_equity for a in agents)

        return {
            "timestamp": datetime.utcnow().isoformat(),
            "total_equity": total_equity,
            "total_peak": total_peak,
            "active_agents": len(agents),
            "drawdown": (total_peak - total_equity) / total_peak if total_peak > 0 else 0,
            "agents": [a.get_status().__dict__ for a in agents],
        }

    def to_json(self, report: DailyReport) -> str:
        """Convert report to JSON"""
        return json.dumps(report.__dict__, default=str, indent=2)

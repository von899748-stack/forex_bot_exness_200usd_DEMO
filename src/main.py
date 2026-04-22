"""Main entry point for the forex bot"""
import asyncio
import argparse
import sys
from pathlib import Path

# Add src to path
sys.path.insert(0, str(Path(__file__).parent))

from src.config.paper import PaperConfig
from src.config.live import LiveConfig
from src.config.backtest import BacktestConfig
from src.orchestrator.demo import DemoOrchestrator
from src.orchestrator.live import LiveOrchestrator
from src.orchestrator.backtest import BacktestOrchestrator
from src.core.logger import setup_logger
from src.core.event_bus import EventBus
import logging

logger = setup_logger(log_level="INFO")


async def main():
    parser = argparse.ArgumentParser(description="Forex Trading Bot")
    parser.add_argument("--mode", choices=["demo", "live", "backtest", "dashboard"], default="demo",
                        help="Trading mode")
    parser.add_argument("--symbols", nargs="+", default=["EURUSD", "GBPUSD", "XAUUSD"],
                        help="Symbols to trade")
    parser.add_argument("--capital", type=float, default=200,
                        help="Total capital")
    parser.add_argument("--risk", type=float, default=0.01,
                        help="Base risk per trade")
    parser.add_argument("--max-agents", type=int, default=5,
                        help="Maximum number of agents")
    parser.add_argument("--backtest-start", default="2024-01-01",
                        help="Backtest start date (YYYY-MM-DD)")
    parser.add_argument("--backtest-end", default="2024-12-31",
                        help="Backtest end date (YYYY-MM-DD)")

    args = parser.parse_args()

    event_bus = EventBus()

    if args.mode == "demo":
        config = PaperConfig()
        config.risk.total_capital = args.capital
        config.risk.max_agents = args.max_agents
        config.risk.base_risk = args.risk
        orchestrator = DemoOrchestrator(config, args.symbols)
        await orchestrator.start()

    elif args.mode == "live":
        config = LiveConfig()
        config.risk.total_capital = args.capital
        config.risk.max_agents = min(args.max_agents, 3)  # max 3 live
        config.risk.base_risk = args.risk * 0.5  # more conservative
        orchestrator = LiveOrchestrator(config, args.symbols)
        await orchestrator.start()

    elif args.mode == "backtest":
        config = BacktestConfig()
        config.backtest_start = args.backtest_start
        config.backtest_end = args.backtest_end
        config.risk.total_capital = args.capital
        config.risk.max_agents = args.max_agents
        config.risk.base_risk = args.risk

        # Load historical data
        import pandas as pd
        data = pd.DataFrame()
        # Placeholder - real implementation would load CSV or DB
        orchestrator = BacktestOrchestrator(config, args.symbols, data)
        await orchestrator.start()

    elif args.mode == "dashboard":
        # Launch Streamlit dashboard
        import subprocess
        subprocess.run(["streamlit", "run", "src/dashboard/app.py"])
        return

    else:
        logger.error(f"Unknown mode: {args.mode}")
        return

    # Keep running until interrupted
    try:
        while True:
            await asyncio.sleep(1)
    except KeyboardInterrupt:
        logger.info("Shutting down...")
        await orchestrator.stop()


if __name__ == "__main__":
    asyncio.run(main())

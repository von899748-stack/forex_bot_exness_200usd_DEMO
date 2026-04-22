#!/usr/bin/env python
"""Run backtest from command line"""
import asyncio
import argparse
import sys
from pathlib import Path

sys.path.insert(0, str(Path(__file__).resolve().parents[2] / "src"))

import pandas as pd

from src.config.backtest import BacktestConfig
from src.orchestrator.backtest import BacktestOrchestrator
from src.core.logger import setup_logger
from src.data.storage.timescaledb import TimescaleDBClient

logger = setup_logger()


async def main():
    parser = argparse.ArgumentParser(description="Run backtest")
    parser.add_argument("--start", required=True, help="Start date YYYY-MM-DD")
    parser.add_argument("--end", required=True, help="End date YYYY-MM-DD")
    parser.add_argument("--symbols", nargs="+", default=["EURUSD", "GBPUSD", "XAUUSD"])
    parser.add_argument("--capital", type=float, default=200)
    parser.add_argument("--risk", type=float, default=0.01)

    args = parser.parse_args()

    config = BacktestConfig()
    config.backtest_start = args.start
    config.backtest_end = args.end
    config.risk.total_capital = args.capital
    config.risk.base_risk = args.risk

    # Load historical data
    data = load_historical_data(args.symbols, args.start, args.end)
    if data.empty:
        logger.error("No data loaded")
        return

    # DB client (optional)
    try:
        db = TimescaleDBClient(config)
    except Exception as e:
        logger.warning(f"DB not available: {e}")
        db = None

    orchestrator = BacktestOrchestrator(config, args.symbols, data, db)
    await orchestrator.start()


def load_historical_data(symbols: list, start: str, end: str) -> pd.DataFrame:
    """Load historical data from CSV or DB"""
    # Placeholder: load from data/historical/*.csv
    data_dir = Path(__file__).resolve().parents[2] / "data" / "historical"
    all_data = []

    for symbol in symbols:
        filepath = data_dir / f"{symbol}_5m_2024.csv"
        if filepath.exists():
            df = pd.read_csv(filepath)
            df['symbol'] = symbol
            # Rename columns to standard
            df.rename(columns={
                'time': 'timestamp',
                'open': 'open',
                'high': 'high',
                'low': 'low',
                'close': 'close',
                'tick_volume': 'volume',
            }, inplace=True)
            df['timestamp'] = pd.to_datetime(df['timestamp'])
            mask = (df['timestamp'] >= start) & (df['timestamp'] <= end)
            all_data.append(df.loc[mask])

    if all_data:
        return pd.concat(all_data, ignore_index=True).sort_values('timestamp')
    return pd.DataFrame()


if __name__ == "__main__":
    asyncio.run(main())

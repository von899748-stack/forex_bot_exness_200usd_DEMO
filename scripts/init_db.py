#!/usr/bin/env python
"""Initialize TimescaleDB with required tables"""
import sys
from pathlib import Path

sys.path.insert(0, str(Path(__file__).resolve().parents[2] / "src"))

from src.config.base import BaseConfig
from src.data.storage.timescaledb import TimescaleDBClient
from src.core.logger import setup_logger

logger = setup_logger()


def main():
    config = BaseConfig()
    db = TimescaleDBClient(config)

    # Ensure tables are created
    # (tables are created by trade_recorder's _ensure_tables)

    # Also create any necessary extensions
    with db.conn.cursor() as cur:
        cur.execute("CREATE EXTENSION IF NOT EXISTS timescaledb;")
        cur.execute("CREATE EXTENSION IF NOT EXISTS pg_stat_statements;")

    logger.info("TimescaleDB initialized successfully")
    db.close()


if __name__ == "__main__":
    main()

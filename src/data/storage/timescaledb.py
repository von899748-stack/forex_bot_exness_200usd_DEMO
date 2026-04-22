"""TimescaleDB client for time-series data storage"""
import psycopg2
from psycopg2.extras import RealDictCursor
from typing import Optional, List, Dict, Any
from datetime import datetime
import pandas as pd
from ...config.base import BaseConfig


class TimescaleDBClient:
    """Client for TimescaleDB operations"""

    def __init__(self, config: BaseConfig):
        self.config = config
        self.conn: Optional[psycopg2.extensions.connection] = None
        self.connect()

    def connect(self) -> bool:
        """Connect to TimescaleDB"""
        try:
            self.conn = psycopg2.connect(
                host=self.config.database.host,
                port=self.config.database.port,
                database=self.config.database.database,
                user=self.config.database.user,
                password=self.config.database.password,
            )
            self.conn.autocommit = True
            self._ensure_extension()
            return True
        except Exception as e:
            print(f"TimescaleDB connection failed: {e}")
            return False

    def _ensure_extension(self):
        """Ensure TimescaleDB extension is enabled"""
        with self.conn.cursor() as cur:
            cur.execute("CREATE EXTENSION IF NOT EXISTS timescaledb CASCADE;")

    def create_hypertable(
        self,
        table_name: str,
        time_column: str = "timestamp",
        chunk_time_interval: str = "1 day"
    ):
        """Convert table to TimescaleDB hypertable"""
        with self.conn.cursor() as cur:
            cur.execute(f"""
                SELECT create_hypertable(
                    '{table_name}', '{time_column}',
                    if_not_exists => TRUE,
                    chunk_time_interval => INTERVAL '{chunk_time_interval}'
                );
            """)

    def execute(self, query: str, params: tuple = None) -> Optional[List[Dict]]:
        """Execute query and return results as dicts"""
        try:
            with self.conn.cursor(cursor_factory=RealDictCursor) as cur:
                cur.execute(query, params)
                if cur.description:
                    return cur.fetchall()
                return None
        except Exception as e:
            print(f"Query error: {e}")
            return None

    def insert(self, table: str, data: Dict[str, Any]) -> bool:
        """Insert single row"""
        columns = list(data.keys())
        placeholders = [f"%({k})s" for k in columns]
        query = f"""
            INSERT INTO {table} ({', '.join(columns)})
            VALUES ({', '.join(placeholders)})
        """
        try:
            with self.conn.cursor() as cur:
                cur.execute(query, data)
            return True
        except Exception as e:
            print(f"Insert error: {e}")
            return False

    def insert_many(self, table: str, rows: List[Dict[str, Any]]) -> bool:
        """Insert multiple rows"""
        if not rows:
            return True
        columns = list(rows[0].keys())
        placeholders = [f"%({k})s" for k in columns]
        query = f"""
            INSERT INTO {table} ({', '.join(columns)})
            VALUES ({', '.join(placeholders)})
        """
        try:
            with self.conn.cursor() as cur:
                cur.executemany(query, rows)
            return True
        except Exception as e:
            print(f"Batch insert error: {e}")
            return False

    def query_to_df(self, query: str, params: tuple = None) -> pd.DataFrame:
        """Execute query and return as DataFrame"""
        result = self.execute(query, params)
        if result:
            return pd.DataFrame(result)
        return pd.DataFrame()

    def close(self):
        """Close connection"""
        if self.conn:
            self.conn.close()

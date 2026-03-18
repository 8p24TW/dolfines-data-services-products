from __future__ import annotations

import sqlite3
from pathlib import Path

import pandas as pd


class CacheStore:
    def __init__(self, db_path: Path) -> None:
        self.db_path = Path(db_path)
        self.db_path.parent.mkdir(parents=True, exist_ok=True)
        self._ensure_schema()

    def _connect(self) -> sqlite3.Connection:
        return sqlite3.connect(self.db_path)

    def _ensure_schema(self) -> None:
        with self._connect() as conn:
            conn.execute(
                """
                CREATE TABLE IF NOT EXISTS raw_mentions (
                    record_id TEXT PRIMARY KEY,
                    source TEXT,
                    source_type TEXT,
                    title TEXT,
                    url TEXT,
                    published_at TEXT,
                    hits REAL,
                    engagement REAL,
                    snippet TEXT,
                    topic_hint TEXT,
                    author TEXT,
                    meta_json TEXT,
                    connector TEXT
                )
                """
            )
            conn.execute(
                """
                CREATE TABLE IF NOT EXISTS connector_status (
                    connector TEXT PRIMARY KEY,
                    last_run TEXT,
                    status TEXT,
                    record_count INTEGER,
                    detail TEXT
                )
                """
            )

    def save_mentions(self, mentions: pd.DataFrame) -> None:
        with self._connect() as conn:
            conn.execute("DELETE FROM raw_mentions")
            mentions.to_sql("raw_mentions", conn, if_exists="append", index=False)

    def load_mentions(self) -> pd.DataFrame:
        with self._connect() as conn:
            try:
                return pd.read_sql_query("SELECT * FROM raw_mentions", conn)
            except Exception:
                return pd.DataFrame()

    def save_connector_status(self, statuses: pd.DataFrame) -> None:
        with self._connect() as conn:
            conn.execute("DELETE FROM connector_status")
            statuses.to_sql("connector_status", conn, if_exists="append", index=False)

    def load_connector_status(self) -> pd.DataFrame:
        with self._connect() as conn:
            try:
                return pd.read_sql_query("SELECT * FROM connector_status", conn)
            except Exception:
                return pd.DataFrame()

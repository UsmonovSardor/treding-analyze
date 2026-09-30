"""SQLite holat ombori: dedup (bir marta yozish) va offline retry navbati.

- `seen_trades`: yozilgan position_id lar — dublikatning oldini oladi.
- `retry_queue`: sink xato bergan yozuvlar (internet uzilishi) — keyin qayta uriniladi.
"""
from __future__ import annotations

import json
import sqlite3
import time
from pathlib import Path
from typing import Any


class StateStore:
    def __init__(self, db_path: str | Path):
        self.db_path = str(db_path)
        Path(self.db_path).parent.mkdir(parents=True, exist_ok=True)
        self._conn = sqlite3.connect(self.db_path)
        self._conn.row_factory = sqlite3.Row
        self._init_schema()

    def _init_schema(self) -> None:
        self._conn.executescript(
            """
            CREATE TABLE IF NOT EXISTS seen_trades (
                account     INTEGER NOT NULL,
                position_id INTEGER NOT NULL,
                written     INTEGER NOT NULL DEFAULT 0,
                logged_at   TEXT,
                PRIMARY KEY (account, position_id)
            );

            CREATE TABLE IF NOT EXISTS retry_queue (
                id         INTEGER PRIMARY KEY AUTOINCREMENT,
                sink       TEXT NOT NULL,
                kind       TEXT NOT NULL,          -- 'trade' yoki 'open'
                payload    TEXT NOT NULL,          -- JSON: qatorlar ro'yxati
                attempts   INTEGER NOT NULL DEFAULT 0,
                next_try   REAL NOT NULL DEFAULT 0,
                created_at REAL NOT NULL
            );
            """
        )
        self._conn.commit()

    # ── dedup ──
    def is_written(self, account: int, position_id: int) -> bool:
        row = self._conn.execute(
            "SELECT written FROM seen_trades WHERE account=? AND position_id=?",
            (account, position_id),
        ).fetchone()
        return bool(row and row["written"] == 1)

    def mark_seen(self, account: int, position_id: int) -> None:
        self._conn.execute(
            "INSERT OR IGNORE INTO seen_trades(account, position_id, written) VALUES (?,?,0)",
            (account, position_id),
        )
        self._conn.commit()

    def mark_written(self, account: int, position_id: int, logged_at: str) -> None:
        self._conn.execute(
            """INSERT INTO seen_trades(account, position_id, written, logged_at)
               VALUES (?,?,1,?)
               ON CONFLICT(account, position_id)
               DO UPDATE SET written=1, logged_at=excluded.logged_at""",
            (account, position_id, logged_at),
        )
        self._conn.commit()

    # ── retry queue ──
    def enqueue(self, sink: str, kind: str, rows: list[list[Any]]) -> None:
        self._conn.execute(
            "INSERT INTO retry_queue(sink, kind, payload, attempts, next_try, created_at) "
            "VALUES (?,?,?,0,?,?)",
            (sink, kind, json.dumps(rows), time.time(), time.time()),
        )
        self._conn.commit()

    def due_retries(self, limit: int = 50) -> list[sqlite3.Row]:
        return self._conn.execute(
            "SELECT * FROM retry_queue WHERE next_try<=? ORDER BY id ASC LIMIT ?",
            (time.time(), limit),
        ).fetchall()

    def retry_succeeded(self, retry_id: int) -> None:
        self._conn.execute("DELETE FROM retry_queue WHERE id=?", (retry_id,))
        self._conn.commit()

    def retry_failed(self, retry_id: int, attempts: int) -> None:
        # Exponential backoff: 2^attempts soniya, maksimum 15 daqiqa.
        delay = min(2 ** attempts, 900)
        self._conn.execute(
            "UPDATE retry_queue SET attempts=?, next_try=? WHERE id=?",
            (attempts, time.time() + delay, retry_id),
        )
        self._conn.commit()

    def close(self) -> None:
        self._conn.close()

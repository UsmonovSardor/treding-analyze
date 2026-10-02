"""SQLite holat ombori — YAGONA ISHONCHLI MANBA (source of truth).

- `trades_full`: har savdoning TO'LIQ ma'lumoti (JSON) — o'zgarmas, doimiy. Excel/Sheets
  o'chib ketsa ham shu yerdan to'liq tiklanadi. Hech qachon avtomatik o'chirilmaydi.
- `seen_trades`: yozilgan position_id lar — dublikatning oldini oladi (idempotentlik).
- `retry_queue`: sink xato bergan yozuvlar (internet uzilishi) — keyin qayta uriniladi.

Baza ochilganda avtomatik ZAXIRA nusxa olinadi (data/backups/), WAL rejimi yoqiladi
(ishonchli yozish). Normal ishlashda ma'lumot HECH QACHON o'chirilmaydi.
"""
from __future__ import annotations

import json
import shutil
import sqlite3
import time
from datetime import datetime
from pathlib import Path
from typing import Any, Iterator

_MAX_BACKUPS = 30  # oxirgi 30 kunlik zaxira saqlanadi


class StateStore:
    def __init__(self, db_path: str | Path):
        self.db_path = str(db_path)
        Path(self.db_path).parent.mkdir(parents=True, exist_ok=True)
        self._backup_existing()
        self._conn = sqlite3.connect(self.db_path)
        self._conn.row_factory = sqlite3.Row
        # WAL = yozish paytida nosozlik bo'lsa ham baza buzilmaydi
        self._conn.execute("PRAGMA journal_mode=WAL")
        self._conn.execute("PRAGMA synchronous=FULL")
        self._init_schema()

    def _backup_existing(self) -> None:
        """Baza mavjud bo'lsa — kunlik zaxira nusxa oladi (eski nusxalarni tozalaydi)."""
        src = Path(self.db_path)
        if not src.exists():
            return
        bdir = src.parent / "backups"
        bdir.mkdir(exist_ok=True)
        stamp = datetime.now().strftime("%Y%m%d")
        dst = bdir / f"{src.stem}_{stamp}.db"
        if not dst.exists():
            try:
                shutil.copy2(src, dst)
            except Exception:
                pass
        # eski zaxiralarni tozalash
        backups = sorted(bdir.glob(f"{src.stem}_*.db"))
        for old in backups[:-_MAX_BACKUPS]:
            try:
                old.unlink()
            except Exception:
                pass

    def _init_schema(self) -> None:
        self._conn.executescript(
            """
            CREATE TABLE IF NOT EXISTS trades_full (
                account     INTEGER NOT NULL,
                position_id INTEGER NOT NULL,
                exit_time   TEXT,
                data        TEXT NOT NULL,          -- to'liq Trade (JSON)
                created_at  REAL NOT NULL,
                PRIMARY KEY (account, position_id)
            );

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

    # ── to'liq savdo (source of truth) ──
    def save_trade_full(self, account: int, position_id: int, exit_time: str, data: dict) -> None:
        """Savdoning to'liq ma'lumotini doimiy saqlaydi (mavjud bo'lsa — yangilaydi)."""
        self._conn.execute(
            """INSERT INTO trades_full(account, position_id, exit_time, data, created_at)
               VALUES (?,?,?,?,?)
               ON CONFLICT(account, position_id)
               DO UPDATE SET exit_time=excluded.exit_time, data=excluded.data""",
            (account, position_id, exit_time, json.dumps(data, ensure_ascii=False), time.time()),
        )
        self._conn.commit()

    def iter_all_trades(self, account: int | None = None) -> Iterator[dict]:
        """Barcha saqlangan savdolarni xronologik (exit_time) tartibda qaytaradi."""
        if account is None:
            rows = self._conn.execute(
                "SELECT data FROM trades_full ORDER BY exit_time ASC, created_at ASC"
            )
        else:
            rows = self._conn.execute(
                "SELECT data FROM trades_full WHERE account=? ORDER BY exit_time ASC, created_at ASC",
                (account,),
            )
        for r in rows:
            yield json.loads(r["data"])

    def count_trades(self) -> int:
        return self._conn.execute("SELECT COUNT(*) AS c FROM trades_full").fetchone()["c"]

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

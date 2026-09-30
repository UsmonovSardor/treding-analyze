"""CSV sink — eng oddiy, internetsiz fallback."""
from __future__ import annotations

import csv
import logging
from pathlib import Path
from typing import Any

from .base import Sink

log = logging.getLogger(__name__)


class CsvSink(Sink):
    name = "csv"

    def __init__(self, trades_path: str | Path = "data/trades.csv", open_path: str | Path = "data/open_positions.csv"):
        self.trades_path = Path(trades_path)
        self.open_path = Path(open_path)
        self._trade_header: list[str] = []
        self._open_header: list[str] = []

    def ensure_ready(self, trade_header: list[str], open_header: list[str]) -> None:
        self._trade_header = trade_header
        self._open_header = open_header
        self.trades_path.parent.mkdir(parents=True, exist_ok=True)
        if not self.trades_path.exists():
            self._write(self.trades_path, [trade_header], mode="w")

    def _write(self, path: Path, rows: list[list[Any]], mode: str) -> None:
        with open(path, mode, newline="", encoding="utf-8-sig") as f:
            csv.writer(f).writerows(rows)

    def append_trades(self, rows: list[list[Any]]) -> None:
        if not rows:
            return
        self._write(self.trades_path, rows, mode="a")
        log.info("CSV: %d savdo qo'shildi", len(rows))

    def replace_open_positions(self, rows: list[list[Any]]) -> None:
        self._write(self.open_path, [self._open_header, *rows], mode="w")

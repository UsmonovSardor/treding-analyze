"""Sink interfeysi — barcha yozish manzillari (Sheets/Excel/CSV) shu shaklda."""
from __future__ import annotations

from abc import ABC, abstractmethod
from typing import Any


class Sink(ABC):
    name: str = "base"

    @abstractmethod
    def ensure_ready(self, trade_header: list[str], open_header: list[str]) -> None:
        """Ulanish/fayl/varaq va sarlavhalarni tayyorlaydi."""

    @abstractmethod
    def append_trades(self, rows: list[list[Any]]) -> None:
        """Yopilgan savdo qatorlarini qo'shadi (idempotentlik yuqori qatlamda)."""

    @abstractmethod
    def replace_open_positions(self, rows: list[list[Any]]) -> None:
        """Ochiq pozitsiyalar varag'ini to'liq yangilaydi (jonli holat)."""

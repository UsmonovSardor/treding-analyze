"""Savdo (Trade) va ochiq pozitsiya ma'lumot modellari."""
from __future__ import annotations

from dataclasses import dataclass, asdict, field
from datetime import datetime
from typing import Any

# Jadval ustunlari tartibi — sink'lar shu tartibda yozadi (Sheets/Excel/CSV bir xil).
TRADE_COLUMNS: list[str] = [
    "logged_at", "account", "broker", "position_id", "symbol", "direction",
    "volume", "entry_time", "entry_price", "sl", "tp", "exit_time", "exit_price",
    "close_reason", "pips", "gross_profit", "commission", "swap", "net_pl",
    "risk_amount", "r_multiple", "duration", "balance_after", "magic",
    "comment", "strategy",
]

OPEN_COLUMNS: list[str] = [
    "updated_at", "account", "position_id", "symbol", "direction", "volume",
    "entry_time", "entry_price", "sl", "tp", "current_price",
    "floating_pl", "pips", "magic", "comment",
]


@dataclass
class Trade:
    """Yopilgan savdo — bitta position_id ga tegishli barcha deal'lar jamlangan holat."""
    logged_at: str
    account: int
    broker: str
    position_id: int
    symbol: str
    direction: str            # BUY / SELL
    volume: float
    entry_time: str           # ISO 8601 + offset
    entry_price: float
    sl: float | None
    tp: float | None
    exit_time: str
    exit_price: float
    close_reason: str         # TP / SL / MANUAL / SO / OTHER
    pips: float
    gross_profit: float
    commission: float
    swap: float
    net_pl: float
    risk_amount: float | None
    r_multiple: float | None
    duration: str             # HH:MM:SS
    balance_after: float | None
    magic: int
    comment: str
    strategy: str

    def as_row(self) -> list[Any]:
        d = asdict(self)
        return [d[c] for c in TRADE_COLUMNS]


@dataclass
class OpenPosition:
    """Hozir ochiq turgan pozitsiya (jonli kuzatuv uchun)."""
    updated_at: str
    account: int
    position_id: int
    symbol: str
    direction: str
    volume: float
    entry_time: str
    entry_price: float
    sl: float | None
    tp: float | None
    current_price: float
    floating_pl: float
    pips: float
    magic: int
    comment: str

    def as_row(self) -> list[Any]:
        d = asdict(self)
        return [d[c] for c in OPEN_COLUMNS]

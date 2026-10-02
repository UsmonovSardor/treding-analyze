"""Savdo (Trade) va ochiq pozitsiya ma'lumot modellari."""
from __future__ import annotations

from dataclasses import dataclass, asdict, field
from datetime import datetime
from typing import Any

from . import formatters as fmt

# ── Jadval ustunlari (foydalanuvchi shabloni bo'yicha, aynan shu tartibda) ──
# "№" — sink tomonidan qator raqami sifatida qo'yiladi (as_row() da yo'q).
TRADE_COLUMNS: list[str] = [
    "№", "SANA", "LOT", "ENTRY", "OCHILISH VAQTI", "TYPE",
    "TP", "SL", "YOPILISH VAQTI", "RESULT", "PIPS", "P/L $",
]

OPEN_COLUMNS: list[str] = [
    "№", "SANA", "LOT", "ENTRY", "OCHILISH VAQTI", "TYPE",
    "TP", "SL", "HOZIRGI NARX", "FLOATING $", "PIPS",
]

# Yutuq/zarar belgisi qaysi ustunda — sink shu ustunga qarab qator rangini beradi.
TRADE_SIGN_COL = "RESULT"   # "+" -> yashil, "-" -> qizil
OPEN_SIGN_COL = "FLOATING $"  # "+$" -> yashil, "-$" -> qizil


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

    def to_dict(self) -> dict:
        """To'liq ma'lumotni lug'atga (bazaga saqlash uchun)."""
        return asdict(self)

    @classmethod
    def from_dict(cls, d: dict) -> "Trade":
        """Bazadan tiklash."""
        return cls(**d)

    def as_row(self) -> list[Any]:
        """Shablon tartibidagi qator (№ dan tashqari — uni sink qo'yadi)."""
        return [
            fmt.iso_to_date(self.entry_time),      # SANA
            round(self.volume, 2),                 # LOT
            self.entry_price,                      # ENTRY
            fmt.iso_to_time(self.entry_time),      # OCHILISH VAQTI
            self.direction,                        # TYPE
            self.tp if self.tp else "",            # TP
            self.sl if self.sl else "",            # SL
            fmt.iso_to_time(self.exit_time),       # YOPILISH VAQTI
            fmt.result_sign(self.net_pl),          # RESULT (+/-)
            int(round(abs(self.pips))),            # PIPS (miqdor)
            fmt.format_pl(self.net_pl),            # P/L $
        ]


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
        """Shablon tartibidagi ochiq pozitsiya qatori (№ dan tashqari)."""
        return [
            fmt.iso_to_date(self.entry_time),      # SANA
            round(self.volume, 2),                 # LOT
            self.entry_price,                      # ENTRY
            fmt.iso_to_time(self.entry_time),      # OCHILISH VAQTI
            self.direction,                        # TYPE
            self.tp if self.tp else "",            # TP
            self.sl if self.sl else "",            # SL
            self.current_price,                    # HOZIRGI NARX
            fmt.format_pl(self.floating_pl),       # FLOATING $
            int(round(abs(self.pips))),            # PIPS
        ]

"""Vaqt, pips, R-multiple va davomiylikni senior aniqlikda hisoblovchi yordamchilar."""
from __future__ import annotations

from datetime import datetime, timezone as dt_timezone
from zoneinfo import ZoneInfo


def iso_to_date(iso: str) -> str:
    """ISO 8601 -> 'DD.MM.YY' (masalan '30.09.26')."""
    if not iso:
        return ""
    return datetime.fromisoformat(iso).strftime("%d.%m.%y")


def iso_to_time(iso: str) -> str:
    """ISO 8601 -> 'HH:MM:SS' (masalan '10:15:22')."""
    if not iso:
        return ""
    return datetime.fromisoformat(iso).strftime("%H:%M:%S")


def result_sign(net_pl: float) -> str:
    """Yutuq/zarar belgisi: '+' yoki '-'."""
    return "+" if net_pl >= 0 else "-"


def format_pl(net_pl: float) -> str:
    """Pul natijasi: '+$146.00' yoki '-$15.00'."""
    sign = "+" if net_pl >= 0 else "-"
    return f"{sign}${abs(net_pl):.2f}"


def to_local_iso(epoch_seconds: int | float, tz_name: str) -> str:
    """MT5 dagi UNIX vaqt (UTC) ni foydalanuvchi timezone'sidagi ISO 8601 satriga o'giradi.

    MetaTrader5 kutubxonasi deal/order vaqtini UTC epoch sifatida qaytaradi.
    Natija: '2026-09-30T13:10:44+05:00'.
    """
    dt_utc = datetime.fromtimestamp(float(epoch_seconds), tz=dt_timezone.utc)
    dt_local = dt_utc.astimezone(ZoneInfo(tz_name))
    return dt_local.isoformat(timespec="seconds")


def now_local_iso(tz_name: str) -> str:
    return datetime.now(ZoneInfo(tz_name)).isoformat(timespec="seconds")


def fmt_duration(entry_epoch: float, exit_epoch: float) -> str:
    """Ushlab turish vaqtini HH:MM:SS ko'rinishida (kunlar ham qamrab olinadi)."""
    total = max(0, int(exit_epoch - entry_epoch))
    h, rem = divmod(total, 3600)
    m, s = divmod(rem, 60)
    return f"{h:02d}:{m:02d}:{s:02d}"


def points_to_pips(symbol_info, price_diff: float) -> float:
    """Narx farqini "points" (MT5 nuqta) da qaytaradi.

    Points = price_diff / point. Bu barcha instrument uchun universal va aniq.
    (Klassik "pip" instrumentga bog'liq; senior jurnalda points aniqroq.)
    """
    if symbol_info is None or getattr(symbol_info, "point", 0) in (0, None):
        return round(price_diff, 5)
    return round(price_diff / symbol_info.point, 1)


def signed_pips(symbol_info, entry: float, exit_: float, direction: str) -> float:
    """Yo'nalishni hisobga olgan holda (BUY: exit-entry, SELL: entry-exit) pips/points."""
    raw = (exit_ - entry) if direction == "BUY" else (entry - exit_)
    return points_to_pips(symbol_info, raw)


def compute_risk_and_r(
    symbol_info,
    entry: float,
    sl: float | None,
    volume: float,
    net_pl: float,
    direction: str,
) -> tuple[float | None, float | None]:
    """SL asosida risk summasini ($) va R-multiple ni hisoblaydi.

    risk_amount = |entry - sl| / tick_size * tick_value * volume
    r_multiple  = net_pl / risk_amount

    SL yo'q bo'lsa (0 yoki None) -> (None, None) qaytadi (risksiz savdo).
    """
    if not sl or sl <= 0 or symbol_info is None:
        return None, None

    tick_size = getattr(symbol_info, "trade_tick_size", 0) or getattr(symbol_info, "point", 0)
    tick_value = getattr(symbol_info, "trade_tick_value", 0)
    if not tick_size or not tick_value:
        return None, None

    risk_per_unit = abs(entry - sl)
    risk_amount = (risk_per_unit / tick_size) * tick_value * volume
    if risk_amount <= 0:
        return None, None

    r_multiple = round(net_pl / risk_amount, 2)
    return round(risk_amount, 2), r_multiple


# MT5 deal reason kodlarini o'qiladigan matnga o'giradi.
# (MetaTrader5.DEAL_REASON_* qiymatlari.)
_DEAL_REASON_MAP = {
    0: "CLIENT",   # DEAL_REASON_CLIENT (manual, terminaldan)
    1: "MOBILE",
    2: "WEB",
    3: "EXPERT",   # EA
    4: "SL",       # DEAL_REASON_SL
    5: "TP",       # DEAL_REASON_TP
    6: "SO",       # DEAL_REASON_SO (Stop Out)
    7: "ROLLOVER",
    8: "VMARGIN",
    9: "SPLIT",
}


def close_reason_label(deal_reason: int | None) -> str:
    """Yopilish sababini matnga: TP/SL/SO -> o'zi; boshqasi -> MANUAL/OTHER."""
    if deal_reason is None:
        return "OTHER"
    label = _DEAL_REASON_MAP.get(int(deal_reason), "OTHER")
    if label in ("TP", "SL", "SO"):
        return label
    if label in ("CLIENT", "MOBILE", "WEB"):
        return "MANUAL"
    if label == "EXPERT":
        return "EXPERT"
    return "OTHER"

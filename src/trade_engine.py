"""Deal'lardan yopilgan savdolarni (Trade) va ochiq pozitsiyalarni quradi.

MT5 mantiqi:
- Har `deal` bir position_id ga tegishli. Bitta pozitsiya bir necha deal'dan iborat
  bo'lishi mumkin (kirish + qisman/to'liq chiqishlar).
- `entry` maydoni: 0=IN (kirish), 1=OUT (chiqish), 2=INOUT (reversal), 3=OUT_BY.
- Pozitsiya "yopilgan" deb hisoblanadi: chiqish hajmi kirish hajmiga teng (yoki katta),
  VA hozir ochiq pozitsiyalar ro'yxatida yo'q.
- SL/TP deal'da bo'lmaydi -> history_orders'dan olinadi.
"""
from __future__ import annotations

import logging

import MetaTrader5 as mt5

from . import formatters as fmt
from .models import Trade, OpenPosition

log = logging.getLogger(__name__)

DEAL_ENTRY_IN = 0
DEAL_ENTRY_OUT = 1
DEAL_ENTRY_INOUT = 2
DEAL_ENTRY_OUT_BY = 3

DEAL_TYPE_BUY = 0
DEAL_TYPE_SELL = 1


def _wavg(pairs: list[tuple[float, float]]) -> float:
    """Hajm bo'yicha o'rtacha narx: pairs = [(price, volume), ...]."""
    tv = sum(v for _, v in pairs)
    if tv <= 0:
        return pairs[0][0] if pairs else 0.0
    return sum(p * v for p, v in pairs) / tv


def _order_sl_tp(position_id: int) -> tuple[float | None, float | None]:
    """Pozitsiyaning SL/TP sini history_orders'dan oladi (oxirgi nolga teng bo'lmagani)."""
    orders = mt5.history_orders_get(position=position_id)
    sl = tp = None
    if orders:
        for o in orders:
            if getattr(o, "sl", 0):
                sl = o.sl
            if getattr(o, "tp", 0):
                tp = o.tp
    return sl, tp


def build_closed_trades(deals, open_position_ids: set[int], tz: str) -> list[Trade]:
    """Yopilgan savdolar ro'yxatini quradi."""
    # position_id bo'yicha guruhlash
    groups: dict[int, list] = {}
    for d in deals:
        pid = getattr(d, "position_id", 0)
        if not pid:
            continue
        groups.setdefault(pid, []).append(d)

    trades: list[Trade] = []
    for pid, glist in groups.items():
        if pid in open_position_ids:
            continue  # hali ochiq

        ins = [d for d in glist if d.entry == DEAL_ENTRY_IN]
        outs = [d for d in glist if d.entry in (DEAL_ENTRY_OUT, DEAL_ENTRY_OUT_BY, DEAL_ENTRY_INOUT)]
        if not ins or not outs:
            continue  # to'liq savdo emas

        in_vol = sum(d.volume for d in ins)
        out_vol = sum(d.volume for d in outs)
        if out_vol + 1e-9 < in_vol:
            continue  # hali to'liq yopilmagan (qisman ochiq)

        first_in = min(ins, key=lambda d: d.time)
        last_out = max(outs, key=lambda d: d.time)

        symbol = first_in.symbol
        sinfo = mt5.symbol_info(symbol)

        direction = "BUY" if first_in.type == DEAL_TYPE_BUY else "SELL"
        entry_price = _wavg([(d.price, d.volume) for d in ins])
        exit_price = _wavg([(d.price, d.volume) for d in outs])

        gross_profit = sum(d.profit for d in outs)
        commission = sum(d.commission for d in glist)
        swap = sum(d.swap for d in glist)
        net_pl = round(gross_profit + commission + swap, 2)

        sl, tp = _order_sl_tp(pid)
        pips = fmt.signed_pips(sinfo, entry_price, exit_price, direction)
        risk_amount, r_multiple = fmt.compute_risk_and_r(
            sinfo, entry_price, sl, in_vol, net_pl, direction
        )

        magic = getattr(first_in, "magic", 0) or 0
        comment = (getattr(last_out, "comment", "") or getattr(first_in, "comment", "") or "").strip()
        strategy = _derive_strategy(magic, comment)

        acc = mt5.account_info()
        trades.append(
            Trade(
                logged_at=fmt.now_local_iso(tz),
                account=acc.login if acc else 0,
                broker=acc.server if acc else "",
                position_id=pid,
                symbol=symbol,
                direction=direction,
                volume=round(in_vol, 2),
                entry_time=fmt.to_local_iso(first_in.time, tz),
                entry_price=round(entry_price, 5),
                sl=round(sl, 5) if sl else None,
                tp=round(tp, 5) if tp else None,
                exit_time=fmt.to_local_iso(last_out.time, tz),
                exit_price=round(exit_price, 5),
                close_reason=fmt.close_reason_label(getattr(last_out, "reason", None)),
                pips=pips,
                gross_profit=round(gross_profit, 2),
                commission=round(commission, 2),
                swap=round(swap, 2),
                net_pl=net_pl,
                risk_amount=risk_amount,
                r_multiple=r_multiple,
                duration=fmt.fmt_duration(first_in.time, last_out.time),
                balance_after=None,
                magic=magic,
                comment=comment,
                strategy=strategy,
            )
        )
    return trades


def build_open_positions(positions, tz: str) -> list[OpenPosition]:
    """Hozir ochiq pozitsiyalarni jonli kuzatuv uchun model qiladi."""
    acc = mt5.account_info()
    result: list[OpenPosition] = []
    for p in positions:
        sinfo = mt5.symbol_info(p.symbol)
        direction = "BUY" if p.type == DEAL_TYPE_BUY else "SELL"
        pips = fmt.signed_pips(sinfo, p.price_open, p.price_current, direction)
        result.append(
            OpenPosition(
                updated_at=fmt.now_local_iso(tz),
                account=acc.login if acc else 0,
                position_id=p.identifier,
                symbol=p.symbol,
                direction=direction,
                volume=round(p.volume, 2),
                entry_time=fmt.to_local_iso(p.time, tz),
                entry_price=round(p.price_open, 5),
                sl=round(p.sl, 5) if p.sl else None,
                tp=round(p.tp, 5) if p.tp else None,
                current_price=round(p.price_current, 5),
                floating_pl=round(p.profit, 2),
                pips=pips,
                magic=p.magic or 0,
                comment=(p.comment or "").strip(),
            )
        )
    return result


def _derive_strategy(magic: int, comment: str) -> str:
    """Strategiya nomini magic yoki comment'dan chiqaradi."""
    if comment:
        return comment
    if magic and magic != 0:
        return f"magic:{magic}"
    return "MANUAL"

"""Kirish nuqtasi: MT5 ni kuzatib, yopilgan savdolarni jurnalga yozadigan doimiy xizmat.

Ishga tushirish:
    python -m src.main            # doimiy poll (daemon)
    python -m src.main --once     # bir marta tekshirib chiqib to'xtaydi
"""
from __future__ import annotations

import argparse
import json
import logging
import signal
import sys
import time
from logging.handlers import RotatingFileHandler

from .config import load_settings, PROJECT_ROOT
from .models import TRADE_COLUMNS, OPEN_COLUMNS
from .mt5_client import MT5Client
from .notifier import Notifier
from .state import StateStore
from .trade_engine import build_closed_trades, build_open_positions

log = logging.getLogger("mt5_journal")

_STOP = False


def _setup_logging() -> None:
    (PROJECT_ROOT / "logs").mkdir(exist_ok=True)
    handler = RotatingFileHandler(
        PROJECT_ROOT / "logs" / "journal.log", maxBytes=5_000_000, backupCount=5, encoding="utf-8"
    )
    logging.basicConfig(
        level=logging.INFO,
        format="%(asctime)s %(levelname)s %(name)s: %(message)s",
        handlers=[handler, logging.StreamHandler(sys.stdout)],
    )


def _build_sinks(s):
    """Yoqilgan sink'lar ro'yxatini quradi."""
    sinks = []
    if s.enable_google_sheets:
        if not s.google_sheet_id:
            log.warning("ENABLE_GOOGLE_SHEETS=true, lekin GOOGLE_SHEET_ID yo'q — o'tkazib yuborildi")
        else:
            from .sinks.google_sheets import GoogleSheetsSink
            sinks.append(GoogleSheetsSink(
                s.abs_path(s.google_credentials_path), s.google_sheet_id, s.sheet_trades, s.sheet_open
            ))
    if s.enable_excel:
        from .sinks.excel import ExcelSink
        sinks.append(ExcelSink(s.abs_path(s.excel_path), s.sheet_trades, s.sheet_open))
    if s.enable_csv:
        from .sinks.csv_sink import CsvSink
        sinks.append(CsvSink(s.abs_path("data/trades.csv"), s.abs_path("data/open_positions.csv")))
    return sinks


def _flush_retries(state: StateStore, sinks_by_name: dict) -> None:
    """Offline navbatdagi yozuvlarni qayta urinib ko'radi."""
    for row in state.due_retries():
        sink = sinks_by_name.get(row["sink"])
        if sink is None:
            state.retry_succeeded(row["id"])  # sink o'chirilgan -> tashlab yuboramiz
            continue
        payload = json.loads(row["payload"])
        try:
            if row["kind"] == "trade":
                sink.append_trades(payload)
            else:
                sink.replace_open_positions(payload)
            state.retry_succeeded(row["id"])
            log.info("Retry muvaffaqiyatli: %s/%s", row["sink"], row["kind"])
        except Exception as e:
            state.retry_failed(row["id"], row["attempts"] + 1)
            log.warning("Retry hali ham xato (%s): %s", row["sink"], e)


def poll_once(mt5c: MT5Client, state: StateStore, sinks, sinks_by_name, notifier, s) -> None:
    # 1) avval offline navbatni bo'shatamiz
    _flush_retries(state, sinks_by_name)

    # 2) ochiq pozitsiyalar
    positions = mt5c.get_open_positions()
    open_ids = {p.identifier for p in positions}
    open_models = build_open_positions(positions, s.timezone)
    open_rows = [m.as_row() for m in open_models]
    for sink in sinks:
        try:
            sink.replace_open_positions(open_rows)
        except Exception as e:
            log.warning("%s open yozishda xato -> navbatga: %s", sink.name, e)
            state.enqueue(sink.name, "open", open_rows)

    # 3) yopilgan savdolar
    deals = mt5c.get_history_deals(s.lookback_days)
    trades = build_closed_trades(deals, open_ids, s.timezone)

    acc = mt5c.account()
    acc_login = acc.login if acc else 0

    new_trades = [t for t in trades if not state.is_written(acc_login, t.position_id)]
    new_trades.sort(key=lambda t: t.exit_time)  # xronologik tartib

    for t in new_trades:
        row = t.as_row()
        # 1-NAVBATDA: to'liq ma'lumotni doimiy bazaga saqlaymiz (source of truth).
        # Sink'lar keyin yozadi; ular o'chsa ham bazadan tiklanadi.
        state.save_trade_full(t.account, t.position_id, t.exit_time, t.to_dict())
        state.mark_seen(t.account, t.position_id)
        ok_any = False
        for sink in sinks:
            try:
                sink.append_trades([row])
                ok_any = True
            except Exception as e:
                log.warning("%s savdo yozishda xato -> navbatga: %s", sink.name, e)
                state.enqueue(sink.name, "trade", [row])
                ok_any = True  # navbatga olindi -> yo'qolmaydi
        if ok_any:
            state.mark_written(t.account, t.position_id, t.logged_at)
            notifier.notify_trade(t)
            log.info("Savdo yozildi: %s %s %s net=%.2f", t.symbol, t.direction, t.position_id, t.net_pl)

    if new_trades:
        log.info("Jami %d yangi savdo qayd etildi", len(new_trades))


def _handle_signal(signum, frame):
    global _STOP
    _STOP = True
    log.info("To'xtatish signali qabul qilindi (%s) — yakunlanmoqda...", signum)


def main() -> None:
    global _STOP
    parser = argparse.ArgumentParser(description="MT5 Trade Journal")
    parser.add_argument("--once", action="store_true", help="bir marta tekshirib to'xtaydi")
    args = parser.parse_args()

    _setup_logging()
    s = load_settings()

    signal.signal(signal.SIGINT, _handle_signal)
    signal.signal(signal.SIGTERM, _handle_signal)

    mt5c = MT5Client(s.mt5_login, s.mt5_password, s.mt5_server, s.mt5_terminal_path)
    mt5c.connect()

    state = StateStore(s.abs_path(s.state_db_path))
    notifier = Notifier(s.enable_telegram, s.telegram_bot_token, s.telegram_chat_id)

    sinks = _build_sinks(s)
    if not sinks:
        log.error("Birorta ham sink yoqilmagan. .env da ENABLE_* ni tekshiring.")
        return
    for sink in sinks:
        sink.ensure_ready(TRADE_COLUMNS, OPEN_COLUMNS)
    sinks_by_name = {sink.name: sink for sink in sinks}

    log.info("Xizmat ishga tushdi. Sink'lar: %s. Interval: %ss",
             ", ".join(sinks_by_name), s.poll_interval_seconds)

    try:
        while not _STOP:
            try:
                poll_once(mt5c, state, sinks, sinks_by_name, notifier, s)
            except Exception as e:
                log.exception("Poll siklida kutilmagan xato: %s", e)
            if args.once:
                break
            for _ in range(s.poll_interval_seconds):
                if _STOP:
                    break
                time.sleep(1)
    finally:
        state.close()
        mt5c.shutdown()
        log.info("Xizmat to'xtadi.")


if __name__ == "__main__":
    main()

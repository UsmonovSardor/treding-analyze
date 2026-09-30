"""O'tmishdagi savdolarni bir marta import qilish (backfill).

Ishlatish:
    python -m scripts.backfill --days 365

Barcha eski savdolarni sink'larga yozadi. Dedup tufayli qayta ishlatsangiz
dublikat bo'lmaydi.
"""
from __future__ import annotations

import argparse
import logging
import sys

from src.config import load_settings
from src.main import _build_sinks
from src.models import TRADE_COLUMNS, OPEN_COLUMNS
from src.mt5_client import MT5Client
from src.state import StateStore
from src.trade_engine import build_closed_trades

logging.basicConfig(level=logging.INFO, format="%(asctime)s %(levelname)s: %(message)s",
                    handlers=[logging.StreamHandler(sys.stdout)])
log = logging.getLogger("backfill")


def main() -> None:
    parser = argparse.ArgumentParser()
    parser.add_argument("--days", type=int, default=365, help="necha kunlik tarix (default 365)")
    args = parser.parse_args()

    s = load_settings()
    mt5c = MT5Client(s.mt5_login, s.mt5_password, s.mt5_server, s.mt5_terminal_path)
    mt5c.connect()

    state = StateStore(s.abs_path(s.state_db_path))
    sinks = _build_sinks(s)
    for sink in sinks:
        sink.ensure_ready(TRADE_COLUMNS, OPEN_COLUMNS)

    deals = mt5c.get_history_deals(args.days)
    open_ids = {p.identifier for p in mt5c.get_open_positions()}
    trades = build_closed_trades(deals, open_ids, s.timezone)
    trades.sort(key=lambda t: t.exit_time)

    acc = mt5c.account()
    acc_login = acc.login if acc else 0

    count = 0
    for t in trades:
        if state.is_written(acc_login, t.position_id):
            continue
        row = t.as_row()
        for sink in sinks:
            sink.append_trades([row])
        state.mark_written(t.account, t.position_id, t.logged_at)
        count += 1

    log.info("Backfill tugadi: %d savdo import qilindi (%d kun).", count, args.days)
    state.close()
    mt5c.shutdown()


if __name__ == "__main__":
    main()

"""Excel va Google Sheets'ni BAZADAN (source of truth) to'liq qayta tiklash.

Qachon kerak:
- Excel/Google Sheet faylini tasodifan o'chirib qo'ysangiz
- Jadval buzilsa yoki tartib chalkashsa
- Yangi jadval/kompyuterga ma'lumotni ko'chirsangiz

Ishlatish (MT5 kerak EMAS — faqat lokal baza o'qiladi):
    python -m scripts.rebuild

Baza (data/journal.db) har savdoning to'liq nusxasini saqlaydi, shuning uchun
jadvallar istalgan vaqt to'liq tiklanadi. Baza hech qachon o'chirilmaydi.
"""
from __future__ import annotations

import logging
import sys

from src.config import load_settings
from src.main import _build_sinks
from src.models import Trade, TRADE_COLUMNS, OPEN_COLUMNS
from src.state import StateStore

logging.basicConfig(level=logging.INFO, format="%(asctime)s %(levelname)s: %(message)s",
                    handlers=[logging.StreamHandler(sys.stdout)])
log = logging.getLogger("rebuild")


def main() -> None:
    s = load_settings()
    state = StateStore(s.abs_path(s.state_db_path))

    total = state.count_trades()
    if total == 0:
        log.warning("Bazada savdo yo'q — tiklash uchun ma'lumot topilmadi.")
        return

    sinks = _build_sinks(s)
    if not sinks:
        log.error("Birorta sink yoqilmagan (.env ENABLE_* ni tekshiring).")
        return

    for sink in sinks:
        sink.ensure_ready(TRADE_COLUMNS, OPEN_COLUMNS)
        sink.reset_trades()  # tozalab, boshidan yozamiz (dublikatsiz)

    rows = [Trade.from_dict(d).as_row() for d in state.iter_all_trades()]
    for sink in sinks:
        sink.append_trades(rows)
        log.info("%s: %d savdo tiklandi", sink.name, len(rows))

    log.info("Tiklash tugadi: jami %d savdo bazadan qayta yozildi.", len(rows))
    state.close()


if __name__ == "__main__":
    main()

"""Ixtiyoriy Telegram bildirishnoma (savdo yopildi / xatolik)."""
from __future__ import annotations

import logging

import requests

log = logging.getLogger(__name__)


class Notifier:
    def __init__(self, enabled: bool, bot_token: str | None, chat_id: str | None):
        self.enabled = enabled and bool(bot_token) and bool(chat_id)
        self.bot_token = bot_token
        self.chat_id = chat_id

    def send(self, text: str) -> None:
        if not self.enabled:
            return
        try:
            requests.post(
                f"https://api.telegram.org/bot{self.bot_token}/sendMessage",
                json={"chat_id": self.chat_id, "text": text, "parse_mode": "HTML"},
                timeout=10,
            )
        except Exception as e:  # bildirishnoma xatosi asosiy oqimni to'xtatmaydi
            log.warning("Telegram xato: %s", e)

    def notify_trade(self, t) -> None:
        emoji = "🟢" if t.net_pl >= 0 else "🔴"
        r = f" | {t.r_multiple:+}R" if t.r_multiple is not None else ""
        self.send(
            f"{emoji} <b>{t.symbol} {t.direction}</b> {t.volume} lot\n"
            f"P/L: <b>{t.net_pl:+.2f}</b>{r} ({t.close_reason})\n"
            f"{t.entry_price} → {t.exit_price} | {t.duration}"
        )

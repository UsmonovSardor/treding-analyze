"""MetaTrader5 terminaliga ulanish va tarix/pozitsiyalarni o'qish."""
from __future__ import annotations

import logging
from datetime import datetime, timedelta, timezone

import MetaTrader5 as mt5

log = logging.getLogger(__name__)


class MT5Client:
    def __init__(
        self,
        login: int | None = None,
        password: str | None = None,
        server: str | None = None,
        terminal_path: str | None = None,
    ):
        self.login = login
        self.password = password
        self.server = server
        self.terminal_path = terminal_path
        self._connected = False

    def connect(self) -> None:
        """MT5 ga ulanadi. Login berilmasa, ochiq terminal sessiyasidan foydalanadi."""
        kwargs: dict = {}
        if self.terminal_path:
            kwargs["path"] = self.terminal_path
        if self.login and self.password and self.server:
            kwargs.update(login=int(self.login), password=self.password, server=self.server)

        if not mt5.initialize(**kwargs):
            code, msg = mt5.last_error()
            raise ConnectionError(f"MT5 initialize xato [{code}]: {msg}")

        info = mt5.account_info()
        if info is None:
            code, msg = mt5.last_error()
            raise ConnectionError(f"MT5 account_info yo'q [{code}]: {msg}")

        self._connected = True
        log.info(
            "MT5 ulandi: login=%s server=%s balance=%.2f %s",
            info.login, info.server, info.balance, info.currency,
        )

    def account(self):
        return mt5.account_info()

    def symbol_info(self, symbol: str):
        return mt5.symbol_info(symbol)

    def symbol_tick(self, symbol: str):
        return mt5.symbol_info_tick(symbol)

    def get_history_deals(self, lookback_days: int):
        """Oxirgi `lookback_days` kunlik barcha deal'larni qaytaradi."""
        to_dt = datetime.now(timezone.utc) + timedelta(days=1)   # kelajakka biroz zaxira
        from_dt = to_dt - timedelta(days=lookback_days + 1)
        deals = mt5.history_deals_get(from_dt, to_dt)
        return list(deals) if deals else []

    def get_open_positions(self):
        positions = mt5.positions_get()
        return list(positions) if positions else []

    def shutdown(self) -> None:
        if self._connected:
            mt5.shutdown()
            self._connected = False
            log.info("MT5 uzildi.")

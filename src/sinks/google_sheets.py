"""Google Sheets sink — gspread + service account. Asosiy bulut manzil."""
from __future__ import annotations

import logging
from pathlib import Path
from typing import Any

import gspread
from google.oauth2.service_account import Credentials

from .base import Sink

log = logging.getLogger(__name__)

_SCOPES = ["https://www.googleapis.com/auth/spreadsheets"]


class GoogleSheetsSink(Sink):
    name = "google_sheets"

    def __init__(
        self,
        credentials_path: str | Path,
        sheet_id: str,
        trades_sheet: str = "Trades",
        open_sheet: str = "Open_Positions",
    ):
        self.credentials_path = str(credentials_path)
        self.sheet_id = sheet_id
        self.trades_sheet = trades_sheet
        self.open_sheet = open_sheet
        self._gc: gspread.Client | None = None
        self._ss = None
        self._ws_trades = None
        self._ws_open = None
        self._open_header: list[str] = []

    def ensure_ready(self, trade_header: list[str], open_header: list[str]) -> None:
        self._open_header = open_header
        creds = Credentials.from_service_account_file(self.credentials_path, scopes=_SCOPES)
        self._gc = gspread.authorize(creds)
        self._ss = self._gc.open_by_key(self.sheet_id)

        self._ws_trades = self._get_or_create(self.trades_sheet, len(trade_header))
        self._ws_open = self._get_or_create(self.open_sheet, len(open_header))

        self._ensure_header(self._ws_trades, trade_header)
        self._ensure_header(self._ws_open, open_header)
        log.info("Google Sheets ulandi: %s", self.sheet_id)

    def _get_or_create(self, title: str, cols: int):
        try:
            return self._ss.worksheet(title)
        except gspread.WorksheetNotFound:
            return self._ss.add_worksheet(title=title, rows=1000, cols=max(cols, 26))

    @staticmethod
    def _ensure_header(ws, header: list[str]) -> None:
        first = ws.row_values(1)
        if first != header:
            ws.update([header], "A1", value_input_option="USER_ENTERED")
            ws.freeze(rows=1)

    def append_trades(self, rows: list[list[Any]]) -> None:
        if not rows:
            return
        # None -> "" (gspread None ni yoqtirmaydi)
        clean = [[("" if v is None else v) for v in r] for r in rows]
        self._ws_trades.append_rows(clean, value_input_option="USER_ENTERED")
        log.info("Google Sheets: %d savdo qo'shildi", len(rows))

    def replace_open_positions(self, rows: list[list[Any]]) -> None:
        clean = [[("" if v is None else v) for v in r] for r in rows]
        self._ws_open.clear()
        self._ws_open.update([self._open_header, *clean], "A1", value_input_option="USER_ENTERED")
        self._ws_open.freeze(rows=1)

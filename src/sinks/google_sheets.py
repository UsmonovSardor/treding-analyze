"""Google Sheets sink — gspread + service account. Senior ko'rinish:
ko'k sarlavha, yashil/qizil qatorlar (shartli formatlash), № avtomatik."""
from __future__ import annotations

import logging
from pathlib import Path
from typing import Any

import gspread
from google.oauth2.service_account import Credentials

from .base import Sink
from ..models import TRADE_SIGN_COL

log = logging.getLogger(__name__)

_SCOPES = ["https://www.googleapis.com/auth/spreadsheets"]


def _san(v):
    """Google Sheets '+' yoki '=' bilan boshlangan matnni formula deb o'ylaydi.
    Oldiga apostrof qo'yib, sof matn sifatida saqlaymiz (apostrof ko'rinmaydi)."""
    if v is None:
        return ""
    if isinstance(v, str) and v[:1] in ("=", "+", "-", "@"):
        return "'" + v
    return v

# Ranglar (0..1 RGB)
_BLUE = {"red": 0.267, "green": 0.447, "blue": 0.769}
_WHITE = {"red": 1, "green": 1, "blue": 1}
_GREEN = {"red": 0.663, "green": 0.816, "blue": 0.557}
_RED = {"red": 0.957, "green": 0.475, "blue": 0.420}


class GoogleSheetsSink(Sink):
    name = "google_sheets"

    def __init__(self, credentials_path, sheet_id, trades_sheet="Trades", open_sheet="Open_Positions"):
        self.credentials_path = str(credentials_path)
        self.sheet_id = sheet_id
        self.trades_sheet = trades_sheet
        self.open_sheet = open_sheet
        self._gc = None
        self._ss = None
        self._ws_trades = None
        self._ws_open = None
        self._trade_header: list[str] = []
        self._open_header: list[str] = []

    def ensure_ready(self, trade_header: list[str], open_header: list[str]) -> None:
        self._trade_header = trade_header
        self._open_header = open_header
        creds = Credentials.from_service_account_file(self.credentials_path, scopes=_SCOPES)
        self._gc = gspread.authorize(creds)
        self._ss = self._gc.open_by_key(self.sheet_id)

        # Kasr ajratuvchisi nuqta bo'lishi uchun til en_US (157.035, vergul emas)
        try:
            self._ss.batch_update({"requests": [{
                "updateSpreadsheetProperties": {
                    "properties": {"locale": "en_US"}, "fields": "locale",
                }}]})
        except Exception:
            pass

        self._ws_trades = self._get_or_create(self.trades_sheet, len(trade_header))
        self._ws_open = self._get_or_create(self.open_sheet, len(open_header))
        self._ensure_header(self._ws_trades, trade_header)
        self._ensure_header(self._ws_open, open_header)
        self._ensure_conditional_formatting(self._ws_trades, len(trade_header))
        log.info("Google Sheets ulandi: %s", self.sheet_id)

    def _get_or_create(self, title: str, cols: int):
        try:
            return self._ss.worksheet(title)
        except gspread.WorksheetNotFound:
            return self._ss.add_worksheet(title=title, rows=2000, cols=max(cols, 12))

    def _ensure_header(self, ws, header: list[str]) -> None:
        if ws.row_values(1) != header:
            ws.update([header], "A1", value_input_option="USER_ENTERED")
        ws.freeze(rows=1)
        # sarlavhani ko'k + oq qalin qilib bo'yash
        self._ss.batch_update({"requests": [{
            "repeatCell": {
                "range": {"sheetId": ws.id, "startRowIndex": 0, "endRowIndex": 1,
                          "startColumnIndex": 0, "endColumnIndex": len(header)},
                "cell": {"userEnteredFormat": {
                    "backgroundColor": _BLUE,
                    "horizontalAlignment": "CENTER",
                    "textFormat": {"foregroundColor": _WHITE, "bold": True},
                }},
                "fields": "userEnteredFormat(backgroundColor,horizontalAlignment,textFormat)",
            }
        }]})

    def _ensure_conditional_formatting(self, ws, ncols: int) -> None:
        """RESULT ustuni '+' -> yashil qator, '-' -> qizil qator (bir marta)."""
        meta = self._ss.fetch_sheet_metadata()
        for sh in meta.get("sheets", []):
            if sh["properties"]["sheetId"] == ws.id and sh.get("conditionalFormats"):
                return  # allaqachon qo'yilgan
        sign_col_letter = chr(ord("A") + self._trade_header.index(TRADE_SIGN_COL))
        rng = {"sheetId": ws.id, "startRowIndex": 1, "startColumnIndex": 0, "endColumnIndex": ncols}
        self._ss.batch_update({"requests": [
            {"addConditionalFormatRule": {"index": 0, "rule": {
                "ranges": [rng],
                "booleanRule": {
                    "condition": {"type": "CUSTOM_FORMULA",
                                  "values": [{"userEnteredValue": f'=${sign_col_letter}2="+"'}]},
                    "format": {"backgroundColor": _GREEN},
                }}}},
            {"addConditionalFormatRule": {"index": 0, "rule": {
                "ranges": [rng],
                "booleanRule": {
                    "condition": {"type": "CUSTOM_FORMULA",
                                  "values": [{"userEnteredValue": f'=${sign_col_letter}2="-"'}]},
                    "format": {"backgroundColor": _RED},
                }}}},
        ]})

    def append_trades(self, rows: list[list[Any]]) -> None:
        if not rows:
            return
        start = max(0, len(self._ws_trades.get_all_values()) - 1)  # sarlavhasiz
        numbered = [[start + i + 1, *[_san(v) for v in r]] for i, r in enumerate(rows)]
        self._ws_trades.append_rows(numbered, value_input_option="USER_ENTERED")
        log.info("Google Sheets: %d savdo qo'shildi", len(rows))

    def replace_open_positions(self, rows: list[list[Any]]) -> None:
        numbered = [[i + 1, *[_san(v) for v in r]] for i, r in enumerate(rows)]
        self._ws_open.clear()
        self._ws_open.update([self._open_header, *numbered], "A1", value_input_option="USER_ENTERED")
        self._ensure_header(self._ws_open, self._open_header)

"""Excel (.xlsx) sink — lokal zaxira. openpyxl bilan."""
from __future__ import annotations

import logging
from pathlib import Path
from typing import Any

from openpyxl import Workbook, load_workbook
from openpyxl.styles import Font, PatternFill

from .base import Sink

log = logging.getLogger(__name__)

_HEADER_FILL = PatternFill("solid", fgColor="1F2A44")
_HEADER_FONT = Font(color="FFFFFF", bold=True)


class ExcelSink(Sink):
    name = "excel"

    def __init__(self, path: str | Path, trades_sheet: str = "Trades", open_sheet: str = "Open_Positions"):
        self.path = Path(path)
        self.trades_sheet = trades_sheet
        self.open_sheet = open_sheet
        self._trade_header: list[str] = []
        self._open_header: list[str] = []

    def ensure_ready(self, trade_header: list[str], open_header: list[str]) -> None:
        self._trade_header = trade_header
        self._open_header = open_header
        self.path.parent.mkdir(parents=True, exist_ok=True)

        if not self.path.exists():
            wb = Workbook()
            ws = wb.active
            ws.title = self.trades_sheet
            self._write_header(ws, trade_header)
            ws_open = wb.create_sheet(self.open_sheet)
            self._write_header(ws_open, open_header)
            wb.save(self.path)
            log.info("Excel yaratildi: %s", self.path)
        else:
            wb = load_workbook(self.path)
            changed = False
            if self.trades_sheet not in wb.sheetnames:
                self._write_header(wb.create_sheet(self.trades_sheet), trade_header); changed = True
            if self.open_sheet not in wb.sheetnames:
                self._write_header(wb.create_sheet(self.open_sheet), open_header); changed = True
            if changed:
                wb.save(self.path)

    @staticmethod
    def _write_header(ws, header: list[str]) -> None:
        ws.append(header)
        for cell in ws[1]:
            cell.fill = _HEADER_FILL
            cell.font = _HEADER_FONT
        ws.freeze_panes = "A2"

    def append_trades(self, rows: list[list[Any]]) -> None:
        if not rows:
            return
        wb = load_workbook(self.path)
        ws = wb[self.trades_sheet]
        for r in rows:
            ws.append(r)
        wb.save(self.path)
        log.info("Excel: %d savdo qo'shildi", len(rows))

    def replace_open_positions(self, rows: list[list[Any]]) -> None:
        wb = load_workbook(self.path)
        if self.open_sheet in wb.sheetnames:
            del wb[self.open_sheet]
        ws = wb.create_sheet(self.open_sheet)
        self._write_header(ws, self._open_header)
        for r in rows:
            ws.append(r)
        wb.save(self.path)

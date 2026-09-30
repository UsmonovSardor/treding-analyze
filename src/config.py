"""Konfiguratsiya: .env va muhit o'zgaruvchilaridan sozlamalarni yuklaydi va tekshiradi."""
from __future__ import annotations

from pathlib import Path

from pydantic import Field, field_validator
from pydantic_settings import BaseSettings, SettingsConfigDict

# Loyiha ildizi (bu fayldan ikki daraja yuqori: src/config.py -> loyiha/)
PROJECT_ROOT = Path(__file__).resolve().parent.parent


class Settings(BaseSettings):
    """Barcha sozlamalar. .env fayldan yoki muhit o'zgaruvchilaridan o'qiladi."""

    model_config = SettingsConfigDict(
        env_file=PROJECT_ROOT / ".env",
        env_file_encoding="utf-8",
        extra="ignore",
        case_sensitive=False,
    )

    # ── MT5 ──
    mt5_login: int | None = None
    mt5_password: str | None = None
    mt5_server: str | None = None
    mt5_terminal_path: str | None = None

    # ── Umumiy ──
    timezone: str = "Asia/Tashkent"
    poll_interval_seconds: int = 5
    lookback_days: int = 7

    # ── Sink'lar ──
    enable_excel: bool = True
    enable_google_sheets: bool = True
    enable_csv: bool = False

    # ── Excel ──
    excel_path: str = "data/trades.xlsx"

    # ── Google Sheets ──
    google_credentials_path: str = "config/credentials/service_account.json"
    google_sheet_id: str | None = None
    sheet_trades: str = "Trades"
    sheet_open: str = "Open_Positions"

    # ── Telegram ──
    enable_telegram: bool = False
    telegram_bot_token: str | None = None
    telegram_chat_id: str | None = None

    # ── Ichki yo'llar ──
    state_db_path: str = "data/journal.db"

    @field_validator("mt5_login", mode="before")
    @classmethod
    def _empty_login_to_none(cls, v):
        """.env da MT5_LOGIN= bo'sh qolsa -> None (ochiq terminalga ulanadi)."""
        if v is None or (isinstance(v, str) and v.strip() == ""):
            return None
        return v

    @field_validator("mt5_password", "mt5_server", "mt5_terminal_path",
                     "google_sheet_id", "telegram_bot_token", "telegram_chat_id",
                     mode="before")
    @classmethod
    def _empty_str_to_none(cls, v):
        """Bo'sh string maydonlarni None ga aylantiradi."""
        if isinstance(v, str) and v.strip() == "":
            return None
        return v

    def abs_path(self, relative: str) -> Path:
        """Nisbiy yo'lni loyiha ildiziga nisbatan absolyut qiladi."""
        p = Path(relative)
        return p if p.is_absolute() else PROJECT_ROOT / p


def load_settings() -> Settings:
    return Settings()

"""StateStore dedup va retry navbati testlari."""
import tempfile
from pathlib import Path

from src.state import StateStore


def _store():
    d = tempfile.mkdtemp()
    return StateStore(Path(d) / "t.db")


def test_dedup_write_once():
    s = _store()
    assert s.is_written(111, 999) is False
    s.mark_seen(111, 999)
    assert s.is_written(111, 999) is False  # ko'rildi lekin yozilmadi
    s.mark_written(111, 999, "2026-01-01T00:00:00+05:00")
    assert s.is_written(111, 999) is True
    s.close()


def test_retry_queue():
    s = _store()
    s.enqueue("google_sheets", "trade", [["a", "b"]])
    due = s.due_retries()
    assert len(due) == 1
    rid = due[0]["id"]
    s.retry_failed(rid, 1)
    # backoff tufayli darhol due bo'lmaydi
    assert len(s.due_retries()) == 0
    s.retry_succeeded(rid)
    s.close()

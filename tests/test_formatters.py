"""formatters uchun unit testlar (MT5 kerak emas)."""
from types import SimpleNamespace

from src import formatters as fmt


def test_duration():
    assert fmt.fmt_duration(0, 3661) == "01:01:01"
    assert fmt.fmt_duration(100, 100) == "00:00:00"
    assert fmt.fmt_duration(100, 50) == "00:00:00"  # manfiy -> 0


def test_to_local_iso_tashkent():
    # 2021-01-01 00:00:00 UTC -> Toshkentda +05:00
    iso = fmt.to_local_iso(1609459200, "Asia/Tashkent")
    assert iso == "2021-01-01T05:00:00+05:00"


def test_signed_pips_buy_sell():
    sinfo = SimpleNamespace(point=0.01)  # XAUUSD misoli
    # BUY: 2645 -> 2655 = +1000 points
    assert fmt.signed_pips(sinfo, 2645.0, 2655.0, "BUY") == 1000.0
    # SELL: 2645 -> 2655 = -1000 points
    assert fmt.signed_pips(sinfo, 2645.0, 2655.0, "SELL") == -1000.0


def test_compute_risk_and_r():
    sinfo = SimpleNamespace(trade_tick_size=0.01, trade_tick_value=1.0, point=0.01)
    # entry 2645, SL 2640 -> risk 5.0 / 0.01 * 1.0 * 0.1 lot = 50
    risk, r = fmt.compute_risk_and_r(sinfo, 2645.0, 2640.0, 0.1, 150.0, "BUY")
    assert risk == 50.0
    assert r == 3.0  # 150 / 50


def test_risk_none_without_sl():
    sinfo = SimpleNamespace(trade_tick_size=0.01, trade_tick_value=1.0, point=0.01)
    risk, r = fmt.compute_risk_and_r(sinfo, 2645.0, None, 0.1, 150.0, "BUY")
    assert risk is None and r is None


def test_close_reason_label():
    assert fmt.close_reason_label(5) == "TP"
    assert fmt.close_reason_label(4) == "SL"
    assert fmt.close_reason_label(6) == "SO"
    assert fmt.close_reason_label(0) == "MANUAL"
    assert fmt.close_reason_label(3) == "EXPERT"
    assert fmt.close_reason_label(None) == "OTHER"

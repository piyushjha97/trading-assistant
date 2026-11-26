from concurrent.futures import ThreadPoolExecutor
from datetime import datetime, timedelta
from decimal import Decimal
from pathlib import Path

import pytest

from trading_assistant.market_data.models import Candle
from trading_assistant.paper_trading import JsonPaperTradeStore, PaperTradePlan, PaperTradeTracker

_DAY = "2026-11-26"


def _time(hour: str) -> datetime:
    return datetime.fromisoformat(f"{_DAY}T{hour}:00+05:30")


def _plan(**overrides) -> PaperTradePlan:
    data = {
        "signal_id": "signal-1", "exchange": "NSE", "symbol": "INFY", "interval": "15minute",
        "side": "BUY", "signal_at": _time("09:30"), "expires_at": _time("11:00"),
        "entry_trigger": "100", "entry_limit": "101", "target": "104", "stop": "98",
        "round_trip_cost_bps": "10",
    }
    return PaperTradePlan.model_validate(data | overrides)


def _bar(start: str, open_: str, high: str, low: str, close: str, volume: int = 100) -> Candle:
    return Candle(timestamp=_time(start), open=open_, high=high, low=low, close=close, volume=volume)


def _tracker(tmp_path: Path, **overrides) -> PaperTradeTracker:
    tracker = PaperTradeTracker(JsonPaperTradeStore(tmp_path / "trades.json"))
    tracker.register(_plan(**overrides))
    return tracker


def test_post_signal_and_completed_bars_only(tmp_path: Path) -> None:
    tracker = _tracker(tmp_path)
    signal_bar = _bar("09:30", "100", "106", "99", "105")
    next_bar = _bar("09:45", "99", "101", "99", "100")
    before_publication = tracker.advance("signal-1", [signal_bar, next_bar], as_of=_time("10:01"))
    assert before_publication.status == "PENDING"
    opened = tracker.advance("signal-1", [signal_bar, next_bar], as_of=_time("10:02"))
    assert opened.status == "OPEN"
    assert opened.entry_bar_at == _time("09:45")
    assert opened.entry_fill_price == Decimal("100")


def test_long_target_and_cost_persist_idempotently(tmp_path: Path) -> None:
    tracker = _tracker(tmp_path)
    entry = _bar("09:45", "100.5", "102", "99", "101")
    exit_ = _bar("10:00", "103", "104.5", "101", "104")
    result = tracker.advance("signal-1", [exit_, entry], as_of=_time("10:17"))
    assert result.status == "CLOSED"
    assert result.exit_reason == "TARGET"
    assert result.exit_fill_price == Decimal("104")
    assert result.gross_pnl_per_share == Decimal("3.5")
    assert result.net_pnl_per_share == Decimal("3.3995")
    assert result.outcome == "WIN"
    reloaded = PaperTradeTracker(JsonPaperTradeStore(tmp_path / "trades.json"))
    assert reloaded.register(_plan()) == result
    assert reloaded.advance("signal-1", [entry, exit_], as_of=_time("10:17")) == result


def test_short_gap_through_stop_uses_open_price(tmp_path: Path) -> None:
    tracker = _tracker(tmp_path, side="SELL", entry_limit="99", target="96", stop="102")
    entry = _bar("09:45", "100", "101", "98", "99")
    gap = _bar("10:00", "104", "105", "95", "99")
    result = tracker.advance("signal-1", [entry, gap], as_of=_time("10:17"))
    assert result.exit_reason == "STOP"
    assert result.exit_fill_price == Decimal("104")
    assert result.outcome == "LOSS"


def test_ambiguous_entry_bar_books_stop_before_target(tmp_path: Path) -> None:
    tracker = _tracker(tmp_path)
    bar = _bar("09:45", "99", "106", "97", "104")
    result = tracker.advance("signal-1", [bar], as_of=_time("10:02"))
    assert result.outcome == "LOSS"
    assert result.exit_fill_price == Decimal("98")


def test_unfilled_gap_and_open_trade_time_exit(tmp_path: Path) -> None:
    tracker = _tracker(tmp_path, expires_at=_time("10:15"))
    gap = _bar("09:45", "102", "104", "99", "102")
    revised = tracker.advance("signal-1", [gap], as_of=_time("10:02"))
    assert revised.status == "PENDING"
    entry = _bar("10:00", "100", "102", "99", "101")
    result = tracker.advance("signal-1", [entry], as_of=_time("10:17"))
    assert result.exit_reason == "TIME"
    assert result.exit_fill_price == Decimal("101")
    assert result.outcome == "WIN"


def test_missing_bars_leave_expired_window_unresolved(tmp_path: Path) -> None:
    tracker = _tracker(tmp_path, expires_at=_time("10:15"))
    missing_first = _bar("10:00", "100", "105", "99", "104")
    result = tracker.advance("signal-1", [missing_first], as_of=_time("10:17"))
    assert result.status == "UNRESOLVED"
    assert result.outcome is None


def test_no_entry_expires_and_conflicting_batches_fail_atomically(tmp_path: Path) -> None:
    tracker = _tracker(tmp_path, expires_at=_time("10:00"))
    bar = _bar("09:45", "98", "99", "97", "99")
    conflict = _bar("09:45", "100", "101", "99", "100")
    with pytest.raises(ValueError, match="Conflicting candles"):
        tracker.advance("signal-1", [bar, conflict], as_of=_time("10:02"))
    assert tracker.get("signal-1").last_bar_at is None
    assert tracker.advance("signal-1", [bar], as_of=_time("10:02")).status == "EXPIRED"


def test_concurrent_registrations_preserve_each_signal(tmp_path: Path) -> None:
    path = tmp_path / "trades.json"

    def register(index: int) -> None:
        PaperTradeTracker(JsonPaperTradeStore(path)).register(
            _plan(signal_id=f"signal-{index}", signal_at=_time("09:30") + timedelta(seconds=index)),
        )

    with ThreadPoolExecutor(max_workers=4) as threads:
        list(threads.map(register, range(12)))
    tracker = PaperTradeTracker(JsonPaperTradeStore(path))
    assert len(tracker.list()) == 12
    with pytest.raises(ValueError, match="different paper plan"):
        tracker.register(_plan(target="106"))

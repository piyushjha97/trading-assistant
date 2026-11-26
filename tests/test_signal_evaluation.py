from dataclasses import replace
from datetime import datetime, timedelta
from decimal import Decimal
from types import SimpleNamespace

from fastapi import FastAPI
from fastapi.testclient import TestClient

from trading_assistant.analytics.indicators import IndicatorSnapshot
from trading_assistant.api import signals
from trading_assistant.evaluation.signals import evaluate_signal
from trading_assistant.llm.signal import NoOpSignalModel, SignalAssessment
from trading_assistant.market_context import MarketContext, MarketMetric
from trading_assistant.market_data.models import Candle
from trading_assistant.paper_trading import JsonPaperTradeStore, PaperTradeTracker

BAR = datetime.fromisoformat("2026-11-26T10:00:00+05:30")
CUTOFF = BAR + timedelta(minutes=17)


def _inputs(side="BUY"):
    snapshot = IndicatorSnapshot(
        candle_count=35, last_candle_at=BAR, open=Decimal("100"), high=Decimal("106"),
        low=Decimal("95"), close=Decimal("105"), volume=2000, sma=Decimal("100"), ema=Decimal("100"),
        rsi=Decimal("60"), atr=Decimal("4"), moving_average_period=20, rsi_period=14,
        atr_period=14, relative_volume=Decimal("2"), prior_range_high=Decimal("103"),
        prior_range_low=Decimal("97"),
    )
    momentum = "1"
    if side == "SELL":
        snapshot = replace(snapshot, close=Decimal("96"))
        momentum = "-1"
    metric = MarketMetric(
        kind="benchmark_return", instrument="NSE:NIFTY 50", value=momentum, unit="percent",
        start_bar=BAR - timedelta(minutes=45), end_bar=BAR, received_at=CUTOFF,
    )
    return snapshot, MarketContext(status="available", metrics=(metric,))


def test_rules_emit_both_sides_with_ordered_prices():
    for side in ("BUY", "SELL"):
        snapshot, market = _inputs(side)
        result = evaluate_signal("NSE:INFY", CUTOFF, snapshot, market, Decimal("0.05"), NoOpSignalModel(), allow_short=True)
        assert result.verdict == side
        assert result.model_status == "no_op"
        setup = result.setup
        assert setup is not None
        if side == "BUY":
            assert setup.stop < setup.entry_trigger <= setup.entry_limit < setup.target
        else:
            assert setup.target < setup.entry_limit <= setup.entry_trigger < setup.stop
        assert all(level % Decimal("0.05") == 0 for level in (setup.entry_trigger, setup.entry_limit, setup.stop, setup.target))


def test_model_cannot_bypass_a_gate_or_approve_unknown_evidence():
    snapshot, market = _inputs()

    class BadModel:
        def assess(self, evidence):
            return SignalAssessment(candidate_id=evidence.candidate_id, decision="APPROVE", evidence_ids=("unknown",))

    result = evaluate_signal("NSE:INFY", CUTOFF, snapshot, market, Decimal("0.05"), BadModel(), allow_short=True)
    assert result.verdict == "WAIT"
    assert result.reasons == ("model_evidence_invalid",)

    result = evaluate_signal(
        "NSE:INFY", CUTOFF, snapshot, MarketContext(status="unavailable"),
        Decimal("0.05"), BadModel(), allow_short=True,
    )
    assert result.model_status == "not_called"
    assert result.reasons == ("aligned_benchmark_unavailable",)


def test_api_registers_once_then_books_win_on_refresh(tmp_path, monkeypatch):
    snapshot, market = _inputs()

    class Clock(datetime):
        now_value = CUTOFF

        @classmethod
        def now(cls, tz=None):
            return cls.now_value.astimezone(tz)

    class Provider:
        def candles(self, **query):
            return SimpleNamespace(candles=self.future)

        def equity_tick_size(self, exchange, symbol):
            return Decimal("0.05")

        future = []

    class ContextProvider:
        def __init__(self, *args, **kwargs):
            pass

        def fetch(self, window):
            return market

    monkeypatch.setattr(signals, "datetime", Clock)
    monkeypatch.setattr(signals, "build_technical_evidence", lambda *args: SimpleNamespace(snapshot=snapshot))
    monkeypatch.setattr(signals, "comparison_window", lambda *args: object())
    monkeypatch.setattr(signals, "KiteMarketContextProvider", ContextProvider)
    app = FastAPI()
    app.include_router(signals.router)
    app.state.kite_provider = Provider()
    app.state.signal_model = NoOpSignalModel()
    store = tmp_path / "journal.json"
    app.state.paper_tracker = PaperTradeTracker(JsonPaperTradeStore(store))

    with TestClient(app) as client:
        first = client.post("/api/v1/analyses", json={"exchange": "NSE", "symbol": "INFY"})
        assert first.status_code == 200
        setup = first.json()["setup"]
        assert setup
        Clock.now_value += timedelta(seconds=10)
        again = client.post("/api/v1/analyses", json={"exchange": "NSE", "symbol": "INFY"})
        assert again.json()["setup"] == setup
        assert len(client.get("/api/v1/paper-trades").json()) == 1

        entry, target = Decimal(setup["entry_trigger"]), Decimal(setup["target"])
        app.state.kite_provider.future = [
            Candle(timestamp=BAR + timedelta(minutes=30), open=entry, high=target, low=entry,
                   close=target, volume=1000),
        ]
        Clock.now_value = BAR + timedelta(minutes=47)
        recorded = client.post(f"/api/v1/paper-trades/{setup['signal_id']}/refresh")
        assert recorded.status_code == 200
        assert recorded.json()["outcome"] == "WIN"
        assert recorded.json()["exit_reason"] == "TARGET"

    assert PaperTradeTracker(JsonPaperTradeStore(store)).list()[0].outcome == "WIN"

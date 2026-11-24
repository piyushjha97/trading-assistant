from datetime import datetime, timedelta
from decimal import Decimal
from unittest.mock import Mock

from fastapi import FastAPI
from fastapi.testclient import TestClient

from trading_assistant.analytics.technical_evidence import build_technical_evidence
from trading_assistant.api.technical import router
from trading_assistant.main import provider_error_handler
from trading_assistant.market_data.kite_provider import KiteProviderError
from trading_assistant.market_data.models import Candle, CandleInterval, CandleResponse, Exchange


def candle(timestamp: str | datetime) -> Candle:
    return Candle(
        timestamp=datetime.fromisoformat(timestamp) if isinstance(timestamp, str) else timestamp,
        open=Decimal("100"), high=Decimal("102"), low=Decimal("99"), close=Decimal("101"),
        volume=1000,
    )


def batch(interval: CandleInterval, bars: list[Candle], cutoff: datetime) -> CandleResponse:
    return CandleResponse(
        exchange=Exchange.NSE, symbol="INFY", interval=interval, candles=bars,
        requested_from=cutoff - timedelta(days=14), requested_to=cutoff, received_at=cutoff,
    )


def test_fifteen_minute_waits_for_bar_end_and_publication_buffer() -> None:
    bars = [candle(f"2026-11-23T09:{minute}:00+05:30") for minute in (15, 30, 45)]
    cutoff = datetime.fromisoformat("2026-11-23T09:46:59+05:30")
    window = batch(CandleInterval.FIFTEEN_MINUTE, bars, cutoff)
    before = build_technical_evidence(window, cutoff)
    boundary = build_technical_evidence(window, cutoff + timedelta(seconds=1))

    assert before.snapshot.last_candle_at == bars[0].timestamp
    assert before.excluded_candle_count == 2
    assert boundary.snapshot.last_candle_at == bars[1].timestamp
    assert boundary.excluded_candle_count == 1
    assert boundary.status == "insufficient_history"
    assert boundary.snapshot.sma is None


def test_hourly_evidence_excludes_short_final_bar() -> None:
    bars = [candle(f"2026-11-23T{hour}:15:00+05:30") for hour in (13, 14, 15)]
    cutoff = datetime.fromisoformat("2026-11-23T17:00:00+05:30")
    evidence = build_technical_evidence(batch(CandleInterval.SIXTY_MINUTE, bars, cutoff), cutoff)

    assert evidence.snapshot.last_candle_at == bars[1].timestamp
    assert evidence.excluded_candle_count == 1


def test_daily_evidence_uses_prior_ist_date_even_after_market_close() -> None:
    bars = [candle(f"2026-11-{day}T00:00:00+05:30") for day in (23, 24)]
    cutoff = datetime.fromisoformat("2026-11-24T23:00:00+05:30")
    evidence = build_technical_evidence(batch(CandleInterval.DAY, bars, cutoff), cutoff)

    assert evidence.snapshot.last_candle_at == bars[0].timestamp
    assert evidence.excluded_candle_count == 1


def _client(provider: Mock) -> TestClient:
    app = FastAPI()
    app.state.kite_provider = provider
    app.add_exception_handler(KiteProviderError, provider_error_handler)
    app.include_router(router)
    return TestClient(app)


def test_endpoint_fetches_bounded_window_and_serializes_the_snapshot() -> None:
    provider = Mock()

    def fetch(*, exchange, symbol, interval, start, end):
        assert (exchange, symbol, interval) == (Exchange.NSE, "INFY", CandleInterval.FIFTEEN_MINUTE)
        assert (end - start).days == 14
        first = start.replace(hour=9, minute=15)
        bars = [
            candle(first + timedelta(days=day, minutes=15 * item))
            for day in range(2)
            for item in range(15)
        ]
        return batch(interval, bars, end)

    provider.candles.side_effect = fetch
    with _client(provider) as client:
        response = client.get("/api/v1/technical-evidence?exchange=NSE&symbol=infy&interval=15minute")

    assert response.status_code == 200
    assert response.headers["cache-control"] == "no-store"
    result = response.json()
    assert result["interval"] == "15minute"
    assert result["status"] == "ready"
    assert result["snapshot"]["candle_count"] == 30
    assert result["snapshot"]["sma"] == "101"
    assert Decimal(result["snapshot"]["adx"]) == 0


def test_endpoint_rejects_unsupported_interval_and_propagates_provider_status() -> None:
    provider = Mock()
    provider.candles.side_effect = KiteProviderError("kite_session_expired", "Kite session expired.", 401)
    with _client(provider) as client:
        unsupported = client.get("/api/v1/technical-evidence?exchange=NSE&symbol=INFY&interval=minute")
        expired = client.get("/api/v1/technical-evidence?exchange=NSE&symbol=INFY")

    assert unsupported.status_code == 422
    assert expired.status_code == 401
    assert expired.json()["detail"]["code"] == "kite_session_expired"
    assert provider.candles.call_count == 1

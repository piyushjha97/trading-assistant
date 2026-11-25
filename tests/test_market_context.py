from datetime import datetime, timedelta
from decimal import Decimal
from unittest.mock import Mock
from zoneinfo import ZoneInfo

from fastapi import FastAPI
from fastapi.testclient import TestClient

from trading_assistant.api.market_context import router

from trading_assistant.market_context import (
    ContextRequest,
    MarketContextService,
    SourceItem,
    SourceResult,
    SourceUnavailable,
)
from trading_assistant.market_context.kite import KiteMarketContextProvider
from trading_assistant.market_data.models import Candle, CandleInterval, CandleResponse, Exchange


def _request() -> ContextRequest:
    first = datetime(2025, 1, 2, 9, 15, tzinfo=ZoneInfo("Asia/Kolkata"))
    return ContextRequest(
        exchange=Exchange.NSE, symbol="INFY", interval=CandleInterval.FIFTEEN_MINUTE,
        start_bar=first, end_bar=first + timedelta(minutes=15),
        cutoff=first + timedelta(minutes=32), event_from=first - timedelta(days=1),
    )


class _Candles:
    def __init__(self, missing_sector: bool = False) -> None:
        self.missing_sector = missing_sector

    def candles(self, exchange, symbol, interval, start, end):
        change = {"INFY": 3, "NIFTY 50": 1, "NIFTY IT": 2, "INDIA VIX": 4}[symbol]
        last = start + timedelta(minutes=15)
        candles = [
            Candle(timestamp=timestamp, open=value, high=value, low=value, close=value, volume=0)
            for timestamp, value in [(start, 100), (last, 100 + change)]
            if timestamp < end
            if not (self.missing_sector and symbol == "NIFTY IT" and timestamp == last)
        ]
        return CandleResponse(
            exchange=exchange, symbol=symbol, interval=interval, requested_from=start,
            requested_to=end, received_at=end + timedelta(minutes=18), candles=candles,
        )


def test_kite_adapter_calculates_returns_from_exact_shared_endpoints() -> None:
    adapter = KiteMarketContextProvider(_Candles(), {(Exchange.NSE, "INFY"): "NIFTY IT"})
    snapshot = MarketContextService(market=adapter).fetch(_request())
    assert snapshot.market.status == "available"
    assert {metric.kind: metric.value for metric in snapshot.market.metrics} == {
        "benchmark_return": Decimal("1"),
        "stock_vs_benchmark": Decimal("2"),
        "sector_return": Decimal("2"),
        "stock_vs_sector": Decimal("1"),
        "vix_level": Decimal("104"),
        "vix_change": Decimal("4"),
    }
    assert snapshot.news.status == "not_configured"


def test_kite_adapter_reports_missing_and_forming_bars() -> None:
    adapter = KiteMarketContextProvider(
        _Candles(missing_sector=True), {(Exchange.NSE, "INFY"): "NIFTY IT"},
    )
    request = _request()
    market = adapter.fetch(request)
    assert market.status == "partial"
    assert market.gaps == ("sector_bars_unavailable",)
    assert "stock_vs_sector" not in {metric.kind for metric in market.metrics}
    assert adapter.fetch(request.model_copy(update={"cutoff": request.cutoff - timedelta(minutes=2)})).status == "unavailable"


class _Events:
    def fetch(self, request: ContextRequest) -> SourceResult:
        item = SourceItem(
            source="exchange", record_id="filing-1", title="Scheduled earnings",
            published_at=request.event_from, known_at=request.event_from,
            scheduled_at=request.cutoff + timedelta(days=1), url="https://example.org/filing",
        )
        revision = item.model_copy(update={"title": "Updated schedule", "known_at": request.cutoff})
        future = item.model_copy(update={"title": "Late correction", "known_at": request.cutoff + timedelta(seconds=1)})
        return SourceResult(status="available", items=(future, item, revision))


class _Unavailable:
    def fetch(self, request: ContextRequest) -> SourceResult:
        raise SourceUnavailable


def test_swappable_event_providers_preserve_cutoff_and_independent_failures() -> None:
    snapshot = MarketContextService(catalysts=_Events(), news=_Unavailable()).fetch(_request())
    assert snapshot.market.status == "not_configured"
    assert snapshot.catalysts.status == "available"
    assert [item.title for item in snapshot.catalysts.items] == ["Updated schedule"]
    assert snapshot.news.status == "unavailable"


def test_context_api_selects_latest_session_and_reuses_stock_batch() -> None:
    candles = _Candles()
    provider = Mock()

    def read(exchange, symbol, interval, start, end):
        if symbol != "INFY":
            return candles.candles(exchange, symbol, interval, start, end)
        latest_start = start.astimezone(ZoneInfo("Asia/Kolkata")).replace(hour=9, minute=15, second=0, microsecond=0)
        latest_end = latest_start + timedelta(minutes=15)
        result = candles.candles(exchange, symbol, interval, latest_start, latest_end + timedelta(minutes=1))
        earlier = result.candles[0].model_copy(update={"timestamp": latest_start - timedelta(days=1)})
        return result.model_copy(update={"candles": [earlier, *result.candles]})

    provider.candles.side_effect = read
    app = FastAPI()
    app.state.kite_provider = provider
    app.include_router(router)
    with TestClient(app) as client:
        response = client.get("/api/v1/market-context?exchange=NSE&symbol=INFY")
    assert response.status_code == 200
    payload = response.json()
    first = datetime.fromisoformat(payload["request"]["start_bar"])
    last = datetime.fromisoformat(payload["request"]["end_bar"])
    assert first.hour == 9 and first.minute == 15
    assert last - first == timedelta(minutes=15)
    assert len(payload["market"]["metrics"]) == 6
    assert payload["catalysts"]["status"] == "not_configured"
    assert sum(call.kwargs["symbol"] == "INFY" for call in provider.candles.call_args_list) == 1

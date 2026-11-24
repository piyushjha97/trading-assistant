from datetime import datetime, timedelta
from decimal import Decimal
from zoneinfo import ZoneInfo

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
        candles = [
            Candle(timestamp=timestamp, open=value, high=value, low=value, close=value, volume=0)
            for timestamp, value in [(start, 100), (end, 100 + change)]
            if not (self.missing_sector and symbol == "NIFTY IT" and timestamp == end)
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

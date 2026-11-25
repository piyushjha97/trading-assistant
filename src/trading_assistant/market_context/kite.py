from collections.abc import Mapping
from dataclasses import dataclass
from datetime import datetime, timedelta
from decimal import Decimal
from typing import Literal, Protocol

from trading_assistant.market_context.contracts import ContextRequest, MarketContext, MarketMetric
from trading_assistant.market_data.candle_eligibility import select_completed_candles
from trading_assistant.market_data.kite_provider import KiteProviderError
from trading_assistant.market_data.models import CandleInterval, CandleResponse, Exchange


_BAR_DURATION = {
    CandleInterval.FIFTEEN_MINUTE: timedelta(minutes=15),
    CandleInterval.SIXTY_MINUTE: timedelta(hours=1),
    CandleInterval.DAY: timedelta(days=1),
}


class _CandleReader(Protocol):
    def candles(
        self, exchange: Exchange, symbol: str, interval: CandleInterval, start: datetime, end: datetime,
    ) -> CandleResponse: ...


@dataclass(frozen=True)
class _Endpoints:
    first: Decimal
    last: Decimal
    received_at: datetime

    def percent_return(self) -> Decimal:
        return (self.last - self.first) / self.first * 100


class KiteMarketContextProvider:
    """Calculate benchmark context over exact requested completed-bar timestamps."""

    def __init__(
        self,
        provider: _CandleReader,
        sector_by_listing: Mapping[tuple[Exchange, str], str] | None = None,
        *,
        stock_batch: CandleResponse | None = None,
    ) -> None:
        self._provider = provider
        self._sectors = dict(sector_by_listing or {})
        self._stock_batch = stock_batch

    def fetch(self, request: ContextRequest) -> MarketContext:
        stock = self._endpoints(request, request.exchange, request.symbol, self._stock_batch)
        metrics: list[MarketMetric] = []
        gaps: list[str] = []
        if stock is None:
            gaps.append("stock_bars_unavailable")

        sector = self._sectors.get((request.exchange, request.symbol))
        for role, symbol in (("benchmark", "NIFTY 50"), ("sector", sector), ("volatility", "INDIA VIX")):
            if symbol is None:
                gaps.append("sector_mapping_unavailable")
                continue
            endpoints = self._endpoints(request, Exchange.NSE, symbol)
            if endpoints is None:
                gaps.append(f"{role}_bars_unavailable")
                continue
            values = _metric_values(role, endpoints, stock)
            for kind, value, unit, received_at in values:
                metrics.append(MarketMetric(
                    kind=kind, instrument=f"NSE:{symbol}", value=value, unit=unit,
                    start_bar=request.start_bar, end_bar=request.end_bar, received_at=received_at,
                ))

        return MarketContext(
            provider="kite", metrics=tuple(metrics), gaps=tuple(gaps),
            status="unavailable" if not metrics else "partial" if gaps else "available",
        )

    def _endpoints(
        self, request: ContextRequest, exchange: Exchange, symbol: str,
        batch: CandleResponse | None = None,
    ) -> _Endpoints | None:
        try:
            if batch is None:
                batch = self._provider.candles(
                    exchange=exchange, symbol=symbol, interval=request.interval,
                    start=request.start_bar,
                    # Kite can omit the last bar when the window ends at its start.
                    end=min(request.cutoff, request.end_bar + _BAR_DURATION[request.interval]),
                )
            if (batch.exchange, batch.symbol, batch.interval) != (exchange, symbol, request.interval):
                return None
            candles = select_completed_candles(batch.candles, request.interval, request.cutoff)
        except (KiteProviderError, ValueError):
            return None

        first = [c.close for c in candles if c.timestamp == request.start_bar]
        last = [c.close for c in candles if c.timestamp == request.end_bar]
        if len(first) != 1 or len(last) != 1 or first[0] <= 0 or last[0] <= 0:
            return None
        return _Endpoints(first[0], last[0], batch.received_at)


_Metric = tuple[
    Literal["benchmark_return", "stock_vs_benchmark", "sector_return", "stock_vs_sector", "vix_level", "vix_change"],
    Decimal,
    Literal["percent", "percentage_points", "index_points"],
    datetime,
]


def _metric_values(role: str, index: _Endpoints, stock: _Endpoints | None) -> tuple[_Metric, ...]:
    if role == "volatility":
        return (
            ("vix_level", index.last, "index_points", index.received_at),
            ("vix_change", index.last - index.first, "index_points", index.received_at),
        )
    index_return = index.percent_return()
    return_kind = "benchmark_return" if role == "benchmark" else "sector_return"
    absolute = (return_kind, index_return, "percent", index.received_at)
    if stock is None:
        return (absolute,)
    relative_kind = "stock_vs_benchmark" if role == "benchmark" else "stock_vs_sector"
    relative = (
        relative_kind, stock.percent_return() - index_return, "percentage_points",
        max(stock.received_at, index.received_at),
    )
    return absolute, relative

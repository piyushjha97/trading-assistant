from decimal import Decimal
from typing import Literal, Protocol

from pydantic import AwareDatetime, BaseModel, ConfigDict, Field, model_validator

from trading_assistant.market_data.models import CandleInterval, Exchange


class _Record(BaseModel):
    model_config = ConfigDict(frozen=True, extra="forbid")


class ContextRequest(_Record):
    exchange: Exchange
    symbol: str = Field(pattern=r"^[A-Z0-9&_-]{1,32}$")
    interval: Literal[CandleInterval.FIFTEEN_MINUTE, CandleInterval.SIXTY_MINUTE, CandleInterval.DAY]
    company_name: str | None = None
    start_bar: AwareDatetime
    end_bar: AwareDatetime
    cutoff: AwareDatetime
    event_from: AwareDatetime

    @model_validator(mode="after")
    def check_window(self) -> "ContextRequest":
        if not self.start_bar < self.end_bar < self.cutoff or self.event_from >= self.cutoff:
            raise ValueError("Context requests require ordered bar starts and an event window before the cutoff.")
        return self


class MarketMetric(_Record):
    kind: Literal["benchmark_return", "stock_vs_benchmark", "sector_return", "stock_vs_sector", "vix_level", "vix_change"]
    instrument: str
    value: Decimal
    unit: Literal["percent", "percentage_points", "index_points"]
    start_bar: AwareDatetime
    end_bar: AwareDatetime
    received_at: AwareDatetime


class MarketContext(_Record):
    provider: str | None = None
    metrics: tuple[MarketMetric, ...] = ()
    status: Literal["available", "partial", "unavailable", "not_configured"]
    gaps: tuple[str, ...] = ()


class SourceItem(_Record):
    source: str = Field(min_length=1)
    record_id: str = Field(min_length=1)
    title: str = Field(min_length=1)
    published_at: AwareDatetime
    known_at: AwareDatetime
    scheduled_at: AwareDatetime | None = None
    url: str = Field(pattern=r"^https://[^\s]+$")

    @model_validator(mode="after")
    def check_publication(self) -> "SourceItem":
        if self.known_at < self.published_at:
            raise ValueError("Source items cannot be known before publication.")
        return self


class SourceResult(_Record):
    observed_at: AwareDatetime | None = None
    status: Literal["available", "empty", "partial", "unavailable", "not_configured"]
    items: tuple[SourceItem, ...] = ()


class ContextSnapshot(_Record):
    request: ContextRequest
    market: MarketContext
    catalysts: SourceResult
    news: SourceResult


class SourceUnavailable(Exception):
    """A provider could not complete the requested read."""


class MarketProvider(Protocol):
    def fetch(self, request: ContextRequest) -> MarketContext: ...


class EventProvider(Protocol):
    def fetch(self, request: ContextRequest) -> SourceResult:
        """Return scoped items and declare coverage for the requested window.

        Use 'empty' only for a successful, complete search with no matching items.
        """
        ...

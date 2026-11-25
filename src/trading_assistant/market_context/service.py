from trading_assistant.market_context.contracts import (
    ContextRequest,
    ContextSnapshot,
    EventProvider,
    MarketContext,
    MarketProvider,
    SourceResult,
    SourceUnavailable,
)


class MarketContextService:
    def __init__(
        self,
        market: MarketProvider | None = None,
        catalysts: EventProvider | None = None,
        news: EventProvider | None = None,
    ) -> None:
        self._market = market
        self._catalysts = catalysts
        self._news = news

    def fetch(self, request: ContextRequest) -> ContextSnapshot:
        if self._market is None:
            market = MarketContext(status="not_configured")
        else:
            try:
                market = self._market.fetch(request)
            except SourceUnavailable:
                market = MarketContext(status="unavailable")
        return ContextSnapshot(
            request=request,
            market=market,
            catalysts=_events(self._catalysts, request),
            news=_events(self._news, request),
        )


def _events(provider: EventProvider | None, request: ContextRequest) -> SourceResult:
    if provider is None:
        return SourceResult(status="not_configured")
    try:
        result = provider.fetch(request)
    except SourceUnavailable:
        return SourceResult(status="unavailable")
    if result.status in {"unavailable", "not_configured", "empty"}:
        return SourceResult(status=result.status)

    items = {
        (item.source, item.record_id): item
        for item in sorted(result.items, key=lambda item: item.known_at)
        if request.event_from <= item.published_at <= item.known_at <= request.cutoff
    }
    status = result.status
    if not items and status == "available":
        status = "partial"
    return SourceResult(status=status, items=tuple(items.values()))

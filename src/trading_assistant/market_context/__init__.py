"""Provider-neutral market context retrieval for stock research."""

from trading_assistant.market_context.contracts import (
    ContextRequest,
    ContextSnapshot,
    EventProvider,
    EventRequest,
    MarketContext,
    MarketMetric,
    MarketProvider,
    SourceItem,
    SourceResult,
    SourceUnavailable,
)
from trading_assistant.market_context.service import MarketContextService

__all__ = [
    "ContextRequest",
    "ContextSnapshot",
    "EventProvider",
    "EventRequest",
    "MarketContext",
    "MarketContextService",
    "MarketMetric",
    "MarketProvider",
    "SourceItem",
    "SourceResult",
    "SourceUnavailable",
]

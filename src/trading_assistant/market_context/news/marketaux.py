from datetime import datetime, timezone

from pydantic import ValidationError

from trading_assistant.market_context import ContextRequest, SourceItem, SourceResult, SourceUnavailable
from trading_assistant.market_context.news.http import fetch_object
from trading_assistant.market_data.models import Exchange


class MarketauxNewsProvider:
    """Retrieve the first bounded page of listing-matched Marketaux coverage."""

    def __init__(self, api_token: str) -> None:
        self._api_token = api_token

    def fetch(self, request: ContextRequest) -> SourceResult:
        suffix = "NS" if request.exchange is Exchange.NSE else "BO"
        ticker = f"{request.symbol}.{suffix}"
        payload = fetch_object(
            "https://api.marketaux.com/v1/news/all",
            {
                "api_token": self._api_token, "symbols": ticker,
                "countries": "in", "filter_entities": "true",
                "group_similar": "true", "limit": "3",
                "published_after": request.event_from.astimezone(timezone.utc).strftime("%Y-%m-%dT%H:%M:%S"),
                "published_before": request.cutoff.astimezone(timezone.utc).strftime("%Y-%m-%dT%H:%M:%S"),
            },
        )
        observed_at = datetime.now(timezone.utc)
        articles = payload.get("data")
        if not isinstance(articles, list):
            raise SourceUnavailable("Marketaux returned an invalid article list.")
        items = []
        for article in articles:
            if not isinstance(article, dict):
                continue
            entities = article.get("entities")
            if not isinstance(entities, list) or not any(
                isinstance(entity, dict)
                and entity.get("symbol") == ticker
                and entity.get("country") == "in"
                for entity in entities
            ):
                continue
            try:
                items.append(SourceItem(
                    source=article["source"], record_id=article["uuid"], title=article["title"], url=article["url"],
                    published_at=article["published_at"], known_at=observed_at,
                ))
            except (KeyError, ValidationError):
                continue
        # A single vendor page cannot establish that all material stories were found.
        return SourceResult(status="partial", items=tuple(items), observed_at=observed_at)

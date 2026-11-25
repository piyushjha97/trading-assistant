import re
from datetime import datetime, timezone

from pydantic import ValidationError

from trading_assistant.market_context import ContextRequest, SourceItem, SourceResult, SourceUnavailable
from trading_assistant.market_context.news.http import fetch_object


def _company_key(name: str) -> str:
    words = re.findall(r"[^\W_]+", name.casefold())
    if words and words[-1] in {"limited", "ltd"}:
        words.pop()
    return " ".join(words)


class HypelessNewsProvider:
    """Retrieve a bounded list of entity-tagged headlines from Hypeless."""

    def __init__(self, api_key: str = "") -> None:
        self._api_key = api_key

    def fetch(self, request: ContextRequest) -> SourceResult:
        if not request.company_name:
            return SourceResult(status="partial")
        company = _company_key(request.company_name)
        if not company:
            return SourceResult(status="partial")
        path = "v1/news" if self._api_key else "public/news"
        headers = {"Authorization": f"Bearer {self._api_key}"} if self._api_key else None
        payload = fetch_object(
            f"https://hypeless.in/api/{path}", {"q": request.company_name, "limit": "20"}, headers=headers,
        )
        observed_at = datetime.now(timezone.utc)
        stories = payload.get("stories")
        if not isinstance(stories, list):
            raise SourceUnavailable("Hypeless returned an invalid story list.")

        items = []
        for story in stories:
            if not isinstance(story, dict):
                continue
            companies = story.get("companies")
            if not isinstance(companies, list) or not any(
                isinstance(name, str) and _company_key(name) == company for name in companies
            ):
                continue
            try:
                items.append(SourceItem(
                    source=story["outlet"], record_id=story.get("eventId") or story["link"],
                    title=story["headline"], url=story["link"],
                    published_at=story["publishedAt"], known_at=observed_at,
                ))
            except (KeyError, ValidationError):
                continue
        # Latest-story searches do not establish coverage of the requested window.
        return SourceResult(status="partial", items=tuple(items), observed_at=observed_at)

from datetime import datetime, timedelta, timezone

import pytest

from trading_assistant.market_context import ContextRequest, MarketContextService
from trading_assistant.market_context.news import hypeless, marketaux


def request_for(exchange: str = "NSE") -> ContextRequest:
    now = datetime.now(timezone.utc)
    return ContextRequest(
        exchange=exchange, symbol="INFY", company_name="Infosys Limited", interval="15minute",
        start_bar=now - timedelta(hours=2), end_bar=now - timedelta(hours=1),
        cutoff=now, event_from=now - timedelta(days=7),
    )


@pytest.mark.parametrize("api_key", ["", "test-key"])
def test_hypeless_filters_company_tags_and_preserves_live_observation(monkeypatch, api_key):
    request = request_for()
    verified_story = {
        "outlet": "Example Publisher", "eventId": "published", "headline": "Infosys files results",
        "link": "https://example.org/story", "publishedAt": request.end_bar.isoformat(),
        "companies": ["Infosys"],
    }

    def fetch(url, params, *, headers):
        assert url.endswith("/v1/news" if api_key else "/public/news")
        assert params["q"] == "Infosys Limited"
        assert headers == ({"Authorization": "Bearer test-key"} if api_key else None)
        return {"stories": [
            verified_story,
            {**verified_story, "eventId": "wrong", "companies": ["Infosys Foundation"]},
            {**verified_story, "eventId": "malformed", "link": "javascript:alert(1)"},
            {**verified_story, "eventId": "outside", "publishedAt": request.event_from - timedelta(days=1)},
        ]}

    monkeypatch.setattr(hypeless, "fetch_object", fetch)
    service = MarketContextService(news=hypeless.HypelessNewsProvider(api_key))
    snapshot = service.fetch(request, live_news=True)
    assert snapshot.news.status == "partial"
    assert [item.record_id for item in snapshot.news.items] == ["published"]
    assert snapshot.news.items[0].known_at == snapshot.news.observed_at
    assert snapshot.news.observed_at >= request.cutoff
    assert service.fetch(request).news.items == ()


@pytest.mark.parametrize(("exchange", "ticker", "other"), [("NSE", "INFY.NS", "INFY.BO"), ("BSE", "INFY.BO", "INFY.NS")])
def test_marketaux_uses_vendor_listing_code(monkeypatch, exchange, ticker, other):
    request = request_for(exchange)
    article = {
        "uuid": "match", "title": "Infosys reports results", "source": "example.org",
        "url": "https://example.org/article", "published_at": request.end_bar.isoformat(),
        "entities": [{"symbol": ticker, "country": "in", "exchange": None}],
    }

    def fetch(url, params):
        assert url == "https://api.marketaux.com/v1/news/all"
        assert params["symbols"] == ticker
        assert params["group_similar"] == "true"
        return {"data": [
            article,
            {**article, "uuid": "other", "entities": [{"symbol": other, "country": "in"}]},
        ]}

    monkeypatch.setattr(marketaux, "fetch_object", fetch)
    snapshot = MarketContextService(news=marketaux.MarketauxNewsProvider("test-token")).fetch(request, live_news=True)
    assert snapshot.news.status == "partial"
    assert [item.record_id for item in snapshot.news.items] == ["match"]


def test_provider_error_does_not_fail_snapshot(monkeypatch):
    monkeypatch.setattr(hypeless, "fetch_object", lambda *args, **kwargs: {"stories": None})
    snapshot = MarketContextService(news=hypeless.HypelessNewsProvider()).fetch(request_for(), live_news=True)
    assert snapshot.news.status == "unavailable"
    assert snapshot.catalysts.status == "not_configured"

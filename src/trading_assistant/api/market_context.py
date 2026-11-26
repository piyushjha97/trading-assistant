from datetime import datetime, timedelta, timezone

from fastapi import APIRouter, HTTPException, Query, Request, Response

from trading_assistant.analytics.technical_evidence import TechnicalInterval
from trading_assistant.market_context import ContextSnapshot, EventRequest, MarketContextService, SourceResult
from trading_assistant.market_context.kite import KiteMarketContextProvider
from trading_assistant.market_context.window import SECTOR_BY_LISTING, comparison_window
from trading_assistant.market_data.kite_provider import KiteProviderError
from trading_assistant.market_data.models import CandleInterval, Exchange

router = APIRouter()

@router.get("/api/v1/market-context", response_model=ContextSnapshot)
def market_context(
    request: Request,
    response: Response,
    exchange: Exchange,
    symbol: str = Query(min_length=1, max_length=32, pattern=r"^[A-Za-z0-9&_-]+$"),
    interval: TechnicalInterval = "15minute",
    include_news: bool = True,
) -> ContextSnapshot:
    cutoff = datetime.now(timezone.utc)
    candle_interval = CandleInterval(interval)
    symbol = symbol.upper()
    provider = request.app.state.kite_provider
    batch = provider.candles(
        exchange=exchange, symbol=symbol, interval=candle_interval,
        start=cutoff - timedelta(days=14), end=cutoff,
    )
    news = getattr(request.app.state, "news_provider", None) if include_news else None
    company_name = None
    if news is not None:
        try:
            company_name = _company_name(request, exchange, symbol)
        except KiteProviderError:
            pass
    try:
        context_request = comparison_window(batch, cutoff, company_name=company_name)
    except ValueError:
        raise HTTPException(status_code=502, detail="Kite returned invalid timestamps for market context.") from None
    if context_request is None:
        raise HTTPException(status_code=422, detail="Market context needs two completed stock bars in the comparison window.")
    market = KiteMarketContextProvider(provider, SECTOR_BY_LISTING, stock_batch=batch)
    response.headers["Cache-Control"] = "no-store"
    return MarketContextService(market=market, news=news).fetch(context_request, live_news=True)



@router.get("/api/v1/company-news", response_model=SourceResult)
def company_news(
    request: Request,
    response: Response,
    exchange: Exchange,
    symbol: str = Query(min_length=1, max_length=32, pattern=r"^[A-Za-z0-9&_-]+$"),
) -> SourceResult:
    response.headers["Cache-Control"] = "no-store"
    news = getattr(request.app.state, "news_provider", None)
    if news is None:
        return SourceResult(status="not_configured")
    symbol = symbol.upper()
    company_name = _company_name(request, exchange, symbol)
    cutoff = datetime.now(timezone.utc)
    event_request = EventRequest(
        exchange=exchange, symbol=symbol, company_name=company_name,
        cutoff=cutoff, event_from=cutoff - timedelta(days=7),
    )
    return MarketContextService(news=news).fetch_news(event_request, live=True)


def _company_name(request: Request, exchange: Exchange, symbol: str) -> str | None:
    listings = request.app.state.kite_provider.search_instruments(symbol, exchange, limit=1)
    return listings[0].name if listings and listings[0].symbol == symbol else None

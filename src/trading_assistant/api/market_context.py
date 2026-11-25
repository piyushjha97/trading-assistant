from datetime import datetime, timedelta, timezone

from fastapi import APIRouter, HTTPException, Query, Request, Response

from trading_assistant.analytics.technical_evidence import TechnicalInterval
from trading_assistant.market_context import ContextRequest, ContextSnapshot, MarketContextService
from trading_assistant.market_context.kite import KiteMarketContextProvider
from trading_assistant.market_data.candle_eligibility import MARKET_TIMEZONE, select_completed_candles
from trading_assistant.market_data.kite_provider import KiteProviderError
from trading_assistant.market_data.models import CandleInterval, Exchange

router = APIRouter()

_SECTORS = {
    (exchange, symbol): "NIFTY IT"
    for exchange in Exchange
    for symbol in ("INFY", "TCS", "WIPRO", "HCLTECH", "TECHM", "LTIM")
}


@router.get("/api/v1/market-context", response_model=ContextSnapshot)
def market_context(
    request: Request,
    response: Response,
    exchange: Exchange,
    symbol: str = Query(min_length=1, max_length=32, pattern=r"^[A-Za-z0-9&_-]+$"),
    interval: TechnicalInterval = "15minute",
) -> ContextSnapshot:
    cutoff = datetime.now(timezone.utc)
    candle_interval = CandleInterval(interval)
    symbol = symbol.upper()
    provider = request.app.state.kite_provider
    batch = provider.candles(
        exchange=exchange, symbol=symbol, interval=candle_interval,
        start=cutoff - timedelta(days=14), end=cutoff,
    )
    try:
        stamps = sorted({bar.timestamp for bar in select_completed_candles(batch.candles, candle_interval, cutoff)})
    except ValueError:
        raise HTTPException(status_code=502, detail="Kite returned invalid timestamps for market context.") from None

    if stamps and candle_interval != CandleInterval.DAY:
        latest_session = stamps[-1].astimezone(MARKET_TIMEZONE).date()
        stamps = [stamp for stamp in stamps if stamp.astimezone(MARKET_TIMEZONE).date() == latest_session]
    if len(stamps) < 2:
        raise HTTPException(status_code=422, detail="Market context needs two completed stock bars in the comparison window.")

    first = stamps[-2] if candle_interval == CandleInterval.DAY else stamps[0]
    news = getattr(request.app.state, "news_provider", None)
    company_name = None
    if news is not None:
        try:
            listings = provider.search_instruments(symbol, exchange, limit=1)
            if listings and listings[0].symbol == symbol:
                company_name = listings[0].name
        except KiteProviderError:
            pass
    context_request = ContextRequest(
        exchange=exchange, symbol=symbol, interval=candle_interval, company_name=company_name,
        start_bar=first, end_bar=stamps[-1], cutoff=cutoff, event_from=cutoff - timedelta(days=7),
    )
    market = KiteMarketContextProvider(provider, _SECTORS, stock_batch=batch)
    response.headers["Cache-Control"] = "no-store"
    return MarketContextService(market=market, news=news).fetch(context_request, live_news=True)

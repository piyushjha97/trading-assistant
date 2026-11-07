from datetime import datetime, timedelta, timezone

from fastapi import APIRouter, HTTPException, Query, Request
from trading_assistant.market_data.kite_provider import (
    KiteMarketDataProvider,
    KiteProviderError,
)
from trading_assistant.market_data.models import (
    CandleInterval,
    CandleResponse,
    Exchange,
    QuoteResponse,
)

router = APIRouter()


def _provider(request: Request) -> KiteMarketDataProvider:
    return request.app.state.kite_provider


def _as_http_error(error: KiteProviderError) -> HTTPException:
    return HTTPException(
        status_code=error.status_code,
        detail={"code": error.code, "message": error.message},
    )


@router.get("/api/v1/health")
def health() -> dict[str, str]:
    return {"status": "ok"}


@router.get("/api/v1/market-data/capabilities")
def market_data_capabilities(request: Request) -> dict[str, object]:
    return {
        "provider": "kite",
        "access_token_configured": _provider(request).authenticated,
        "market_data_storage": False,
        "note": "Kite plan entitlement is verified when a market-data endpoint is called.",
    }


@router.get("/api/v1/market-data/quotes", response_model=QuoteResponse)
def quotes(
    request: Request,
    symbols: list[str] = Query(),
) -> QuoteResponse:
    if not symbols or len(symbols) > 50:
        raise HTTPException(
            status_code=422,
            detail={"code": "invalid_symbol_count", "message": "Request between 1 and 50 symbols."},
        )
    normalized: list[str] = []
    for value in symbols:
        parts = value.upper().split(":", maxsplit=1)
        if len(parts) != 2 or parts[0] not in Exchange.__members__ or not parts[1]:
            raise HTTPException(
                status_code=422,
                detail={"code": "invalid_symbol", "message": "Use symbols like NSE:INFY or BSE:RELIANCE."},
            )
        if not parts[1] or any(character.isspace() for character in parts[1]):
            raise HTTPException(
                status_code=422,
                detail={"code": "invalid_symbol", "message": "Use symbols like NSE:INFY or BSE:RELIANCE."},
            )
        normalized.append(f"{parts[0]}:{parts[1]}")
    try:
        return _provider(request).quotes(normalized)
    except KiteProviderError as error:
        raise _as_http_error(error) from None


@router.get("/api/v1/market-data/candles", response_model=CandleResponse)
def candles(
    request: Request,
    exchange: Exchange,
    symbol: str = Query(min_length=1, max_length=32, pattern=r"^[A-Za-z0-9&_-]+$"),
    interval: CandleInterval = CandleInterval.DAY,
    from_: datetime = Query(alias="from"),
    to: datetime = Query(),
) -> CandleResponse:
    if from_.tzinfo is None:
        from_ = from_.replace(tzinfo=timezone(timedelta(hours=5, minutes=30)))
    if to.tzinfo is None:
        to = to.replace(tzinfo=timezone(timedelta(hours=5, minutes=30)))
    if from_ >= to:
        raise HTTPException(
            status_code=422,
            detail={"code": "invalid_time_range", "message": "The from time must be before the to time."},
        )
    try:
        return _provider(request).candles(
            exchange=exchange,
            symbol=symbol.upper(),
            interval=interval,
            start=from_,
            end=to,
        )
    except KiteProviderError as error:
        raise _as_http_error(error) from None

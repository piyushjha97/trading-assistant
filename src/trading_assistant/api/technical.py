from datetime import datetime, timezone

from fastapi import APIRouter, HTTPException, Query, Request, Response

from trading_assistant.analytics.technical_evidence import (
    TechnicalEvidence,
    TechnicalInterval,
    build_technical_evidence,
    technical_window_start,
)
from trading_assistant.market_data.models import CandleInterval, Exchange

router = APIRouter()


@router.get("/api/v1/technical-evidence", response_model=TechnicalEvidence)
def technical_evidence(
    request: Request,
    response: Response,
    exchange: Exchange,
    symbol: str = Query(min_length=1, max_length=32, pattern=r"^[A-Za-z0-9&_-]+$"),
    interval: TechnicalInterval = "15minute",
) -> TechnicalEvidence:
    as_of = datetime.now(timezone.utc)
    candle_interval = CandleInterval(interval)
    provider = request.app.state.kite_provider
    batch = provider.candles(
        exchange=exchange,
        symbol=symbol.upper(),
        interval=candle_interval,
        start=technical_window_start(candle_interval, as_of),
        end=as_of,
    )
    try:
        evidence = build_technical_evidence(batch, as_of)
    except ValueError:
        raise HTTPException(status_code=502, detail={
            "code": "invalid_technical_candles",
            "message": "The provider returned invalid candles for technical evidence.",
        }) from None
    response.headers["Cache-Control"] = "no-store"
    return evidence

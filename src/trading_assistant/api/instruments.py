from typing import Annotated

from fastapi import APIRouter, Query, Request
from pydantic import StringConstraints

from trading_assistant.market_data.kite_provider import KiteMarketDataProvider
from trading_assistant.market_data.models import Exchange, InstrumentSearchResponse

router = APIRouter()
SearchTerm = Annotated[str, StringConstraints(strip_whitespace=True, min_length=2, max_length=80)]


@router.get("/api/v1/instruments", response_model=InstrumentSearchResponse)
def search_instruments(
    request: Request,
    q: SearchTerm,
    exchange: Exchange | None = None,
    limit: Annotated[int, Query(ge=1, le=30)] = 12,
) -> InstrumentSearchResponse:
    provider: KiteMarketDataProvider = request.app.state.kite_provider
    return InstrumentSearchResponse(instruments=provider.search_instruments(q, exchange, limit))

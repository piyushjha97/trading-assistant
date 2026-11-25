from contextlib import asynccontextmanager
from collections.abc import AsyncIterator
from threading import Lock

from fastapi import FastAPI, Request
from fastapi.responses import JSONResponse

from trading_assistant.api.instruments import router as instruments_router
from trading_assistant.api.market_context import router as market_context_router
from trading_assistant.api.routes import router
from trading_assistant.api.technical import router as technical_router
from trading_assistant.config import get_settings
from trading_assistant.market_context.news.hypeless import HypelessNewsProvider
from trading_assistant.market_context.news.marketaux import MarketauxNewsProvider
from trading_assistant.market_data.kite_provider import (
    KiteMarketDataProvider,
    KiteProviderError,
)
from trading_assistant.market_data.kite_session import restore_kite_session


@asynccontextmanager
async def lifespan(app: FastAPI) -> AsyncIterator[None]:
    settings = get_settings()
    app.state.kite_provider = KiteMarketDataProvider(restore_kite_session(settings))
    app.state.news_provider = None
    if settings.news_provider == "hypeless":
        app.state.news_provider = HypelessNewsProvider(settings.hypeless_api_key.get_secret_value())
    elif settings.news_provider == "marketaux" and settings.marketaux_api_token.get_secret_value():
        app.state.news_provider = MarketauxNewsProvider(settings.marketaux_api_token.get_secret_value())
    app.state.kite_session_lock = Lock()
    yield


app = FastAPI(
    title="Trading Assistant API",
    version="0.1.0",
    description="Local backend for real Kite market data. No market data is persisted.",
    lifespan=lifespan,
)
app.include_router(router)
app.include_router(instruments_router)
app.include_router(technical_router)
app.include_router(market_context_router)


@app.exception_handler(KiteProviderError)
async def provider_error_handler(_: Request, error: KiteProviderError) -> JSONResponse:
    return JSONResponse(
        status_code=error.status_code,
        content={"detail": {"code": error.code, "message": error.message}},
    )

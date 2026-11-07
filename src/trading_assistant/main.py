from contextlib import asynccontextmanager
from collections.abc import AsyncIterator

from fastapi import FastAPI, Request
from fastapi.responses import JSONResponse

from trading_assistant.api.routes import router
from trading_assistant.config import get_settings
from trading_assistant.market_data.kite_provider import (
    KiteMarketDataProvider,
    KiteProviderError,
)


@asynccontextmanager
async def lifespan(app: FastAPI) -> AsyncIterator[None]:
    app.state.kite_provider = KiteMarketDataProvider(get_settings())
    yield


app = FastAPI(
    title="Trading Assistant API",
    version="0.1.0",
    description="Local backend for real Kite market data. No market data is persisted.",
    lifespan=lifespan,
)
app.include_router(router)


@app.exception_handler(KiteProviderError)
async def provider_error_handler(_: Request, error: KiteProviderError) -> JSONResponse:
    return JSONResponse(
        status_code=error.status_code,
        content={"detail": {"code": error.code, "message": error.message}},
    )

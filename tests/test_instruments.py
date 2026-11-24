from datetime import datetime, timezone
from unittest.mock import Mock, call

from fastapi import FastAPI
from fastapi.testclient import TestClient

from trading_assistant.api.instruments import router
from trading_assistant.config import Settings
from trading_assistant.main import provider_error_handler
from trading_assistant.market_data.kite_provider import KiteMarketDataProvider, KiteProviderError
from trading_assistant.market_data.models import CandleInterval, Exchange


def test_search_ranks_listings_and_reuses_the_candle_instrument_catalog() -> None:
    provider = KiteMarketDataProvider(Settings(kite_api_key="test", kite_access_token="test"))
    kite = Mock()
    provider._client = kite
    kite.instruments.side_effect = [
        [
            {"tradingsymbol": "INFY", "name": "Infosys", "instrument_token": 408065, "instrument_type": "EQ"},
            {"tradingsymbol": "INFYET", "name": "Infosys ETF", "instrument_token": 12, "instrument_type": "EQ"},
            {"tradingsymbol": "INFCOMP", "name": "Info Company", "instrument_token": 13, "instrument_type": "EQ"},
            {"tradingsymbol": "INFYINDEX", "name": "Infosys index", "instrument_token": 14, "instrument_type": "INDEX"},
        ],
        [{"tradingsymbol": "INFY", "name": "Infosys", "instrument_token": 15, "instrument_type": "EQ"}],
    ]
    kite.historical_data.return_value = []

    results = provider.search_instruments("iNFY")
    assert [(item.symbol, item.exchange) for item in results] == [
        ("INFY", Exchange.NSE), ("INFY", Exchange.BSE), ("INFYET", Exchange.NSE),
    ]
    results = provider.search_instruments("Infosys", Exchange.NSE, limit=1)
    assert [(item.symbol, item.name) for item in results] == [("INFY", "Infosys")]

    start = datetime(2026, 1, 2, tzinfo=timezone.utc)
    end = datetime(2026, 1, 3, tzinfo=timezone.utc)
    provider.candles(Exchange.NSE, "INFY", CandleInterval.DAY, start, end)
    assert kite.historical_data.call_args.kwargs["instrument_token"] == 408065
    assert kite.instruments.call_args_list == [call("NSE"), call("BSE")]


def test_instruments_api_validates_terms_and_propagates_expired_session() -> None:
    app = FastAPI()
    app.include_router(router)
    app.add_exception_handler(KiteProviderError, provider_error_handler)
    app.state.kite_provider = KiteMarketDataProvider(
        Settings(kite_api_key="test", kite_access_token="")
    )
    client = TestClient(app)

    assert client.get("/api/v1/instruments", params={"q": "  a  "}).status_code == 422
    assert client.get("/api/v1/instruments", params={"q": "in", "limit": 31}).status_code == 422
    assert client.get("/api/v1/instruments", params={"q": "infosys"}).status_code == 401

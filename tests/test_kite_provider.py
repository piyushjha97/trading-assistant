from datetime import datetime, timezone
from decimal import Decimal
from types import SimpleNamespace
from unittest.mock import Mock

import pytest

from trading_assistant.market_data.kite_provider import (
    KiteMarketDataProvider,
    KiteProviderError,
)
from trading_assistant.market_data.models import CandleInterval, Exchange


@pytest.fixture
def provider() -> KiteMarketDataProvider:
    settings = SimpleNamespace(
        kite_api_key="test-key",
        kite_access_token=SimpleNamespace(get_secret_value=lambda: "test-access-token"),
        kite_timeout_seconds=1,
    )
    instance = KiteMarketDataProvider.__new__(KiteMarketDataProvider)
    instance._client = Mock()
    instance._authenticated = False
    instance._instrument_cache = {}
    return instance


def test_quotes_normalize_kite_payload(provider: KiteMarketDataProvider) -> None:
    provider._authenticated = True
    provider._client.quote.return_value = {
        "NSE:INFY": {
            "instrument_token": 408065,
            "last_price": 1500.25,
            "volume": 100,
            "timestamp": None,
            "last_trade_time": None,
            "ohlc": {"open": 1490, "high": 1510, "low": 1485, "close": 1488},
        }
    }

    result = provider.quotes(["NSE:INFY"])

    assert len(result.quotes) == 1
    assert result.quotes[0].last_price == Decimal("1500.25")
    assert result.quotes[0].previous_close == Decimal("1488")
    assert result.quotes[0].symbol == "INFY"


def test_quotes_require_access_token(provider: KiteMarketDataProvider) -> None:
    with pytest.raises(KiteProviderError) as error:
        provider.quotes(["NSE:INFY"])

    assert error.value.code == "kite_access_token_missing"
    assert error.value.status_code == 401


def test_historical_data_resolves_symbol_and_normalizes_candles(
    provider: KiteMarketDataProvider,
) -> None:
    provider._authenticated = True
    provider._client.instruments.return_value = [
        {"tradingsymbol": "INFY", "instrument_token": 408065}
    ]
    provider._client.historical_data.return_value = [
        {
            "date": datetime(2025, 1, 2, 9, 15, tzinfo=timezone.utc),
            "open": 1490.0,
            "high": 1510.0,
            "low": 1485.0,
            "close": 1500.0,
            "volume": 100,
        }
    ]

    result = provider.candles(
        Exchange.NSE,
        "INFY",
        CandleInterval.DAY,
        datetime(2025, 1, 2, tzinfo=timezone.utc),
        datetime(2025, 1, 3, tzinfo=timezone.utc),
    )

    provider._client.historical_data.assert_called_once()
    assert len(result.candles) == 1
    assert result.candles[0].close == Decimal("1500.0")
    assert result.candles[0].volume == 100


def test_unknown_symbol_returns_not_found(provider: KiteMarketDataProvider) -> None:
    provider._authenticated = True
    provider._client.instruments.return_value = []

    with pytest.raises(KiteProviderError) as error:
        provider.candles(
            Exchange.NSE,
            "NOTREAL",
            CandleInterval.DAY,
            datetime(2025, 1, 2, tzinfo=timezone.utc),
            datetime(2025, 1, 3, tzinfo=timezone.utc),
        )

    assert error.value.code == "instrument_not_found"
    assert error.value.status_code == 404

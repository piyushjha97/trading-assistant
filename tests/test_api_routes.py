from datetime import datetime, timezone
from decimal import Decimal

from fastapi import FastAPI
from fastapi.testclient import TestClient

from trading_assistant.api.routes import router
from trading_assistant.market_data.models import Exchange, Quote, QuoteResponse


class FakeKiteProvider:
    authenticated = True

    def quotes(self, symbols: list[str]) -> QuoteResponse:
        return QuoteResponse(
            quotes=[
                Quote(
                    exchange=Exchange.NSE,
                    symbol="INFY",
                    instrument_token=408065,
                    last_price=Decimal("1500.25"),
                    received_at=datetime(2026, 11, 7, tzinfo=timezone.utc),
                )
            ],
            missing_symbols=[symbol for symbol in symbols if symbol != "NSE:INFY"],
        )


def make_client() -> TestClient:
    app = FastAPI()
    app.state.kite_provider = FakeKiteProvider()
    app.include_router(router)
    return TestClient(app)


def test_quotes_endpoint_returns_typed_provider_data() -> None:
    with make_client() as client:
        response = client.get(
            "/api/v1/market-data/quotes",
            params=[("symbols", "NSE:INFY"), ("symbols", "NSE:RELIANCE")],
        )

    assert response.status_code == 200
    payload = response.json()
    assert payload["quotes"][0]["symbol"] == "INFY"
    assert payload["quotes"][0]["last_price"] == "1500.25"
    assert payload["missing_symbols"] == ["NSE:RELIANCE"]


def test_quotes_endpoint_rejects_invalid_symbol() -> None:
    with make_client() as client:
        response = client.get(
            "/api/v1/market-data/quotes",
            params={"symbols": "INFY"},
        )

    assert response.status_code == 422

from datetime import datetime, timezone
from decimal import Decimal

from trading_assistant.market_data.models import Exchange, Quote


def test_quote_uses_decimal_values_and_canonical_fields() -> None:
    quote = Quote(
        exchange=Exchange.NSE,
        symbol="INFY",
        instrument_token=408065,
        last_price=Decimal("1500.25"),
        received_at=datetime(2026, 11, 7, tzinfo=timezone.utc),
    )

    assert quote.last_price == Decimal("1500.25")
    assert quote.previous_close is None
    assert quote.exchange == Exchange.NSE

from datetime import datetime, timedelta

from trading_assistant.market_context import ContextRequest
from trading_assistant.market_data.candle_eligibility import MARKET_TIMEZONE, select_completed_candles
from trading_assistant.market_data.models import CandleInterval, CandleResponse, Exchange

# The instrument master supplies listing identity. Sector mappings are explicit.
SECTOR_BY_LISTING = {
    (exchange, symbol): "NIFTY IT"
    for exchange in Exchange
    for symbol in ("INFY", "TCS", "WIPRO", "HCLTECH", "TECHM", "LTIM")
}


def comparison_window(
    batch: CandleResponse, cutoff: datetime, *, company_name: str | None = None,
) -> ContextRequest | None:
    stamps = sorted({bar.timestamp for bar in select_completed_candles(batch.candles, batch.interval, cutoff)})
    if stamps and batch.interval != CandleInterval.DAY:
        latest_session = stamps[-1].astimezone(MARKET_TIMEZONE).date()
        stamps = [stamp for stamp in stamps if stamp.astimezone(MARKET_TIMEZONE).date() == latest_session]
    if len(stamps) < 2:
        return None

    return ContextRequest(
        exchange=batch.exchange, symbol=batch.symbol, interval=batch.interval, company_name=company_name,
        start_bar=stamps[-2] if batch.interval == CandleInterval.DAY else stamps[0],
        end_bar=stamps[-1], cutoff=cutoff, event_from=cutoff - timedelta(days=7),
    )

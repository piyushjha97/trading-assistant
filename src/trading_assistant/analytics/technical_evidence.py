from dataclasses import dataclass
from datetime import datetime, time, timedelta
from typing import Literal

from trading_assistant.analytics.indicators import IndicatorSnapshot, analyze_closed_candles
from trading_assistant.market_data.candle_eligibility import MARKET_TIMEZONE, select_completed_candles
from trading_assistant.market_data.models import CandleInterval, CandleResponse, Exchange

TechnicalInterval = Literal["15minute", "60minute", "day"]

_LOOKBACK_DAYS = {
    CandleInterval.FIFTEEN_MINUTE: 14,
    CandleInterval.SIXTY_MINUTE: 45,
    CandleInterval.DAY: 95,
}


@dataclass(frozen=True, slots=True)
class TechnicalEvidence:
    provider: str
    exchange: Exchange
    symbol: str
    interval: CandleInterval
    as_of: datetime
    received_at: datetime
    requested_from: datetime
    status: Literal["ready", "insufficient_history"]
    snapshot: IndicatorSnapshot
    excluded_candle_count: int
    notes: list[str]


def technical_window_start(interval: CandleInterval, as_of: datetime) -> datetime:
    date = as_of.astimezone(MARKET_TIMEZONE).date() - timedelta(days=_LOOKBACK_DAYS[interval])
    return datetime.combine(date, time.min, MARKET_TIMEZONE)


def build_technical_evidence(batch: CandleResponse, as_of: datetime) -> TechnicalEvidence:
    """Calculate technical evidence from the eligible candles in a fetched window."""
    closed = select_completed_candles(batch.candles, batch.interval, as_of)
    snapshot = analyze_closed_candles(closed)
    # ADX requires twice its period, the longest minimum history in this snapshot.
    enough_history = snapshot.candle_count >= 2 * snapshot.adx_period
    if batch.interval is CandleInterval.DAY:
        notes = ["Daily evidence uses prior IST dates only. Same-day final publication is unverified."]
    else:
        notes = [
            "Intraday evidence uses full-length bars on the 09:15 IST grid with a two-minute buffer. "
            "15:30 IST is an upper bound. Special sessions, auctions and provider freshness are unverified."
        ]
    if snapshot.candle_count > snapshot.relative_volume_period and snapshot.relative_volume is None:
        notes.append("Relative volume is unavailable because the prior volume baseline is zero.")
    return TechnicalEvidence(
        provider=batch.provider,
        exchange=batch.exchange,
        symbol=batch.symbol,
        interval=batch.interval,
        as_of=as_of,
        received_at=batch.received_at,
        requested_from=batch.requested_from,
        status="ready" if enough_history else "insufficient_history",
        snapshot=snapshot,
        excluded_candle_count=len(batch.candles) - len(closed),
        notes=notes,
    )

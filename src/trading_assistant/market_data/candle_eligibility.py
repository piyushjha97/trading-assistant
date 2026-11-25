from collections.abc import Sequence
from datetime import datetime, time, timedelta
from zoneinfo import ZoneInfo

from trading_assistant.market_data.models import Candle, CandleInterval

MARKET_TIMEZONE = ZoneInfo("Asia/Kolkata")
_REGULAR_OPEN = time(9, 15)
_SESSION_UPPER_BOUND = time(15, 30)
# Kite historical candles have a start timestamp and no finalized-bar flag.
_PUBLICATION_BUFFER = timedelta(minutes=2)
_INTRADAY_DURATION = {
    CandleInterval.FIFTEEN_MINUTE: timedelta(minutes=15),
    CandleInterval.SIXTY_MINUTE: timedelta(hours=1),
}


def _eligible(candle: Candle, interval: CandleInterval, local_cutoff: datetime) -> bool:
    if candle.timestamp.utcoffset() is None:
        raise ValueError("Candle timestamps must include a timezone.")
    start = candle.timestamp.astimezone(MARKET_TIMEZONE)
    if interval is CandleInterval.DAY:
        # The stable daily price can differ from the last live close until publication.
        return start.date() < local_cutoff.date()

    session_open = datetime.combine(start.date(), _REGULAR_OPEN, MARKET_TIMEZONE)
    session_close = datetime.combine(start.date(), _SESSION_UPPER_BOUND, MARKET_TIMEZONE)
    duration = _INTRADAY_DURATION[interval]
    end = start + duration
    return (
        session_open <= start
        and (start - session_open) % duration == timedelta(0)
        and end <= session_close
        and end + _PUBLICATION_BUFFER <= local_cutoff
    )


def select_completed_candles(
    candles: Sequence[Candle], interval: CandleInterval, as_of: datetime
) -> list[Candle]:
    """Apply the regular-session cutoff to received candles without filling gaps."""
    if as_of.utcoffset() is None:
        raise ValueError("The analysis cutoff must include a timezone.")
    local_cutoff = as_of.astimezone(MARKET_TIMEZONE)
    return [bar for bar in candles if _eligible(bar, interval, local_cutoff)]

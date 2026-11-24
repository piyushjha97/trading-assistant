from collections.abc import Sequence
from dataclasses import dataclass
from datetime import datetime
from decimal import Context, Decimal, localcontext

from trading_assistant.market_data.models import Candle


@dataclass(frozen=True, slots=True)
class IndicatorSnapshot:
    candle_count: int
    last_candle_at: datetime | None
    open: Decimal | None
    high: Decimal | None
    low: Decimal | None
    close: Decimal | None
    volume: int | None
    sma: Decimal | None
    ema: Decimal | None
    rsi: Decimal | None
    atr: Decimal | None
    moving_average_period: int
    rsi_period: int
    atr_period: int
    calculation_version: str = "2"
    first_candle_at: datetime | None = None
    adx: Decimal | None = None
    relative_volume: Decimal | None = None
    prior_range_high: Decimal | None = None
    prior_range_low: Decimal | None = None
    adx_period: int = 14
    relative_volume_period: int = 20
    prior_range_period: int = 20


def _mean(values: Sequence[Decimal]) -> Decimal:
    return sum(values, Decimal(0)) / len(values)


def _smoothed_average(
    values: Sequence[Decimal], period: int, weight: Decimal
) -> Decimal | None:
    if len(values) < period:
        return None
    average = _mean(values[:period])
    for value in values[period:]:
        average += weight * (value - average)
    return average


def _adx(candles: Sequence[Candle], period: int) -> Decimal | None:
    if len(candles) < 2 * period:
        return None

    positive = Decimal(0)
    negative = Decimal(0)
    directional_indices: list[Decimal] = []
    for index, (previous, current) in enumerate(zip(candles, candles[1:]), start=1):
        up = current.high - previous.high
        down = previous.low - current.low
        if index > period:
            positive -= positive / period
            negative -= negative / period
        if up > max(down, 0):
            positive += up
        elif down > max(up, 0):
            negative += down
        if index >= period:
            # The common true-range denominator cancels when computing DX.
            total = positive + negative
            directional_indices.append(
                100 * abs(positive - negative) / total if total else Decimal(0)
            )

    return _smoothed_average(directional_indices, period, Decimal(1) / period)


def analyze_closed_candles(
    candles: Sequence[Candle],
    *,
    moving_average_period: int = 20,
    rsi_period: int = 14,
    atr_period: int = 14,
    adx_period: int = 14,
    relative_volume_period: int = 20,
    prior_range_period: int = 20,
) -> IndicatorSnapshot:
    """Analyze one listing and interval, using only ordered, eligible closed bars.

    The caller verifies session coverage, adjustments and availability at its
    analysis cutoff before passing candles here. The input may include earlier
    bars for warm-up. An empty series or insufficient history yields None for
    unavailable values. OHLCV describes the most recent supplied bar.

    SMA uses the last N closes. EMA seeds with the first N closes' SMA and
    uses weight 2/(N+1). RSI and ATR seed with the mean of N changes and N
    true ranges respectively and use Wilder smoothing (weight 1/N). Both
    need N+1 candles because the first supplies the previous close. Flat RSI
    is 50, rising-only RSI is 100, and falling-only RSI is 0.

    ADX uses Wilder smoothing of directional movement and DX. It needs
    2N candles and returns 0 for flat prices. Relative volume divides the
    latest volume by the mean of the preceding N bars and is unavailable
    when that mean is zero. This baseline does not account for time of day.
    The prior range is the highest high and lowest low over the preceding N
    bars. Both comparisons exclude the latest bar and require N+1 candles.
    """
    for period in (
        moving_average_period, rsi_period, atr_period,
        adx_period, relative_volume_period, prior_range_period,
    ):
        if type(period) is not int or period < 1:
            raise ValueError("Indicator periods must be positive integers.")

    closes: list[Decimal] = []
    gains: list[Decimal] = []
    losses: list[Decimal] = []
    true_ranges: list[Decimal] = []
    previous: Candle | None = None
    zero = Decimal(0)
    with localcontext(Context(prec=34)):
        for candle in candles:
            if candle.timestamp.utcoffset() is None:
                raise ValueError("Candle timestamps must include a timezone.")
            if candle.volume < 0 or candle.low <= 0:
                raise ValueError("Candles require positive prices and non-negative volume.")
            if previous is not None:
                if candle.timestamp <= previous.timestamp:
                    raise ValueError("Candle timestamps must be strictly increasing.")
                change = candle.close - previous.close
                gains.append(max(change, zero))
                losses.append(max(-change, zero))
                true_ranges.append(
                    max(candle.high, previous.close) - min(candle.low, previous.close)
                )
            closes.append(candle.close)
            previous = candle

        sma = _mean(closes[-moving_average_period:]) if len(closes) >= moving_average_period else None
        ema = _smoothed_average(
            closes, moving_average_period, Decimal(2) / (moving_average_period + 1)
        )
        rsi_weight = Decimal(1) / rsi_period
        average_gain = _smoothed_average(gains, rsi_period, rsi_weight)
        average_loss = _smoothed_average(losses, rsi_period, rsi_weight)
        rsi = None
        if average_gain is not None and average_loss is not None:
            total = average_gain + average_loss
            rsi = 100 * average_gain / total if total else Decimal(50)
        atr = _smoothed_average(true_ranges, atr_period, Decimal(1) / atr_period)
        adx = _adx(candles, adx_period)

        relative_volume = None
        if previous is not None and len(candles) > relative_volume_period:
            baseline_volume = sum(bar.volume for bar in candles[-relative_volume_period - 1:-1])
            if baseline_volume:
                relative_volume = Decimal(previous.volume * relative_volume_period) / baseline_volume

    prior_range = candles[-prior_range_period - 1:-1] if len(candles) > prior_range_period else ()

    return IndicatorSnapshot(
        candle_count=len(closes),
        last_candle_at=previous.timestamp if previous else None,
        open=previous.open if previous else None,
        high=previous.high if previous else None,
        low=previous.low if previous else None,
        close=previous.close if previous else None,
        volume=previous.volume if previous else None,
        sma=sma,
        ema=ema,
        rsi=rsi,
        atr=atr,
        moving_average_period=moving_average_period,
        rsi_period=rsi_period,
        atr_period=atr_period,
        first_candle_at=candles[0].timestamp if closes else None,
        adx=adx,
        relative_volume=relative_volume,
        prior_range_high=max((bar.high for bar in prior_range), default=None),
        prior_range_low=min((bar.low for bar in prior_range), default=None),
        adx_period=adx_period,
        relative_volume_period=relative_volume_period,
        prior_range_period=prior_range_period,
    )

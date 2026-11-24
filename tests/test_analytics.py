from datetime import datetime, timedelta, timezone
from decimal import Decimal

import pytest

from trading_assistant.analytics import analyze_closed_candles
from trading_assistant.market_data.models import Candle


def make_bars(closes: list[int], volumes: list[int] | None = None) -> list[Candle]:
    start = datetime(2026, 1, 5, tzinfo=timezone.utc)
    return [
        Candle(
            timestamp=start + timedelta(minutes=15 * index),
            open=close, high=close + 1, low=close - 1, close=close,
            volume=volumes[index] if volumes is not None else 100,
        )
        for index, close in enumerate(closes)
    ]


def test_price_indicators_use_wilder_smoothing_and_previous_close() -> None:
    result = analyze_closed_candles(
        make_bars([10, 12, 11, 13, 12]),
        moving_average_period=2, rsi_period=2, atr_period=2, adx_period=2,
    )

    assert result.sma == Decimal('12.5')
    assert result.ema == pytest.approx(Decimal('12.111111111111'))
    assert result.rsi == pytest.approx(Decimal('54.545454545455'))
    assert result.atr == Decimal('2.375')
    assert result.adx == pytest.approx(Decimal('30.735930735931'))


def test_indicators_against_published_kite_bars() -> None:
    # Contiguous rows from https://kite.trade/docs/connect/v3/historical/#examples
    rows = [
        ('1703', '1704.45', '1702.35', '1703.65', 2212),
        ('1703.6', '1703.75', '1702.5', '1702.55', 799),
        ('1703.5', '1703.6', '1700.15', '1701.95', 3562),
        ('1699.8', '1701.3', '1698.15', '1701.3', 3433),
    ]
    bars = [
        Candle(
            timestamp=datetime.fromisoformat(f'2017-12-15T09:{minute}:00+05:30'),
            open=open_, high=high, low=low, close=close, volume=volume,
        )
        for minute, (open_, high, low, close, volume) in enumerate(rows, start=17)
    ]
    result = analyze_closed_candles(
        bars, moving_average_period=2, rsi_period=2, atr_period=2, adx_period=2,
        relative_volume_period=2, prior_range_period=2,
    )
    assert result.first_candle_at == bars[0].timestamp
    assert result.last_candle_at == bars[-1].timestamp
    assert result.sma == Decimal('1701.625')
    assert result.ema == pytest.approx(Decimal('1701.644444444444'))
    assert result.rsi == 0
    assert result.atr == Decimal('3.075')
    assert result.adx == 100
    assert result.relative_volume == pytest.approx(Decimal(6866) / 4361)
    assert result.prior_range_high == Decimal('1703.75')
    assert result.prior_range_low == Decimal('1700.15')


@pytest.mark.parametrize(('closes', 'expected'), [([10, 11, 12, 13], 100), ([13, 12, 11, 10], 100), ([10] * 4, 0)])
def test_adx_measures_strength_in_both_directions(closes: list[int], expected: int) -> None:
    bars = make_bars(closes)
    assert analyze_closed_candles(bars[:-1], adx_period=2).adx is None
    assert analyze_closed_candles(bars, adx_period=2).adx == expected


def test_relative_volume_and_breakout_range_exclude_latest_bar() -> None:
    bars = make_bars([50, 10, 12, 20], [999, 100, 300, 600])
    result = analyze_closed_candles(bars, relative_volume_period=2, prior_range_period=2)

    assert result.relative_volume == 3
    assert result.prior_range_high == 13
    assert result.prior_range_low == 9
    assert result.close == 20
    assert result.volume == 600


def test_missing_warmup_and_zero_volume_baseline() -> None:
    bars = make_bars([10, 10, 10], [0, 0, 500])
    result = analyze_closed_candles(bars, relative_volume_period=2, prior_range_period=3)
    assert result.relative_volume is None
    assert result.prior_range_high is None
    assert analyze_closed_candles(bars, relative_volume_period=3).relative_volume is None
    assert analyze_closed_candles(bars, rsi_period=2).rsi == 50
    assert analyze_closed_candles([]).close is None


def test_rejects_invalid_order_and_period() -> None:
    bar = make_bars([10])[0]
    with pytest.raises(ValueError, match='strictly increasing'):
        analyze_closed_candles([bar, bar])
    with pytest.raises(ValueError, match='positive integers'):
        analyze_closed_candles([bar], adx_period=0)

from datetime import datetime, time, timedelta
from decimal import Decimal, ROUND_CEILING, ROUND_FLOOR
from hashlib import sha256
from typing import Literal

from pydantic import AwareDatetime, BaseModel, ValidationError

from trading_assistant.analytics.indicators import IndicatorSnapshot
from trading_assistant.llm.signal import NoOpSignalModel, SignalAssessment, SignalInput, SignalModel
from trading_assistant.market_context import MarketContext
from trading_assistant.market_data.candle_eligibility import MARKET_TIMEZONE

POLICY_VERSION = "intraday-breakout-v1"
PAPER_COST_BPS = Decimal("15")
_BAR = timedelta(minutes=15)
_BUFFER = timedelta(minutes=2)


class SignalSetup(BaseModel):
    signal_id: str
    entry_trigger: Decimal
    entry_limit: Decimal
    target: Decimal
    stop: Decimal
    signal_at: AwareDatetime
    expires_at: AwareDatetime


class SignalVerdict(BaseModel):
    verdict: Literal["BUY", "SELL", "WAIT"]
    as_of: AwareDatetime
    policy_version: str = POLICY_VERSION
    reasons: tuple[str, ...]
    setup: SignalSetup | None = None
    model_status: Literal["not_called", "no_op", "approved", "abstained", "invalid"] = "not_called"


def evaluate_signal(
    listing: str,
    cutoff: datetime,
    indicators: IndicatorSnapshot,
    context: MarketContext,
    tick_size: Decimal | None,
    model: SignalModel,
    *,
    allow_short: bool,
) -> SignalVerdict:
    def wait(reason: str, model_status: Literal["not_called", "abstained", "invalid"] = "not_called") -> SignalVerdict:
        return SignalVerdict(verdict="WAIT", as_of=cutoff, reasons=(reason,), model_status=model_status)

    local = cutoff.astimezone(MARKET_TIMEZONE)
    session_start = datetime.combine(local.date(), time(9, 15), MARKET_TIMEZONE)
    session_end = datetime.combine(local.date(), time(15, 15), MARKET_TIMEZONE)
    if local.weekday() >= 5 or not session_start <= local < session_end:
        return wait("outside_session")

    bar = indicators.last_candle_at
    if bar is None or bar < session_start or not bar + _BAR + _BUFFER <= cutoff < bar + 2 * _BAR + _BUFFER:
        return wait("recent_completed_bar_required")
    expiry = min(bar + 4 * _BAR, session_end)
    if expiry < bar + 3 * _BAR or local >= expiry - _BAR:
        return wait("insufficient_time_to_track")

    close, high, low = indicators.close, indicators.high, indicators.low
    ema, atr, relative_volume = indicators.ema, indicators.atr, indicators.relative_volume
    prior_high, prior_low = indicators.prior_range_high, indicators.prior_range_low
    if any(value is None for value in (close, high, low, ema, atr, relative_volume, prior_high, prior_low)):
        return wait("insufficient_technical_history")
    assert close is not None and high is not None and low is not None and ema is not None and atr is not None
    assert relative_volume is not None and prior_high is not None and prior_low is not None
    if atr <= 0 or relative_volume < 1:
        return wait("weak_volume_or_volatility")

    if close > max(prior_high, ema):
        side, direction, extreme = "BUY", 1, high
    elif close < min(prior_low, ema) and allow_short:
        side, direction, extreme = "SELL", -1, low
    else:
        return wait("no_supported_breakout")

    metrics = {item.kind: item.value for item in context.metrics if item.end_bar == bar}
    benchmark = metrics.get("benchmark_return")
    if benchmark is None:
        return wait("aligned_benchmark_unavailable")
    sector = metrics.get("sector_return")
    if direction * benchmark <= 0 or (sector is not None and direction * sector < 0):
        return wait("market_or_sector_disagrees")
    if tick_size is None or not tick_size.is_finite() or tick_size <= 0:
        return wait("instrument_tick_size_unavailable")

    rounding = ROUND_CEILING if direction == 1 else ROUND_FLOOR
    trigger = ((extreme + direction * tick_size) / tick_size).to_integral_value(rounding=rounding) * tick_size
    atr_ticks = max(1, (atr / tick_size).to_integral_value(rounding=ROUND_CEILING))
    risk = atr_ticks * tick_size
    band = (atr_ticks // 4) * tick_size
    limit = trigger + direction * band
    stop = trigger - direction * risk
    target = limit + direction * (risk + band) * 2
    estimated_cost = limit * PAPER_COST_BPS / 10_000
    net_reward = abs(target - limit) - estimated_cost
    net_risk = abs(limit - stop) + estimated_cost
    if min(trigger, limit, stop, target) <= 0 or net_reward < Decimal("1.5") * net_risk:
        return wait("levels_or_estimated_cost_invalid")

    signal_id = sha256(f"{listing}|{bar.isoformat()}|{side}|{POLICY_VERSION}".encode()).hexdigest()[:32]
    evidence = {
        "close": close, "ema": ema, "atr": atr, "relative_volume": relative_volume,
        "prior_range_high": prior_high, "prior_range_low": prior_low, "benchmark_return": benchmark,
    }
    if sector is not None:
        evidence["sector_return"] = sector

    try:
        raw = model.assess(SignalInput(signal_id, side, evidence))
        assessment = SignalAssessment.model_validate(raw, from_attributes=False) if raw is not None else None
    except (ValidationError, TimeoutError):
        return wait("model_response_invalid", "invalid")
    if assessment is None and not isinstance(model, NoOpSignalModel):
        return wait("model_response_invalid", "invalid")
    if assessment is not None:
        if (
            assessment.candidate_id != signal_id or not assessment.evidence_ids
            or not set(assessment.evidence_ids) <= evidence.keys()
        ):
            return wait("model_evidence_invalid", "invalid")
        if assessment.decision == "ABSTAIN":
            return wait("model_abstained", "abstained")

    return SignalVerdict(
        verdict=side, as_of=cutoff, reasons=("breakout_confirmed", "benchmark_aligned"),
        setup=SignalSetup(
            signal_id=signal_id, entry_trigger=trigger, entry_limit=limit, target=target,
            stop=stop, signal_at=cutoff, expires_at=expiry,
        ),
        model_status="no_op" if assessment is None else "approved",
    )

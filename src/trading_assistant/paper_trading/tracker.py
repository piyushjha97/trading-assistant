from collections.abc import Iterable
from datetime import datetime, time, timedelta
from decimal import Decimal

from trading_assistant.market_data.candle_eligibility import (
    MARKET_TIMEZONE,
    select_completed_candles,
)
from trading_assistant.market_data.models import Candle, CandleInterval
from trading_assistant.paper_trading.models import ExitReason, PaperTrade, PaperTradePlan
from trading_assistant.paper_trading.store import PaperTradeStore

_INTRADAY_DURATION = {
    CandleInterval.FIFTEEN_MINUTE: timedelta(minutes=15),
    CandleInterval.SIXTY_MINUTE: timedelta(hours=1),
}
_TERMINAL_STATES = {"CLOSED", "EXPIRED", "UNRESOLVED"}


class PaperTradeTracker:
    """Track one-share paper trades from completed, chronological candle batches."""

    def __init__(self, store: PaperTradeStore) -> None:
        self._store = store

    def register(self, plan: PaperTradePlan) -> PaperTrade:
        return self._store.register(plan)

    def get(self, signal_id: str) -> PaperTrade:
        return self._store.get(signal_id)

    def list(self) -> list[PaperTrade]:
        return self._store.list()

    def advance(
        self, signal_id: str, candles: Iterable[Candle], *, as_of: datetime,
    ) -> PaperTrade:
        batch = list(candles)
        return self._store.update(signal_id, lambda trade: _replay(trade, batch, as_of))


def _replay(trade: PaperTrade, candles: list[Candle], as_of: datetime) -> PaperTrade:
    if as_of.utcoffset() is None:
        raise ValueError("Paper-trade cutoff must include a timezone.")
    if trade.status in _TERMINAL_STATES:
        return trade

    plan = trade.plan
    starts: dict[datetime, Candle] = {}
    since = trade.last_bar_at or plan.signal_at
    for bar in select_completed_candles(candles, plan.interval, as_of):
        if bar.timestamp <= since or _bar_end(plan, bar.timestamp) > plan.expires_at:
            continue
        if min(bar.open, bar.close, bar.low, bar.high) <= 0 or bar.volume < 0:
            raise ValueError("Paper-trade candles need positive OHLC values and nonnegative volume.")
        previous = starts.setdefault(bar.timestamp, bar)
        if previous != bar:
            raise ValueError("Conflicting candles share a paper-trade timestamp.")

    for bar in sorted(starts.values(), key=lambda candle: candle.timestamp):
        if _same_session_gap(plan, trade.last_bar_at, bar.timestamp):
            break
        trade = trade.model_copy(update={"last_bar_at": bar.timestamp})
        if bar.volume > 0:
            trade = _apply_bar(trade, bar)
        if trade.status == "CLOSED":
            return trade
        if _bar_end(plan, bar.timestamp) == _last_eligible_end(plan):
            if trade.status == "PENDING":
                return trade.model_copy(update={"status": "EXPIRED"})
            if bar.volume > 0:
                fill = min(bar.close, plan.target) if plan.side == "BUY" else max(bar.close, plan.target)
                return _close(trade, bar, fill, "TIME")
            return trade.model_copy(update={"status": "UNRESOLVED"})

    expiry_observable = (
        as_of.astimezone(MARKET_TIMEZONE).date() > plan.expires_at.astimezone(MARKET_TIMEZONE).date()
        if plan.interval == CandleInterval.DAY else as_of >= plan.expires_at + timedelta(minutes=2)
    )
    if expiry_observable:
        status = "EXPIRED" if _no_post_signal_bar(plan) else "UNRESOLVED"
        return trade.model_copy(update={"status": status})
    return trade


def _bar_end(plan: PaperTradePlan, start: datetime) -> datetime:
    if plan.interval == CandleInterval.DAY:
        return start.astimezone(MARKET_TIMEZONE).replace(hour=15, minute=30)
    return start + _INTRADAY_DURATION[plan.interval]


def _last_eligible_end(plan: PaperTradePlan) -> datetime:
    expiry = plan.expires_at.astimezone(MARKET_TIMEZONE)
    if plan.interval == CandleInterval.DAY:
        close = datetime.combine(expiry.date(), time(15, 30), MARKET_TIMEZONE)
        return close if close <= expiry else close - timedelta(days=1)
    duration = _INTRADAY_DURATION[plan.interval]
    opening = datetime.combine(expiry.date(), time(9, 15), MARKET_TIMEZONE)
    upper_bound = datetime.combine(expiry.date(), time(15, 30), MARKET_TIMEZONE)
    elapsed = min(expiry, upper_bound) - opening
    return opening + (elapsed // duration) * duration


def _no_post_signal_bar(plan: PaperTradePlan) -> bool:
    if plan.interval == CandleInterval.DAY:
        return False
    expiry = _last_eligible_end(plan)
    signal = plan.signal_at.astimezone(MARKET_TIMEZONE)
    return expiry.date() == signal.date() and expiry - _INTRADAY_DURATION[plan.interval] <= signal


def _same_session_gap(plan: PaperTradePlan, previous: datetime | None, current: datetime) -> bool:
    # Without an exchange calendar this can detect missing intraday bars within a session.
    if plan.interval == CandleInterval.DAY:
        return False
    current_local = current.astimezone(MARKET_TIMEZONE)
    duration = _INTRADAY_DURATION[plan.interval]
    opening = datetime.combine(current_local.date(), time(9, 15), MARKET_TIMEZONE)
    if previous is not None and previous.astimezone(MARKET_TIMEZONE).date() == current_local.date():
        expected = previous + duration
    elif plan.signal_at.astimezone(MARKET_TIMEZONE).date() == current_local.date() and plan.signal_at >= opening:
        expected = opening + (((plan.signal_at - opening) // duration) + 1) * duration
    else:
        expected = opening
    return current > expected


def _apply_bar(trade: PaperTrade, bar: Candle) -> PaperTrade:
    plan = trade.plan
    if trade.status == "OPEN":
        return _check_exit(trade, bar, entered_intrabar=False)

    if plan.side == "BUY":
        if bar.high < plan.entry_trigger or bar.open > plan.entry_limit:
            return trade
        fill = max(plan.entry_trigger, bar.open)
    else:
        if bar.low > plan.entry_trigger or bar.open < plan.entry_limit:
            return trade
        fill = min(plan.entry_trigger, bar.open)

    entered = trade.model_copy(update={
        "status": "OPEN", "entry_fill_price": fill, "entry_bar_at": bar.timestamp,
    })
    return _check_exit(entered, bar, entered_intrabar=fill != bar.open)


def _check_exit(trade: PaperTrade, bar: Candle, *, entered_intrabar: bool) -> PaperTrade:
    plan = trade.plan
    if plan.side == "BUY":
        if not entered_intrabar and bar.open >= plan.target:
            return _close(trade, bar, plan.target, "TARGET")
        if bar.low <= plan.stop:
            stop_fill = plan.stop if entered_intrabar else min(plan.stop, bar.open)
            return _close(trade, bar, stop_fill, "STOP")
        target_reached = bar.high >= plan.target
    else:
        if not entered_intrabar and bar.open <= plan.target:
            return _close(trade, bar, plan.target, "TARGET")
        if bar.high >= plan.stop:
            stop_fill = plan.stop if entered_intrabar else max(plan.stop, bar.open)
            return _close(trade, bar, stop_fill, "STOP")
        target_reached = bar.low <= plan.target

    # A bar containing an intrabar entry cannot establish subsequent favorable travel.
    if target_reached and not entered_intrabar:
        return _close(trade, bar, plan.target, "TARGET")
    return trade


def _close(trade: PaperTrade, bar: Candle, fill: Decimal, reason: ExitReason) -> PaperTrade:
    entry = trade.entry_fill_price
    if entry is None:
        raise ValueError("An open paper trade must have an entry fill.")
    gross = fill - entry if trade.plan.side == "BUY" else entry - fill
    net = gross - entry * trade.plan.round_trip_cost_bps / Decimal(10_000)
    outcome = "WIN" if net > 0 else "LOSS" if net < 0 else "FLAT"
    return trade.model_copy(update={
        "status": "CLOSED", "exit_fill_price": fill, "exit_bar_at": bar.timestamp,
        "exit_reason": reason, "gross_pnl_per_share": gross, "net_pnl_per_share": net,
        "outcome": outcome,
    })

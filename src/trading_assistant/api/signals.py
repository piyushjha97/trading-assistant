from datetime import datetime, timezone

from fastapi import APIRouter, HTTPException, Request, Response
from pydantic import BaseModel, Field

from trading_assistant.analytics.technical_evidence import build_technical_evidence, technical_window_start
from trading_assistant.evaluation.signals import PAPER_COST_BPS, SignalVerdict, evaluate_signal
from trading_assistant.market_context import MarketContext
from trading_assistant.market_context.kite import KiteMarketContextProvider
from trading_assistant.market_context.window import SECTOR_BY_LISTING, comparison_window
from trading_assistant.market_data.models import CandleInterval, Exchange
from trading_assistant.paper_trading import PaperTrade, PaperTradePlan

router = APIRouter()


class AnalysisRequest(BaseModel):
    exchange: Exchange
    symbol: str = Field(pattern=r"^[A-Z0-9&_-]{1,32}$")


@router.post("/api/v1/analyses", response_model=SignalVerdict)
def analyze(body: AnalysisRequest, request: Request, response: Response) -> SignalVerdict:
    cutoff = datetime.now(timezone.utc)
    exchange, symbol = body.exchange, body.symbol.upper()
    interval = CandleInterval.FIFTEEN_MINUTE
    provider = request.app.state.kite_provider
    model = request.app.state.signal_model
    response.headers["Cache-Control"] = "no-store"
    batch = provider.candles(
        exchange=exchange, symbol=symbol, interval=interval,
        start=technical_window_start(interval, cutoff), end=cutoff,
    )
    try:
        technical = build_technical_evidence(batch, cutoff)
        window = comparison_window(batch, cutoff)
    except ValueError:
        raise HTTPException(status_code=502, detail="Kite returned invalid signal candles.") from None

    context = MarketContext(status="unavailable")
    if window is not None:
        market = KiteMarketContextProvider(provider, SECTOR_BY_LISTING, stock_batch=batch)
        context = market.fetch(window)
    result = evaluate_signal(
        f"{exchange}:{symbol}", cutoff, technical.snapshot, context,
        provider.equity_tick_size(exchange, symbol), model, allow_short=True,
    )
    setup = result.setup
    if setup is None or result.verdict == "WAIT":
        return result

    tracker = request.app.state.paper_tracker
    plan = PaperTradePlan(
        signal_id=setup.signal_id, exchange=exchange, symbol=symbol, interval=interval,
        side=result.verdict, signal_at=setup.signal_at, expires_at=setup.expires_at,
        entry_trigger=setup.entry_trigger, entry_limit=setup.entry_limit, target=setup.target,
        stop=setup.stop, round_trip_cost_bps=PAPER_COST_BPS,
        policy_version=result.policy_version, evaluation_reasons=result.reasons,
    )
    try:
        trade = tracker.register(plan)
    except ValueError as error:
        # Concurrent or repeated evaluation of the same completed bar reuses its original plan.
        try:
            trade = tracker.get(plan.signal_id)
        except KeyError:
            raise error from None
    return result.model_copy(update={"setup": setup.model_copy(update={
        "signal_at": trade.plan.signal_at, "expires_at": trade.plan.expires_at,
        "entry_trigger": trade.plan.entry_trigger, "entry_limit": trade.plan.entry_limit,
        "target": trade.plan.target, "stop": trade.plan.stop,
    })})


@router.get("/api/v1/paper-trades", response_model=list[PaperTrade])
def paper_trades(request: Request, response: Response) -> list[PaperTrade]:
    response.headers["Cache-Control"] = "no-store"
    return list(request.app.state.paper_tracker.list())


@router.post("/api/v1/paper-trades/{signal_id}/refresh", response_model=PaperTrade)
def refresh_paper_trade(signal_id: str, request: Request, response: Response) -> PaperTrade:
    response.headers["Cache-Control"] = "no-store"
    tracker = request.app.state.paper_tracker
    try:
        trade = tracker.get(signal_id)
    except KeyError:
        raise HTTPException(status_code=404, detail="Paper trade not found.") from None
    if trade.status not in {"PENDING", "OPEN"}:
        return trade

    plan = trade.plan
    provider = request.app.state.kite_provider
    cutoff = datetime.now(timezone.utc)
    start = trade.last_bar_at or plan.signal_at
    if cutoff <= start:
        return trade
    batch = provider.candles(
        exchange=plan.exchange, symbol=plan.symbol, interval=plan.interval,
        start=start, end=min(cutoff, plan.expires_at),
    )
    return tracker.advance(signal_id, batch.candles, as_of=cutoff)

from decimal import Decimal
from typing import Literal

from pydantic import AwareDatetime, BaseModel, ConfigDict, Field, model_validator

from trading_assistant.market_data.models import CandleInterval, Exchange

PaperInterval = Literal[CandleInterval.FIFTEEN_MINUTE, CandleInterval.SIXTY_MINUTE, CandleInterval.DAY]
PaperStatus = Literal["PENDING", "OPEN", "CLOSED", "EXPIRED", "UNRESOLVED"]
ExitReason = Literal["TARGET", "STOP", "TIME"]
Outcome = Literal["WIN", "LOSS", "FLAT"]


class PaperTradePlan(BaseModel):
    model_config = ConfigDict(frozen=True, extra="forbid", allow_inf_nan=False)

    signal_id: str = Field(min_length=1, max_length=128)
    exchange: Exchange
    symbol: str = Field(pattern=r"^[A-Z0-9&_-]{1,32}$")
    interval: PaperInterval
    side: Literal["BUY", "SELL"]
    signal_at: AwareDatetime
    expires_at: AwareDatetime
    entry_trigger: Decimal = Field(gt=0)
    entry_limit: Decimal = Field(gt=0)
    target: Decimal = Field(gt=0)
    stop: Decimal = Field(gt=0)
    policy_version: str | None = None
    evaluation_reasons: tuple[str, ...] = ()
    round_trip_cost_bps: Decimal = Field(default=Decimal(0), ge=0, lt=10_000)

    @model_validator(mode="after")
    def check_plan(self) -> "PaperTradePlan":
        if self.expires_at <= self.signal_at:
            raise ValueError("A paper plan must expire after its signal.")
        if self.side == "BUY":
            ordered = self.stop < self.entry_trigger <= self.entry_limit < self.target
        else:
            ordered = self.target < self.entry_limit <= self.entry_trigger < self.stop
        if not ordered:
            raise ValueError("Paper plan prices must be ordered for the selected side.")
        return self


class PaperTrade(BaseModel):
    model_config = ConfigDict(frozen=True, extra="forbid")

    plan: PaperTradePlan
    status: PaperStatus = "PENDING"
    last_bar_at: AwareDatetime | None = None
    entry_fill_price: Decimal | None = None
    entry_bar_at: AwareDatetime | None = None
    exit_fill_price: Decimal | None = None
    exit_bar_at: AwareDatetime | None = None
    exit_reason: ExitReason | None = None
    gross_pnl_per_share: Decimal | None = None
    net_pnl_per_share: Decimal | None = None
    outcome: Outcome | None = None

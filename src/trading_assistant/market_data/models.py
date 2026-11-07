from datetime import datetime
from decimal import Decimal
from enum import StrEnum

from pydantic import BaseModel, ConfigDict, Field, model_validator


class Exchange(StrEnum):
    NSE = "NSE"
    BSE = "BSE"


class CandleInterval(StrEnum):
    MINUTE = "minute"
    THREE_MINUTE = "3minute"
    FIVE_MINUTE = "5minute"
    TEN_MINUTE = "10minute"
    FIFTEEN_MINUTE = "15minute"
    THIRTY_MINUTE = "30minute"
    SIXTY_MINUTE = "60minute"
    DAY = "day"


class Quote(BaseModel):
    model_config = ConfigDict(extra="forbid")

    exchange: Exchange
    symbol: str
    instrument_token: int
    last_price: Decimal
    last_trade_time: datetime | None = None
    provider_timestamp: datetime | None = None
    received_at: datetime
    volume: int | None = None
    open: Decimal | None = None
    high: Decimal | None = None
    low: Decimal | None = None
    previous_close: Decimal | None = None


class QuoteResponse(BaseModel):
    provider: str = "kite"
    quotes: list[Quote]
    missing_symbols: list[str] = Field(default_factory=list)


class Candle(BaseModel):
    timestamp: datetime
    open: Decimal
    high: Decimal
    low: Decimal
    close: Decimal
    volume: int
    open_interest: int | None = None

    @model_validator(mode="after")
    def validate_ohlc(self) -> "Candle":
        if self.low > min(self.open, self.close) or self.high < max(self.open, self.close):
            raise ValueError("Candle OHLC values are inconsistent.")
        if self.low > self.high:
            raise ValueError("Candle low cannot exceed its high.")
        return self


class CandleResponse(BaseModel):
    provider: str = "kite"
    exchange: Exchange
    symbol: str
    interval: CandleInterval
    requested_from: datetime
    requested_to: datetime
    received_at: datetime
    candles: list[Candle] = Field(default_factory=list)

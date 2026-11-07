from datetime import datetime, timezone
from decimal import Decimal
from typing import Any
from zoneinfo import ZoneInfo

from kiteconnect import KiteConnect

from trading_assistant.config import Settings
from trading_assistant.market_data.models import (
    Candle,
    CandleInterval,
    CandleResponse,
    Exchange,
    Quote,
    QuoteResponse,
)


class KiteProviderError(Exception):
    def __init__(self, code: str, message: str, status_code: int) -> None:
        super().__init__(message)
        self.code = code
        self.message = message
        self.status_code = status_code


def _decimal(value: Any) -> Decimal | None:
    if value is None:
        return None
    return Decimal(str(value))


def _provider_error(error: Exception) -> KiteProviderError:
    kind = type(error).__name__
    known = {
        "TokenException": ("kite_session_expired", "Kite session is invalid or expired.", 401),
        "PermissionException": ("kite_permission_denied", "Kite denied this data request. Check the API plan and data entitlement.", 403),
        "InputException": ("kite_invalid_request", "Kite rejected the market-data request parameters.", 400),
        "NetworkException": ("kite_unavailable", "Could not connect to Kite. Try again shortly.", 503),
        "DataException": ("kite_invalid_response", "Kite returned an invalid market-data response.", 502),
        "RateLimitException": ("kite_rate_limited", "Kite rate-limited this request. Try again later.", 429),
    }
    code, message, status = known.get(
        kind,
        ("kite_request_failed", "Kite market-data request failed.", 502),
    )
    return KiteProviderError(code, message, status)


class KiteMarketDataProvider:
    """Synchronous Kite Connect adapter; no provider data is persisted."""

    def __init__(self, settings: Settings) -> None:
        self._client = KiteConnect(
            api_key=settings.kite_api_key,
            access_token=settings.kite_access_token.get_secret_value(),
            timeout=settings.kite_timeout_seconds,
        )
        self._authenticated = bool(settings.kite_access_token.get_secret_value())
        self._instrument_cache: dict[Exchange, tuple[str, dict[str, int]]] = {}

    @property
    def authenticated(self) -> bool:
        return self._authenticated

    def quotes(self, symbols: list[str]) -> QuoteResponse:
        client = self._authenticated_client()
        try:
            response = client.quote(symbols)
        except Exception as error:
            raise self._provider_error(error) from None

        received_at = datetime.now(timezone.utc)
        normalized: list[Quote] = []
        missing: list[str] = []
        for key in symbols:
            raw = response.get(key)
            if raw is None:
                missing.append(key)
                continue
            if raw.get("last_price") is None or raw.get("instrument_token") is None:
                raise KiteProviderError(
                    "kite_invalid_response",
                    "Kite returned an incomplete quote response.",
                    502,
                )
            exchange_text, symbol = key.split(":", maxsplit=1)
            ohlc = raw.get("ohlc") or {}
            normalized.append(
                Quote(
                    exchange=Exchange(exchange_text),
                    symbol=symbol,
                    instrument_token=int(raw["instrument_token"]),
                    last_price=_decimal(raw["last_price"]),
                    last_trade_time=raw.get("last_trade_time"),
                    provider_timestamp=raw.get("timestamp"),
                    received_at=received_at,
                    volume=raw.get("volume"),
                    open=_decimal(ohlc.get("open")),
                    high=_decimal(ohlc.get("high")),
                    low=_decimal(ohlc.get("low")),
                    previous_close=_decimal(ohlc.get("close")),
                )
            )
        return QuoteResponse(quotes=normalized, missing_symbols=missing)

    def candles(
        self,
        exchange: Exchange,
        symbol: str,
        interval: CandleInterval,
        start: datetime,
        end: datetime,
    ) -> CandleResponse:
        client = self._authenticated_client()
        instrument_token = self._instrument_token(client, exchange, symbol)
        india_tz = ZoneInfo("Asia/Kolkata")
        start_local = start.astimezone(india_tz) if start.tzinfo else start.replace(tzinfo=india_tz)
        end_local = end.astimezone(india_tz) if end.tzinfo else end.replace(tzinfo=india_tz)
        try:
            records = client.historical_data(
                instrument_token=instrument_token,
                from_date=start_local,
                to_date=end_local,
                interval=interval.value,
            )
        except Exception as error:
            raise self._provider_error(error) from None

        try:
            candles = [
                Candle(
                    timestamp=record["date"],
                    open=_decimal(record["open"]),
                    high=_decimal(record["high"]),
                    low=_decimal(record["low"]),
                    close=_decimal(record["close"]),
                    volume=int(record.get("volume", 0)),
                    open_interest=(
                        int(record["oi"]) if record.get("oi") is not None else None
                    ),
                )
                for record in records
            ]
        except (KeyError, TypeError, ValueError):
            raise KiteProviderError(
                "kite_invalid_response",
                "Kite returned candle data that did not match the expected OHLCV format.",
                502,
            ) from None
        candles.sort(key=lambda candle: candle.timestamp)
        if len({candle.timestamp for candle in candles}) != len(candles):
            raise KiteProviderError(
                "kite_invalid_response",
                "Kite returned duplicate candle timestamps.",
                502,
            )
        return CandleResponse(
            exchange=exchange,
            symbol=symbol,
            interval=interval,
            requested_from=start,
            requested_to=end,
            received_at=datetime.now(timezone.utc),
            candles=candles,
        )

    def _instrument_token(
        self,
        client: KiteConnect,
        exchange: Exchange,
        symbol: str,
    ) -> int:
        cache_day = datetime.now(ZoneInfo("Asia/Kolkata")).date().isoformat()
        cached = self._instrument_cache.get(exchange)
        if cached is None or cached[0] != cache_day:
            try:
                instruments = client.instruments(exchange.value)
            except Exception as error:
                raise self._provider_error(error) from None
            mapping = {
                item["tradingsymbol"]: int(item["instrument_token"])
                for item in instruments
                if item.get("tradingsymbol") and item.get("instrument_token")
            }
            self._instrument_cache[exchange] = (cache_day, mapping)
        else:
            mapping = cached[1]
        token = mapping.get(symbol)
        if token is None:
            raise KiteProviderError(
                "instrument_not_found",
                f"{exchange.value}:{symbol} was not found in Kite's instrument list.",
                404,
            )
        return token

    def _provider_error(self, error: Exception) -> KiteProviderError:
        if type(error).__name__ == "TokenException":
            self._authenticated = False
        return _provider_error(error)

    def _authenticated_client(self) -> KiteConnect:
        if not self.authenticated:
            raise KiteProviderError(
                "kite_access_token_missing",
                "Set KITE_ACCESS_TOKEN in .env before requesting market data.",
                401,
            )
        return self._client

import json
from datetime import datetime, time, timedelta
from pathlib import Path
from tempfile import NamedTemporaryFile
from urllib.parse import urlencode
from zoneinfo import ZoneInfo

from kiteconnect import KiteConnect, exceptions
from pydantic import SecretStr

from trading_assistant.config import Settings
from trading_assistant.market_data.kite_provider import KiteProviderError

_SESSION_PATH = Path(".secrets/kite-session.json")
_IST = ZoneInfo("Asia/Kolkata")


def _api_secret(settings: Settings) -> str:
    secret = settings.kite_api_secret.get_secret_value()
    if not secret:
        raise KiteProviderError("kite_login_unconfigured", "Set KITE_API_SECRET in .env and restart the backend to connect Kite.", 503)
    return secret


def kite_login_url(settings: Settings, state: str) -> str:
    _api_secret(settings)
    params = urlencode({
        "api_key": settings.kite_api_key,
        "v": "3",
        "redirect_params": urlencode({"state": state}),
    })
    return f"https://kite.zerodha.com/connect/login?{params}"


def restore_kite_session(settings: Settings) -> Settings:
    try:
        session = json.loads(_SESSION_PATH.read_text())
        expires_at = datetime.fromisoformat(session["expires_at"])
        token = session["access_token"]
        if session["api_key"] == settings.kite_api_key and expires_at > datetime.now(_IST) and isinstance(token, str) and token:
            return settings.model_copy(update={"kite_access_token": SecretStr(token)})
    except (OSError, ValueError, TypeError, KeyError):
        pass
    return settings


def connect_kite_session(settings: Settings, request_token: str) -> Settings:
    secret = _api_secret(settings)
    client = KiteConnect(api_key=settings.kite_api_key, timeout=settings.kite_timeout_seconds)
    try:
        token = client.generate_session(request_token, api_secret=secret)["access_token"]
    except (exceptions.TokenException, exceptions.InputException):
        raise KiteProviderError("kite_login_rejected", "Kite rejected the login. Start a new connection and try again.", 401) from None
    except Exception:
        raise KiteProviderError("kite_login_unavailable", "Kite login could not be completed. Try again shortly.", 502) from None

    if not isinstance(token, str) or not token:
        raise KiteProviderError("kite_login_unavailable", "Kite returned an incomplete session. Try connecting again.", 502)

    expires_at = datetime.combine(datetime.now(_IST).date() + timedelta(days=1), time(6), _IST)
    temp_path: Path | None = None
    try:
        _SESSION_PATH.parent.mkdir(mode=0o700, parents=True, exist_ok=True)
        with NamedTemporaryFile(mode="w", dir=_SESSION_PATH.parent, delete=False) as handle:
            temp_path = Path(handle.name)
            json.dump({"api_key": settings.kite_api_key, "access_token": token, "expires_at": expires_at.isoformat()}, handle)
        temp_path.replace(_SESSION_PATH)
    except OSError:
        raise KiteProviderError("kite_session_save_failed", "Could not save the local Kite session. Check that .secrets is writable.", 500) from None
    finally:
        if temp_path is not None:
            temp_path.unlink(missing_ok=True)
    return settings.model_copy(update={"kite_access_token": SecretStr(token)})

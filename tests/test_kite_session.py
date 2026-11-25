import json
import stat
from datetime import datetime, timedelta
from urllib.parse import parse_qs, urlsplit

from fastapi.testclient import TestClient
from kiteconnect.exceptions import TokenException

from trading_assistant.config import get_settings
from trading_assistant.main import app
from trading_assistant.market_data import kite_session


def test_backend_root_forwards_kite_callback_to_dashboard() -> None:
    response = TestClient(app, follow_redirects=False).get("/", params={
        "request_token": "one-time-token",
        "state": "a" * 64,
        "status": "success",
        "next": "https://example.com",
    })
    assert response.status_code == 303
    target = urlsplit(response.headers["location"])
    assert target.netloc == "127.0.0.1:3000"
    assert target.path == "/api/kite/callback"
    assert parse_qs(target.query) == {
        "request_token": ["one-time-token"], "state": ["a" * 64], "status": ["success"],
    }
    assert response.headers["cache-control"] == "no-store"
    assert response.headers["referrer-policy"] == "no-referrer"


def test_login_installs_and_persists_session(monkeypatch, tmp_path) -> None:
    path = tmp_path / ".secrets" / "kite-session.json"
    monkeypatch.setattr(kite_session, "_SESSION_PATH", path)
    monkeypatch.setenv("KITE_API_KEY", "test-key")
    monkeypatch.setenv("KITE_API_SECRET", "test-secret")
    monkeypatch.setenv("KITE_ACCESS_TOKEN", "")
    get_settings.cache_clear()

    def exchange(self, request_token, *, api_secret):
        assert (request_token, api_secret) == ("one-time-token", "test-secret")
        return {"access_token": "session-token"}

    monkeypatch.setattr(kite_session.KiteConnect, "generate_session", exchange)
    try:
        with TestClient(app) as client:
            assert client.get("/api/v1/market-data/quotes", params={"symbols": "NSE:INFY"}).status_code == 401
            state = "a" * 64
            login = client.get("/api/v1/kite/login-url", params={"state": state})
            assert login.status_code == 200
            params = parse_qs(urlsplit(login.json()["url"]).query)
            assert parse_qs(params["redirect_params"][0]) == {"state": [state]}
            assert "test-secret" not in login.text

            response = client.post("/api/v1/kite/session", json={"request_token": "one-time-token"})
            assert response.status_code == 204 and not response.content
            assert app.state.kite_provider.authenticated

        assert stat.S_IMODE(path.stat().st_mode) == 0o600
        saved = json.loads(path.read_text())
        assert saved["access_token"] == "session-token"
        with TestClient(app):
            assert app.state.kite_provider.authenticated

        saved["expires_at"] = (datetime.now(kite_session._IST) - timedelta(minutes=1)).isoformat()
        path.write_text(json.dumps(saved))
        assert not kite_session.restore_kite_session(get_settings()).kite_access_token.get_secret_value()
    finally:
        get_settings.cache_clear()


def test_failed_exchange_does_not_expose_or_persist_credentials(monkeypatch, tmp_path) -> None:
    path = tmp_path / "kite-session.json"
    monkeypatch.setattr(kite_session, "_SESSION_PATH", path)
    monkeypatch.setenv("KITE_API_KEY", "test-key")
    monkeypatch.setenv("KITE_API_SECRET", "test-secret")
    monkeypatch.setenv("KITE_ACCESS_TOKEN", "")
    get_settings.cache_clear()

    def reject(self, request_token, *, api_secret):
        raise TokenException(request_token)

    monkeypatch.setattr(kite_session.KiteConnect, "generate_session", reject)
    try:
        with TestClient(app) as client:
            response = client.post("/api/v1/kite/session", json={"request_token": "expired-token"})
            assert response.status_code == 401
            assert "expired-token" not in response.text
            assert not path.exists()
    finally:
        get_settings.cache_clear()

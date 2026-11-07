# Trading Assistant Backend

The first implementation slice is a local FastAPI backend that connects to the
owner's existing Kite Connect account. It returns live quote snapshots and
historical candles from Kite. It does not place orders, call an LLM, build a UI,
or persist provider market data. This slice is for local development only: it
does not implement application login and must not be deployed or exposed beyond
the local machine.

## Run locally

Use Python 3.12 or newer. From the repository root, create the config file if
needed:

```sh
test -f .env || cp .env.example .env
```

Set `KITE_API_KEY` and `KITE_ACCESS_TOKEN` in `.env`. Use the access token from
your existing `kiteconnect.generate_session()` flow; this backend does not
implement Kite login or token exchange. Kite access tokens expire daily, so
update the value in `.env` when you generate a new one. Keep `.env` private; it
is ignored by Git.

Run the startup script. It installs the application and development
dependencies, then starts FastAPI bound to loopback only:

```sh
./scripts/run_backend.sh
```

If `.env` still contains example placeholders, the script asks you to fill them
in and rerun it. The API reads the access token on startup; restart the backend
after changing it.

## Market-data endpoints

Fetch real quote snapshots:

```sh
curl 'http://127.0.0.1:8000/api/v1/market-data/quotes?symbols=NSE%3AINFY&symbols=NSE%3ARELIANCE'
```

Fetch historical candles (requires Kite's historical-data entitlement):

```sh
curl 'http://127.0.0.1:8000/api/v1/market-data/candles?exchange=NSE&symbol=INFY&interval=day&from=2025-01-02T09%3A15%3A00%2B05%3A30&to=2025-01-03T15%3A30%3A00%2B05%3A30'
```

The API supports Kite intervals `minute`, `3minute`, `5minute`, `10minute`,
`15minute`, `30minute`, `60minute`, and `day`. Quote and candle responses are
normalized into typed JSON. Data is returned from the provider on each call and
is not stored by this backend. A successful quote request confirms quote
connectivity; plan entitlements for historical data are checked by the candle
request itself.

Health check: `GET /api/v1/health`. OpenAPI docs: `http://127.0.0.1:8000/docs`.
The other endpoints are `GET /api/v1/market-data/capabilities`,
`GET /api/v1/market-data/quotes`, and `GET /api/v1/market-data/candles`.
You can import [`docs/postman/trading-assistant.postman_collection.json`](docs/postman/trading-assistant.postman_collection.json)
into Postman to run these requests and their basic response checks.

## Development checks

```sh
.venv/bin/pytest
```

The tests use mocked Kite responses and do not make live provider calls.

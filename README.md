# Trading Assistant

An AI-assisted analysis application for Indian equities. The design direction is documented in the [Engineering Design Document (EDD) v0.3](docs/EDD-v0.3.md).

## What is implemented today

The application runs locally with a **FastAPI backend** for Zerodha Kite quote snapshots and candles and a **Next.js research dashboard**. Use the dashboard to select a listing, switch chart intervals, and inspect the available market data. Evaluation and AI reports, persistence, and application login are planned. Keep both servers on your own machine.

The backend calls Kite for real provider data. It does not substitute synthetic data. Historical candle availability depends on the Kite account's entitlements.

## Run locally

### Requirements and credentials

- Python 3.12 or newer.
- A Kite API key and a valid Kite access token for the owner's account. Ask the repository owner to provide these through an approved secure channel. Do not paste credentials into chat, issues, pull requests, or source files.
- Kite access tokens expire at 6:00 AM the next day; see [Kite Connect authentication docs](https://www.kite.trade/docs/connect/v3/user/). Ask the owner for a fresh token when needed. The backend does not implement Kite login or token generation. It needs the API key and access token at runtime; it does not need the API secret.

Clone the repository and enter its directory, or open your existing local clone:

```sh
git clone https://github.com/piyushjha97/trading-assistant.git
cd trading-assistant
```

Create a local `.env` file and restrict its permissions:

```sh
touch .env
chmod 600 .env
```

Open `.env` in a local text editor and add the credentials supplied by the owner:

```dotenv
KITE_API_KEY=
KITE_ACCESS_TOKEN=
KITE_TIMEOUT_SECONDS=10
```

Fill in the first two values locally. Do not commit or share the file; `.env` is ignored by Git.

### Start the backend

From the repository root:

```sh
./scripts/run_backend.sh
```

The script creates a local `.venv` and installs the application and development dependencies if needed, then starts FastAPI on `127.0.0.1:8000`. Keep the process running in that terminal. If you update the access token, stop and restart the backend.

### Open the dashboard

With the backend running, use Node.js 20.9 or newer in a second terminal:

```sh
cd frontend
npm ci
npm run dev
```

Open `http://127.0.0.1:3000`. The dashboard requests market data through the
Next.js server, which uses `http://127.0.0.1:8000` by default. Set
`TRADING_BACKEND_URL` in the Next.js server environment if the local backend
uses a different loopback port.

### Check the API

- Health: `GET http://127.0.0.1:8000/api/v1/health`
- Interactive API documentation: `http://127.0.0.1:8000/docs`
- Kite capabilities: `GET http://127.0.0.1:8000/api/v1/market-data/capabilities`
- Live quote snapshots: `GET http://127.0.0.1:8000/api/v1/market-data/quotes`
- Historical candles: `GET http://127.0.0.1:8000/api/v1/market-data/candles`

Example quote request:

```sh
curl 'http://127.0.0.1:8000/api/v1/market-data/quotes?symbols=NSE%3AINFY&symbols=NSE%3ARELIANCE'
```

Historical candle requests require the relevant Kite entitlement. The Postman collection is at [docs/postman/trading-assistant.postman_collection.json](docs/postman/trading-assistant.postman_collection.json).

## Local analytics

`analyze_closed_candles` in `trading_assistant.analytics` consumes normalized,
chronologically ordered candles for one listing and interval. It returns the
input range, latest OHLCV, and these indicators:

| Signal | Default indicator |
| --- | --- |
| Trend direction | 20-bar SMA and EMA |
| Momentum | 14-period Wilder RSI |
| Volatility | 14-period Wilder ATR |
| Trend strength | 14-period Wilder ADX, requiring 28 candles |
| Trading participation | Latest volume divided by the mean of the previous 20 bars |
| Breakout context | Highest high and lowest low of the previous 20 bars |

Periods are configurable. Indicator values return `None` when warm-up is
insufficient or the relative-volume baseline is zero. Relative volume uses a
rolling baseline without adjusting for time of day. The caller supplies only
closed candles after checking session coverage, freshness, and adjustment basis.

## Safety

This backend does not implement application authentication. It binds to loopback for local development; do not change the host to expose it to a network or deploy it. Never commit `.env`, access tokens, API secrets, or other credentials.

# Trading Assistant

An AI-assisted analysis application for Indian equities. The design direction is documented in the [Engineering Design Document (EDD) v0.3](docs/EDD-v0.3.md).

## What is implemented today

The application runs locally with a **FastAPI backend** for Zerodha Kite quote snapshots and candles and a **Next.js research dashboard**. Use the dashboard to select a listing, switch chart intervals, and inspect the available market data. Evaluation and AI reports, persistence, and application login are planned. Keep both servers on your own machine.

The backend calls Kite for real provider data. It does not substitute synthetic data. Historical candle availability depends on the Kite account's entitlements.

## Run locally

### Requirements and credentials

- Python 3.12 or newer.
- A Kite API key and API secret for the owner's account. Keep these in the backend's local `.env`.
- Set the Kite Connect application's registered redirect URL to `http://127.0.0.1:3000/api/kite/callback`. If your app already redirects to `http://127.0.0.1:8000/`, the local backend forwards the callback to the dashboard on port 3000. Use `127.0.0.1` to open the dashboard so the callback can validate the sign-in state.

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
KITE_API_SECRET=
KITE_TIMEOUT_SECONDS=10
```

Fill in the first two values locally. Do not commit or share the file; `.env` is ignored by Git.

### Start the backend

From the repository root:

```sh
./scripts/run_backend.sh
```

The script creates a local `.venv`, installs the application and development dependencies, and starts FastAPI on `127.0.0.1:8000`. For manual API-only use, you can supply `KITE_ACCESS_TOKEN` in `.env` instead of connecting through the dashboard.

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

Select **Connect Kite** and complete Zerodha sign-in. The backend exchanges the
one-time request token and stores the resulting access token in the ignored
`.secrets/kite-session.json` file. The dashboard resumes the selected data
request after sign-in. The token works across refreshes and backend restarts
until Kite expires it at 6:00 a.m. IST the next day or revokes it. Use **Load
market data** and the interval buttons to refresh the candlestick and volume
chart during a valid session. [Kite authentication](https://kite.trade/docs/connect/v3/user/)

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

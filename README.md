# Trading Assistant

An AI-assisted analysis application for Indian equities. The design direction is documented in the [Engineering Design Document (EDD) v0.3](docs/EDD-v0.3.md).

## What is implemented today

The current application slice is a **local FastAPI backend** that requests live quote snapshots and historical candles from Zerodha Kite Connect. It does not generate AI analysis or place orders, and it has no UI, persistence, or application login yet. Run it on your own machine only; it is not ready to deploy or expose on a network.

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

## Safety

This backend does not implement application authentication. It binds to loopback for local development; do not change the host to expose it to a network or deploy it. Never commit `.env`, access tokens, API secrets, or other credentials.

# V1 Implementation Plan

- **Design authority:** [EDD v0.2](EDD-v0.2.md). This plan does not change its decisions.
- **V1 target:** a small, hosted, single-owner market-analysis app for NSE/BSE equities.
- **Market-data scope:** current-day intraday candles for on-demand analysis; fetch only the prior bars required to warm up the selected indicators. Do not build a historical data warehouse.
- **Cost constraint:** use a provider with free access for the V1 market-data needs. Do not add a paid fallback unless the owner approves it.
- **Shape:** one typed Python application, synchronous requests, one market-data provider and one LLM. No orders, scheduled jobs, queues, microservices, LangGraph or Google ADK.
- **Initial provider to try:** Upstox, provisionally. Current official docs describe a free, read-only Analytics Token, current-day intraday candles and live quote/streaming APIs. This is a first connectivity candidate, not a claim that the owner's account is eligible or that candle snapshots may be retained.
- **Current status:** no provider connectivity test has passed yet. Do not use fabricated or synthetic market candles in the app.

## How to keep this small

Do not require every hosting, monitoring or future-scale decision before the first code. Resolve only choices that can block the next step. Try one provider first; if it works for the minimum V1 need and its terms allow the required use, proceed. For V1, fetch current-day candles when an analysis is requested. Add a continuous WebSocket stream only if the UI needs prices that update between requests. Keep the app simple and use actual provider responses for market-data checks; never substitute invented candle values.

## Phase 0 — Pick and verify a free market-data provider

The EDD names Upstox, Angel One SmartAPI and TejHQ as possible providers, but selects none. To keep V1 simple, try Upstox first rather than comparing every candidate. Its current official documentation describes a free, read-only Analytics Token that supports current-day intraday candles and live market-data APIs. If this does not work for the owner's account or V1 data needs, return with the specific failure before adding another provider.

| Work | Depends on | Result and check |
|---|---|---|
| Confirm the minimum V1 data need: supported NSE/BSE listings, an intraday interval and enough bars for the initial indicators. Keep the EDD's single-owner, no-orders scope. | EDD v0.2 | A short list of symbols and intervals. Limit old history to indicator warm-up; do not backfill a large history. |
| Create an Upstox Analytics Token for the owner's account and make one authenticated Intraday Candle V3 request for a real NSE/BSE instrument while its market is open. Check the latest candle timestamp and whether the last candle is complete. | Minimum data need; owner has an Upstox account/token | A recorded result: request succeeded and returned real same-day candles, or the exact HTTP/API error and next action. Never put the token in chat, source control, screenshots or logs. |
| Check whether the applicable account terms allow the V1 use: processing, private display and the EDD's per-report normalized candle snapshot, including storage and deletion. | Provider terms | Record the relevant terms or written provider answer. If snapshot rights are unclear, pause snapshot persistence and ask the owner; free API access does not itself establish retention rights. |

**Phase 0 is done when:** the Upstox test returns real same-day candles for the minimum V1 request and the required use/snapshot rights are clear, or the exact blocker is presented to the owner. Do not implement a second provider just because the first test fails. A same-day-only V1 initially supports intraday analysis; daily/swing analysis needs enough prior candles to warm up its indicators. The backend shell can proceed after implementation approval, but live data handling follows the successful connectivity and terms checks.

### Official research starting points

Provider comparison from current official sources: **Upstox** is the first choice to test because its free read-only Analytics Token supports the current-day candle and live-data API categories; current-day intraday candles are available over REST, and continuous WebSocket feeds are available if needed. The WebSocket uses Protobuf, so defer it unless the UI needs continuous updates. **Angel One SmartAPI** also documents free live WebSocket/quote access, but its documented login uses account credentials plus TOTP and the session lasts until midnight. **TejHQ is not suitable for live/same-day-in-session V1:** it documents end-of-day data, normally available the next morning. Sources: [Upstox Analytics Token](https://upstox.com/developer/api-documentation/analytics-token/), [Upstox Intraday Candle V3](https://upstox.com/developer/api-documentation/v3/get-intra-day-candle-data/), [Upstox live feed V3](https://upstox.com/developer/api-documentation/v3/get-market-data-feed/), [Angel One SmartAPI](https://smartapi.angelone.in/docs) and [FAQ](https://smartapi.angelone.in/faq), [TejHQ API reference](https://tejhq.dev/docs) and [data terms](https://tejhq.dev/data-terms). NSE publishes a separate [Data Sharing & Usage Policy](https://www.nseindia.com/static/market-data/nse-data-policy). Check account-specific terms before storing or displaying data: API documentation and a successful response do not by themselves establish snapshot-retention rights. Sources checked 2026-11-07; recheck when testing.

## Phase 1 — Backend foundation and API shell

**Depends on:** owner approval to begin implementation. Provider research can continue in parallel using the Phase 0 checklist.

**Work:** Create the Python modular-monolith app, FastAPI shell, typed request/response contracts, configuration, local development setup, PostgreSQL schema/migrations, and owner-only authentication. Test the backend contracts, auth and error handling. Do not build the UI or fabricate market-data responses.

**Deliverable:** a locally runnable backend with documented API contracts and an owner-only auth boundary.

**Acceptance check:** the API starts from documented steps; request/response schemas and errors are tested; protected routes reject anonymous requests; health/status output contains no secrets; schema migrations work from an empty database.

**Done when:** the backend shell and its first API tests run locally and are ready for the selected provider integration.

## Phase 2 — Basic market data

**Depends on:** Phase 1; Phase 0 provider capability and snapshot-rights checks for any live or retained data.

**Work:** Connect one provider adapter to Upstox's current-day intraday candle endpoint; retrieve real candles on each analysis request. Add only the instrument lookup, request limits/timeouts, normalization and validation needed for the observed responses. Store exact normalized candles only under the approved retention policy. Defer a persistent streaming connection unless the UI needs continuous updates. Avoid building a provider framework or generalized data warehouse.

**Deliverable:** a tested backend endpoint/service can retrieve and validate supported candles, with source and time-range recorded.

**Acceptance check:** supported requests return correctly ordered candles with explicit timestamps and OHLCV; unsupported, empty, malformed, stale or unauthorized responses produce clear errors; snapshots cannot be written when rights are unapproved and expire/delete according to the selected policy.

**Done when:** one provider works for the limited V1 request set and its limitations are visible to the user.

## Phase 3 — Deterministic analysis

**Depends on:** Phase 2 and the EDD's initial indicator definitions.

**Work:** Implement OHLCV evidence, SMA/EMA, RSI and ATR with clear warm-up and missing-data behavior. Add a small set of named analysis/risk gates and candidate price levels. Keep all calculations in ordinary typed Python functions.

**Deliverable:** tested backend services and API responses for deterministic evidence and candidate levels calculated from real provider candles or a permitted retained snapshot.

**Acceptance check:** calculations are checked against actual provider candles (retained as test data only if permitted); repeated analysis of the same permitted input produces repeatable outputs; candle boundaries and lookahead are checked; failed or unknown mandatory gates cannot become actionable; no scalar setup score or uncalibrated probability is produced. Do not generate synthetic candles for these checks.

**Done when:** the analysis result is useful and explainable without calling an LLM.

## Phase 4 — LLM report

**Depends on:** Phase 3; an LLM choice and its data-handling terms; direction rules for the supported instrument and horizon.

**Work:** Send only the structured evidence needed for one report to one LLM. Require typed output that refers to supplied evidence and candidate levels. Validate the result in Python and return WAIT/NO_TRADE when data or actionability checks fail.

**Deliverable:** a tested synchronous backend endpoint returns a validated report or a clear bounded error.

**Acceptance check:** malformed, unsupported or invented model output is rejected or downgraded; invalid market data stops before the LLM call; duplicate requests do not cause duplicate paid model calls; no work continues in the background after a timeout.

**Done when:** the report separates market data, computed evidence and LLM interpretation and records the versions used.

## Phase 5 — UI and end-to-end integration

**Depends on:** the Phase 4 report API and its contract tests are stable. Chart replay depends on permitted retained snapshots.

**Work:** Build the React/TypeScript interface against the tested backend APIs: instrument/timeframe form, report view, simple report history, charts from the report's own snapshot where allowed, and follow-up chat scoped to that report. Keep UI logic thin; validation and analysis rules stay in the backend.

**Deliverable:** an integrated UI lets the owner request, inspect and revisit an analysis through the backend APIs.

**Acceptance check:** UI integration tests use the documented API contracts; unsupported settings cannot be submitted; the report shows freshness, source and actionability; chart data matches the report snapshot; chat stays within that report and cannot place orders.

**Done when:** the UI works end to end against the tested backend without duplicating business rules or adding unrelated features.

## Phase 6 — Deploy the private V1

**Depends on:** Phases 1–5 and a chosen hosting option.

**Work:** Deploy the single application with HTTPS, private database/storage, backend-only secrets, basic logs, backups and a tested restore/deletion procedure. Set a modest request and cost limit based on observed use.

**Deliverable:** private owner-only hosted V1 and short operating instructions.

**Acceptance check:** anonymous and cross-owner access fail; secrets are not exposed in browser responses or logs; provider/model failures return bounded errors; backup restore and approved data deletion are demonstrated.

**Done when:** the EDD's V1 acceptance criteria pass for the private owner deployment. Public registration, sharing, scheduled analysis and order execution remain out of scope.

## Decisions to make when needed

- **Before live provider integration:** confirm the Upstox account/token works, choose supported intraday intervals, decide the minimum indicator warm-up bars, and confirm data/snapshot rights.
- **Before storing user reports:** hosting choice, region, authentication/session approach and retention periods.
- **Before sending evidence to an LLM:** model/provider, applicable data terms and bounded cost/latency.
- **Before actionable LONG/SHORT output:** supported segment × horizon × direction rules, especially cash-equity SHORT.
- **After basic V1 works:** whether to pursue more indicators, additional providers, backtesting or paper trading. These are not prerequisites for the first vertical slice.

No calendar estimates are included. Each phase should be kept small and adjusted based on what the preceding phase actually demonstrates. This plan does not authorize application code; wait for the owner's approval to start implementation.

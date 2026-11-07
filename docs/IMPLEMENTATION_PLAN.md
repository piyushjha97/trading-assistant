# V1 Implementation Plan

- **Design authority:** [EDD v0.3](EDD-v0.3.md). This plan does not change its decisions.
- **V1 target:** a small, hosted, single-owner market-analysis app for NSE/BSE equities.
- **Market-data scope:** on-demand quote snapshots and candle requests for analysis; fetch only the prior bars required to warm up selected indicators. Do not build a historical data warehouse or continuous stream in the first backend slice.
- **Cost constraint:** Kite Connect is the owner-selected provider. Do not assume market-data access is free; confirm the active plan and any recurring charge before relying on historical candles.
- **Shape:** one typed Python application, synchronous requests, one market-data provider and one LLM. No orders, scheduled jobs, queues, microservices, LangGraph or Google ADK.
- **Provider:** Zerodha Kite Connect, selected by the owner because they already hold a Zerodha account. The owner has successfully exchanged a Kite request token using `kiteconnect` and received quotes for `NSE:INFY` and `NSE:RELIANCE`. This verifies quote connectivity for that account. Historical-candle entitlement and supported intervals still need a direct API check. Do not use fabricated or synthetic market candles in the app.

## How to keep this small

Do not require every hosting, monitoring or future-scale decision before the first code. Resolve only choices that can block the next step. Try one provider first; if it meets the minimum V1 need, proceed. For V1, fetch current-day candles when an analysis is requested. Add a continuous WebSocket stream only if the UI needs prices that update between requests. Keep the app simple and use actual provider responses for market-data checks; never substitute invented candle values.

## Phase 0 — Verify Kite historical-data access

Kite Connect is the selected provider. The owner has verified authentication and quote retrieval. Before depending on historical candles, confirm that the owner's account can retrieve the required intervals and enough bars for the initial indicators. This is a data-access check for the local application, not a blocker to storing the owner's fetched candle responses with their reports and charts. Public display or redistribution is outside the current scope.

| Work | Depends on | Result and check |
|---|---|---|
| Confirm the first supported symbols, candle interval, and indicator warm-up requirement. | EDD v0.3 | A small request list; do not backfill unrelated history. |
| Request a small, recent historical candle range for one real NSE equity using the owner's account. Record the actual timestamps, interval, and any entitlement/API error. | Kite access token and account | Real provider response or the exact error. Never put credentials or tokens in chat, source control, screenshots, or logs. |

**Phase 0 status:** Kite authentication and quote connectivity are verified. Historical-candle entitlement and coverage should be confirmed with a real request before relying on those intervals. Do not add another provider unless Kite cannot meet a necessary requirement and the owner approves a change.

### Official provider references

The owner's quote check used the official `kiteconnect` client. Kite's [authentication docs](https://kite.trade/docs/connect/v3/user/) describe the request-token exchange; its [historical candle API](https://kite.trade/docs/connect/v3/historical/) documents supported intervals and ranges. These references help verify the API behavior; the account's actual response confirms its entitlement.

## Phase 1 — Backend foundation and API shell

**Depends on:** owner approval to begin implementation (granted). The initial backend is local and owner-only.

**Work:** Create the local Python/FastAPI shell, typed request/response contracts, configuration and development runner. For this local data-API stage, use the owner's manually generated Kite access token from `.env`; do not add application login, database or migrations yet. Add owner authentication and persistence before any hosted deployment. Do not build the UI or fabricate market-data responses.

**Deliverable:** a locally runnable backend with documented API contracts and no exposed market-data credentials.

**Acceptance check:** the API starts from the runner script; health and response schemas work; provider errors are bounded; health/status output contains no secrets; `.env` stays untracked. This local stage is not deployable.

**Done when:** the backend shell and its mocked API tests run locally and are ready for real Kite connectivity checks.

## Phase 2 — Basic market data

**Depends on:** Phase 1 and a successful Phase 0 historical-data check for the requested intervals.

**Work:** Connect the Kite adapter to quote and historical-candle endpoints; retrieve real provider data on request. Add only the instrument lookup, request limits/timeouts, normalization and validation needed for observed responses. Return real provider data. Add local report and candle persistence with report-history work. Defer WebSocket streaming unless the UI needs continuous updates. Avoid building a provider framework or generalized data warehouse.

**Deliverable:** a tested backend endpoint/service can retrieve and validate supported candles, with source and time-range recorded.

**Acceptance check:** supported requests return correctly ordered candles with explicit timestamps and OHLCV; unsupported, empty, malformed, stale or unauthorized responses produce clear errors.

**Done when:** one provider works for the limited V1 request set and its limitations are visible to the user.

## Phase 3 — Deterministic analysis

**Depends on:** Phase 2 and the EDD's initial indicator definitions.

**Work:** Implement OHLCV evidence, SMA/EMA, RSI and ATR with clear warm-up and missing-data behavior. Add a small set of named analysis/risk gates and candidate price levels. Keep all calculations in ordinary typed Python functions.

**Deliverable:** tested backend services and API responses for deterministic evidence and candidate levels calculated from real provider candles or the candle input saved with a report.

**Acceptance check:** calculations are checked against real provider candles; repeated analysis of the same input produces repeatable outputs; candle boundaries and lookahead are checked; failed or unknown mandatory gates cannot become actionable; no scalar setup score or uncalibrated probability is produced. Do not generate synthetic candles for these checks.

**Done when:** the analysis result is useful and explainable without calling an LLM.

## Phase 4 — LLM report

**Depends on:** Phase 3; an LLM choice and its data-handling terms; direction rules for the supported instrument and horizon.

**Work:** Send only the structured evidence needed for one report to one LLM. Require typed output that refers to supplied evidence and candidate levels. Validate the result in Python and return WAIT/NO_TRADE when data or actionability checks fail.

**Deliverable:** a tested synchronous backend endpoint returns a validated report or a clear bounded error.

**Acceptance check:** malformed, unsupported or invented model output is rejected or downgraded; invalid market data stops before the LLM call; duplicate requests do not cause duplicate paid model calls; no work continues in the background after a timeout.

**Done when:** the report separates market data, computed evidence and LLM interpretation and records the versions used.

## Phase 5 — UI and end-to-end integration

**Depends on:** the Phase 4 report API and its contract tests are stable. Chart replay uses the candle input saved with the report.

**Work:** Build the React/TypeScript interface against the tested backend APIs: instrument/timeframe form, report view, simple report history, charts from the candle data saved with the report, and follow-up chat scoped to that report. Keep UI logic thin; validation and analysis rules stay in the backend.

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

- **Before relying on historical analysis:** confirm Kite entitlement, supported intervals, and the minimum indicator warm-up bars. Before expanding beyond the private owner application or redistributing data, review the applicable provider requirements.
- **Before storing user reports:** hosting choice, region, authentication/session approach and retention periods.
- **Before sending evidence to an LLM:** model/provider, applicable data terms and bounded cost/latency.
- **Before actionable LONG/SHORT output:** supported segment × horizon × direction rules, especially cash-equity SHORT.
- **After basic V1 works:** whether to pursue more indicators, additional providers, backtesting or paper trading. These are not prerequisites for the first vertical slice.

No calendar estimates are included. Each phase should be kept small and adjusted based on what the preceding phase actually demonstrates. The owner has approved the backend-first implementation. Later phases still require their listed decisions and acceptance checks.

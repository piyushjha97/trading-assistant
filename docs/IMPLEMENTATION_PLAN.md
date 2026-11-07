# V1 Implementation Plan

- **Design authority:** [EDD v0.2](EDD-v0.2.md). This plan does not change its decisions.
- **V1 target:** a small, hosted, single-owner market-analysis app for NSE/BSE equities.
- **Cost constraint:** use a provider with free access for the V1 market-data needs. Do not add a paid fallback unless the owner approves it.
- **Shape:** one typed Python application, synchronous requests, one market-data provider and one LLM. No orders, scheduled jobs, queues, microservices, LangGraph or Google ADK.
- **Current status:** planning only. Application work starts after the owner's approval.

## How to keep this small

Do not require every hosting, monitoring or future-scale decision before the first code. Resolve only choices that can block the next step. Use a small provider spike to choose a workable free source; keep the app simple and add operational detail when the chosen host is known. Use synthetic fixtures for development until live provider access and terms are confirmed.

## Phase 0 — Pick and verify a free market-data provider

The EDD names Upstox, Angel One SmartAPI and TejHQ as possible providers, but selects none. Compare those candidates using their current official material and account terms. Do not build a large vendor scorecard.

| Work | Depends on | Result and check |
|---|---|---|
| Confirm the minimum V1 data need: supported NSE/BSE listings, a small set of candle intervals and the lookback needed by the initial indicators. Keep the EDD's single-owner, no-orders scope. | EDD v0.2 | A short list of required symbols/intervals/lookbacks. Drop unsupported options from V1 rather than building around hypothetical provider capabilities. |
| Check which candidate offers free access for the owner's account and supports that exact data need. Check current endpoint status, authentication, limits and terms using official provider sources. | Minimum data need | One recommended candidate, with unsupported items clearly listed. No price, access or capability is assumed from an API page alone. |
| Make a small, non-production request using the intended account. Inspect timestamps, OHLCV, gaps, session boundaries and one historical corporate-action example if the selected history includes one. | Candidate check; authorized account | A short spike note showing working requests and data limitations. Do not keep or commit raw responses unless the terms allow it. |
| Confirm that the free plan permits the V1 use: processing, private display and the EDD's per-report normalized candle snapshot, including its storage and deletion. | Provider terms | Record the applicable terms or written provider answer. If snapshot rights are not clear, pause that provider-backed feature and ask the owner; do not treat free access as a retention license. |

**Phase 0 is done when:** one free provider can meet the minimum V1 data need and the relevant use and snapshot rights are clear, or the exact blocker is presented to the owner. The app shell does not need to wait for every future product decision, but live provider integration and snapshot storage do.

### Official research starting points

The EDD's candidates remain candidates, not endorsements. Check current official documentation and account-specific terms during Phase 0: [Upstox Historical Candle V3](https://upstox.com/developer/api-documentation/v3/get-historical-candle-data/), [Angel One SmartAPI](https://smartapi.angelone.in/docs), and NSE's [Data Sharing & Usage Policy](https://www.nseindia.com/static/market-data/nse-data-policy). Upstox marks its older [V2 historical-candle endpoint deprecated](https://upstox.com/developer/api-documentation/get-historical-candle-data/), so confirm the supported endpoint when testing. These links do not establish free access or data-retention rights.

## Phase 1 — Minimal app foundation

**Depends on:** owner approval to begin implementation. Provider research can continue in parallel using the Phase 0 checklist.

**Work:** Create the Python modular-monolith app, basic typed API, simple React/TypeScript UI, configuration, local development setup, PostgreSQL schema/migrations, and owner-only sign-in. Keep the project tooling conventional and limited to what the app needs.

**Deliverable:** a locally runnable, owner-only application shell using synthetic data.

**Acceptance check:** the app starts from documented steps; the owner can sign in; protected data is not available anonymously; health/status output contains no secrets; schema migrations work from an empty database.

**Done when:** a small vertical slice runs locally and is ready to receive the selected provider integration.

## Phase 2 — Basic market data

**Depends on:** Phase 1; Phase 0 provider capability and snapshot-rights checks for any live or retained data.

**Work:** Add one provider adapter, instrument lookup, request limits/timeouts, candle normalization and basic validation. Store the exact normalized candles used by a report only under the approved retention policy. Avoid building a provider framework or generalized data warehouse.

**Deliverable:** one on-demand request can retrieve and validate supported candles, with source and time-range recorded.

**Acceptance check:** supported requests return correctly ordered candles with explicit timestamps and OHLCV; unsupported, empty, malformed, stale or unauthorized responses produce clear errors; snapshots cannot be written when rights are unapproved and expire/delete according to the selected policy.

**Done when:** one provider works for the limited V1 request set and its limitations are visible to the user.

## Phase 3 — Deterministic analysis

**Depends on:** Phase 2 and the EDD's initial indicator definitions.

**Work:** Implement OHLCV evidence, SMA/EMA, RSI and ATR with clear warm-up and missing-data behavior. Add a small set of named analysis/risk gates and candidate price levels. Keep all calculations in ordinary typed Python functions.

**Deliverable:** deterministic evidence and candidate levels from a candle fixture or permitted snapshot.

**Acceptance check:** fixed inputs produce repeatable outputs; tests cover warm-up, missing/gapped data, candle boundaries and lookahead; failed or unknown mandatory gates cannot become an actionable plan; no scalar setup score or uncalibrated probability is produced.

**Done when:** the analysis result is useful and explainable without calling an LLM.

## Phase 4 — LLM report

**Depends on:** Phase 3; an LLM choice and its data-handling terms; direction rules for the supported instrument and horizon.

**Work:** Send only the structured evidence needed for one report to one LLM. Require typed output that refers to supplied evidence and candidate levels. Validate the result in Python and return WAIT/NO_TRADE when data or actionability checks fail.

**Deliverable:** one synchronous analysis request returns a validated report or a clear bounded error.

**Acceptance check:** malformed, unsupported or invented model output is rejected or downgraded; invalid market data stops before the LLM call; duplicate requests do not cause duplicate paid model calls; no work continues in the background after a timeout.

**Done when:** the report separates market data, computed evidence and LLM interpretation and records the versions used.

## Phase 5 — Basic user workflow

**Depends on:** Phases 1 and 4. Chart replay depends on permitted retained snapshots.

**Work:** Add the instrument/timeframe form, report view, simple report history, charts from the report's own snapshot where allowed, and follow-up chat scoped to that report.

**Deliverable:** the owner can request, inspect and revisit an analysis.

**Acceptance check:** unsupported settings cannot be submitted; the report shows freshness, source and actionability; chart data matches the report snapshot; chat stays within that report and cannot place orders.

**Done when:** the main owner workflow works end to end without adding unrelated settings or features.

## Phase 6 — Deploy the private V1

**Depends on:** Phases 1–5 and a chosen hosting option.

**Work:** Deploy the single application with HTTPS, private database/storage, backend-only secrets, basic logs, backups and a tested restore/deletion procedure. Set a modest request and cost limit based on observed use.

**Deliverable:** private owner-only hosted V1 and short operating instructions.

**Acceptance check:** anonymous and cross-owner access fail; secrets are not exposed in browser responses or logs; provider/model failures return bounded errors; backup restore and approved data deletion are demonstrated.

**Done when:** the EDD's V1 acceptance criteria pass for the private owner deployment. Public registration, sharing, scheduled analysis and order execution remain out of scope.

## Decisions to make when needed

- **Before live provider integration:** named free provider/account, supported intervals/lookback and data/snapshot rights.
- **Before storing user reports:** hosting choice, region, authentication/session approach and retention periods.
- **Before sending evidence to an LLM:** model/provider, applicable data terms and bounded cost/latency.
- **Before actionable LONG/SHORT output:** supported segment × horizon × direction rules, especially cash-equity SHORT.
- **After basic V1 works:** whether to pursue more indicators, additional providers, backtesting or paper trading. These are not prerequisites for the first vertical slice.

No calendar estimates are included. Each phase should be kept small and adjusted based on what the preceding phase actually demonstrates. This plan does not authorize application code; wait for the owner's approval to start implementation.

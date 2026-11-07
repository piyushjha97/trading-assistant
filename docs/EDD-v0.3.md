# Engineering Design Document
## AI-Assisted Indian Equity Analysis

- **Document version:** 0.3
- **Status:** Architecture baseline
- **Date:** 7 November 2026
- **Supersedes:** [EDD v0.2](EDD-v0.2.md) as the current design baseline
- **Decision authority:** Project owner

## 1. Purpose and product scope

The application helps its owner analyze NSE/BSE equities using market data, technical calculations, market context, and AI-assisted explanations. It is an analysis and decision-support tool. It does not place or manage orders.

The current development phase is a private, local application using the owner's Zerodha Kite Connect account. The repository already has a FastAPI backend with Kite quote and candle endpoints. The analysis API, deterministic engines, chat, and UI remain to be built.

The broader product direction is a hosted, private owner application. Access by other users or public display is a separate product decision and requires its own security, provider, and regulatory review.

## 2. Architecture decisions

| Area | Decision |
|---|---|
| Application shape | Strongly typed Python modular monolith using FastAPI. Modules are Python packages and function calls, not separately deployed services. |
| Request flow | Synchronous request/response for analysis. |
| Market data | Zerodha Kite Connect is the selected provider for quotes and candles. Use real provider responses; never substitute synthetic market data. |
| Data storage | The application may save fetched candles with the associated analysis for the owner's local reports and charts. Public redistribution is outside the current scope. |
| Analytics | Deterministic, testable calculations implemented in Python. |
| Evaluation | Explicit, explainable rules and named gates determine bias, actionability, and verdict. |
| AI | Optional agent and LLM capabilities add qualitative context and explanations. They do not invent market facts or bypass mandatory deterministic gates. |
| Chat | Report-scoped and uses the same data and analysis services as the dashboard. |
| UI | React and TypeScript remain provisional choices. |
| Persistence | PostgreSQL remains provisional for the hosted application. |

Keep module boundaries clear while retaining one application and one deployment. Do not add microservices, message brokers, LangGraph, Google ADK, or background jobs without a demonstrated need.

## 3. Architecture and request flow

The analysis API is the entry point for the UI. It coordinates the request; the market-data module calls Kite; the analytics engine calculates evidence; and the evaluation engine applies rules to that evidence. The response returns through the API as typed JSON.

~~~mermaid
flowchart LR
    UI[UI] -->|Analysis request| API[Analysis API]
    API -->|Request parameters| DATA[Market data module]
    DATA --> KITE[Kite REST API]
    DATA --> SENT[Future sentiment sources]
    KITE --> NORMALIZE[Normalize and validate data]
    SENT --> NORMALIZE
    NORMALIZE -->|Candles and numeric context| ANALYTICS[Analytics engine]
    NORMALIZE -->|Sourced text and market context| AGENTS[AI research agents]
    ANALYTICS -->|Technical and sentiment features| EVALUATION[Evaluation engine]
    AGENTS -->|Attributed qualitative evidence| EVALUATION
    EVALUATION -->|Gates, bias, actionability, verdict| AI[AI report and chat services]
    AI -->|Structured analysis result| API
    API -->|JSON response| UI

    UI -->|Follow-up question| CHATAPI[Chat API]
    CHATAPI --> CHAT[Report-scoped assistant]
    CHAT -->|Report context or approved read-only request| SHARED[Shared data and analysis services]
    SHARED --> CHAT
    CHAT -->|Grounded answer| CHATAPI
    CHATAPI -->|JSON response| UI
~~~

The diagram shows logical module boundaries, not network hops. Modules exchange typed Python objects internally. The API serializes the completed result for the UI.

### 3.1 Module responsibilities

| Module | Responsibility |
|---|---|
| **Analysis API** | Validates the UI request, invokes application services, handles request errors, and returns the response contract. |
| **Market data** | Resolves exchange and symbol, requests Kite quotes/candles, and normalizes provider responses. It also provides adapters for future sentiment sources. |
| **Analytics engine** | Calculates technical indicators and measurable sentiment features from validated, timestamped inputs. It does not choose a trade verdict. |
| **Evaluation engine** | Applies versioned deterministic rules and gates to analytics evidence and any explicitly allowed qualitative evidence. Produces bias, actionability, verdict, candidate levels, and reasons. |
| **AI research agents** | May retrieve and summarize approved sources as attributed qualitative evidence. Their output is identified as model-generated and enters evaluation only through explicit rules. |
| **AI report and chat services** | Explain a completed result and answer bounded, report-scoped follow-up questions using shared application services. |
| **Chat API** | Supplies report context and routes permitted read-only questions through the shared application services. |

### 3.2 Analysis flow

1. The UI submits exchange, symbol, interval, requested range/lookback, and analysis settings.
2. The API validates the request and calls the analysis service.
3. The market-data module resolves the instrument and fetches the required real candles from Kite. Additional sentiment sources can be added behind adapters.
4. The application normalizes and validates timestamps, OHLCV consistency, ordering, duplicates, completeness, and data freshness.
5. The analytics engine calculates requested indicators and returns typed values with their parameters, source range, and evidence references.
6. The evaluation engine checks data sufficiency and applies explicit rules. It may return LONG, SHORT, WAIT, or NO_TRADE, with named gate results and reasons.
7. Optional research agents may return attributed qualitative evidence; the evaluation engine uses it only where an explicit rule allows it. The deterministic gates remain authoritative for data quality, eligibility, and risk.
8. The AI report service may explain the structured result. The API returns the result, data timestamps, provenance, and warnings to the UI. The application can persist the report and its candle input for the owner's history and chart replay.

A live quote is optional for a candle-based analysis. Indicator calculations use completed candles by default; an incomplete current candle must be identified and handled explicitly.

### 3.3 Chat flow

Chat is grounded in a selected report. It can explain that report or, when the user changes the instrument, interval, or settings, request a new analysis through the same services. It must not create a second analysis implementation or place orders. Answers distinguish provider facts, calculated evidence, and AI interpretation, and include relevant source and freshness information.

## 4. Data and analysis contracts

Use typed request and result models at module boundaries:

- **Analysis request:** exchange, symbol, interval or timeframes, date range/lookback, indicator parameters, and relevant analysis preferences.
- **Market data bundle:** normalized candles plus source, requested/actual range, retrieval time, and any timestamped sentiment inputs.
- **Analytics result:** indicator values and other features, their parameters, warm-up/data-quality status, and links to supporting input data.
- **Evaluation result:** directional bias, actionability, verdict, named gates, reasons, and any evidence-backed candidate levels.
- **Analysis response:** request summary, result, provenance, freshness, and warnings.

Keep provider-specific response shapes inside adapters. The analytics and evaluation engines consume the canonical typed models rather than Kite JSON.

## 5. Analytics and evaluation behavior

### 5.1 Initial deterministic analytics

Start with OHLCV evidence and a small indicator set: SMA, EMA, RSI, and ATR. Each implementation defines its formula, parameters, required warm-up, missing-data behavior, output semantics, and version. Add indicators only when their requirements and correctness checks are clear.

Calculations must be repeatable for the same inputs and configuration. Do not use the LLM to calculate indicator values or prices. Do not use future bars in past calculations.

### 5.2 Evaluation

The evaluation engine consumes analytics outputs and any supported, timestamped market context. Its rules are explicit and versioned. Each gate returns PASS, FAIL, or UNKNOWN with a reason and evidence reference.

Keep directional bias separate from actionability. A bearish view does not automatically imply an actionable short. The verdict may be WAIT or NO_TRADE when data is insufficient, a mandatory gate fails, or the direction is unsupported for the selected segment and horizon.

Do not present an uncalibrated numeric probability or aggregate setup-quality score. Risk/reward and price distances are calculated deterministically from supported levels.

## 6. Sentiment and AI

Sentiment is an additional evidence input, not an untraceable opinion. Each input records its source, timestamp, instrument or market scope, and transformation. Candidate sources and exact sentiment features remain to be selected; do not assume availability or quality before testing them.

Future agents may retrieve and summarize approved information using bounded, read-only tools. Their output must be marked as model-generated and kept distinct from provider data and deterministic calculations. The evaluation workflow may consider this qualitative evidence only through explicit rules; the deterministic engine remains responsible for hard gates. AI output cannot fabricate prices, candles, events, or source claims, and cannot override failed mandatory gates.

The LLM provider/model is undecided. Before sending private report or chat context to an external model, select a provider and review its data-handling terms.

## 7. Persistence, security, and API

Persist the analysis request/settings, normalized candle input, analytics evidence, evaluation result, provenance, and report so that the owner can revisit and explain an earlier result. PostgreSQL is the provisional hosted database. Keep local credentials in .env; do not commit secrets. For hosted operation, store credentials server-side and require authentication and owner-scoped authorization before exposing the application beyond the local machine.

Existing backend endpoints provide health, Kite capabilities, quotes, and candles. The analysis API is planned as POST /api/v1/analyses. Chat endpoints will operate on a report or chat-session identifier and reuse the same application services. Final paths and response schemas are defined with the corresponding implementation tasks.

## 8. Quality requirements

- Never replace missing or failed provider data with fabricated candles.
- Reject or clearly report malformed, stale, incomplete, or insufficient data.
- Keep indicator and evaluation rules deterministic, versioned, and independently testable.
- Include source and as-of timestamps for market and sentiment inputs.
- Test calculations on reviewed real-provider candle samples; use provider-call mocks only to test adapter behavior and failure handling.
- Ensure API errors and logs never expose API keys, access tokens, or secrets.
- Keep provider, analytics, evaluation, and AI responsibilities separate so each can be extended without duplicating the analysis flow.

## 9. Delivery sequence

1. **Market data foundation:** complete the Kite quote and candle API path and verify the required historical intervals with the owner's account.
2. **Deterministic analysis:** add the analytics models and calculations, then the evaluation rules, gates, and analysis API response.
3. **Sentiment and AI:** add selected sentiment inputs and a bounded AI interpretation/report layer; preserve provenance and deterministic gates.
4. **Chat and UI:** add report-scoped chat and build the UI against the stable analysis API.
5. **Private hosted operation:** add authentication, owner-scoped persistence, deployment, monitoring, backups, and restore checks.

Each stage is complete when its contracts and acceptance checks pass. Do not add another provider, indicators, agent framework, or infrastructure without a concrete need.

## 10. Decisions still open

- Exact indicator defaults and the first versioned evaluation rules/gates.
- Which market-sentiment sources and measurable features provide useful, timely data.
- LLM provider/model and allowed agent tools.
- Final UI and hosted deployment choices.
- Persistence and report-retention details for the hosted deployment.
- Supported instrument, segment, horizon, and direction combinations.

## Revision history

| Version | Date | Change |
|---|---|---|
| 0.2 | 7 November 2026 | Owner decisions and independent architecture reviews incorporated. Preserved in [EDD-v0.2.md](EDD-v0.2.md). |
| 0.3 | 7 November 2026 | Replaced the proposed architecture with the agreed module boundaries and data flow; clarified sentiment, AI, and report-scoped chat responsibilities; shortened the design baseline. |

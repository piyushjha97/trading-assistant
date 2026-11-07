# Engineering Design Document (EDD)
## AI-Assisted Indian Equity Market Analysis Platform

- **Document status:** Draft v0.2 — owner decisions incorporated; implementation gates remain open
- **Version:** 0.2
- **Date:** 7 November 2026
- **Basis:** Owner decisions plus independent Codex and Claude reviews of v0.1
- **Decision authority:** Project owner, with review support from the agents

> **Status note:** V0.2 incorporates the owner decisions: hosted deployment, a low-cost market-data provider, both bullish/long and bearish/short analysis (with actionability constrained by segment and horizon), synchronous API execution, and retained historical candle snapshots. Snapshot retention is conditional on explicit provider rights. This document is a design baseline, not permission to bypass provider, security or legal gates. Items not explicitly decided by the owner remain open or are marked as proposed defaults.

---

## 1. Executive summary

The product is a **hosted AI-assisted market-analysis application**, initially focused on Indian listed equities (NSE/BSE). A user configures an instrument, timeframes, indicators and analysis preferences, then requests an on-demand analysis. The application obtains market data from a low-cost external provider, normalizes and validates it, computes quantitative evidence deterministically, asks a configurable LLM to interpret the structured evidence, validates any proposed trade plan with deterministic risk and market-eligibility rules, and presents a report. Users can ask report-scoped follow-up questions through chat, using the same application services as the dashboard.

V1 is an analysis and decision-support product, not an automated trading system. It does not place orders, run scheduled analyses, or claim statistically calibrated probabilities unless calibration has been demonstrated. Both bullish and bearish views are supported. An actionable LONG or SHORT plan is emitted only where the selected instrument, market segment, holding horizon and applicable provider/broker/exchange constraints support it. Otherwise the application may report a bearish/bullish directional bias with `WAIT` or `NO_TRADE` and explain why the bias is not actionable.

The backend is a Python modular monolith using FastAPI and PostgreSQL (provisional). The execution model is synchronous request/response for V1. Use a plain typed Python pipeline; do not add LangGraph, Google ADK, a message broker or a background job system unless later measurements or requirements justify them. The application is hosted, so authentication, authorization, tenant isolation (if more than one user is enabled), encrypted secret handling, secure session management, operational monitoring and deletion controls are release requirements—not optional future hardening.

The owner wants historical charts and retained candle snapshots. The system will therefore support per-analysis normalized candle snapshots, but **only for data sources whose current contracts explicitly permit the required storage, display, processing and retention**. The provider spike must verify those rights before the corresponding snapshot feature is enabled. If a provider does not permit retention, the adapter must enforce a non-retaining mode and the UI must disclose that historical chart replay may be unavailable or may not exactly match the original report. A provider that cannot meet the product's minimum retention requirement may be rejected.

### 1.1 Product goals

1. Provide configurable, evidence-backed technical analysis on demand for Indian equities.
2. Operate as a securely hosted application.
3. Support both bullish/long and bearish/short analysis while separating directional bias from actionability.
4. Separate deterministic market calculations from LLM interpretation.
5. Make market-data and LLM providers replaceable behind stable interfaces.
6. Persist reports, provenance and permitted candle snapshots for historical charts and reproducibility.
7. Provide a dashboard and report-scoped chat over shared application services.
8. Keep V1 achievable as a modular monolith with synchronous execution.

### 1.2 Non-goals for V1

- Placing, modifying or cancelling live orders; brokerage execution integration.
- Scheduled/unattended analysis, streaming alerts or autonomous agents.
- Portfolio management, tax accounting or personalized portfolio-level advice.
- Derivatives as first-class supported instruments unless explicitly added after a separate scope and compliance review. The domain model must not prevent later support.
- A sophisticated backtesting or paper-trading platform.
- A permanent provider-independent market-data warehouse. Retain only bounded per-analysis snapshots where licensed.
- Microservices, message brokers, Kubernetes, distributed workflow engines or background workers without demonstrated need.
- Public multi-user launch until legal/regulatory and data-licensing review is complete.

### 1.3 V1 audience and release posture

The owner has chosen hosted deployment but has not yet specified whether V1 is private for one named owner, shared with invited users, or publicly available. The safe implementation default is **private hosted, single-owner access**. Build authentication and authorization from the beginning; keep tenant ownership fields and query scoping in the data model so invited-user support can be added deliberately. Do not expose public registration or allow cross-user sharing in V1 by default. Any expansion to other users, public access, paid access or marketing requires a separate India-specific legal/regulatory review and provider/LLM contract review before release.

## 2. Confirmed decisions, provisional choices and open questions

### 2.1 Owner-confirmed decisions for v0.2

| Topic | Decision | Design consequence |
|---|---|---|
| Deployment | Hosted | Authentication, secure sessions, backend-only secrets, TLS, authorization, operational monitoring and backup/deletion controls are mandatory for V1. Private single-owner access is the proposed initial release posture; multi-user/public access remains unapproved. |
| Market data | Low-cost provider | Select on total cost, usable history/intervals, reliability, auth burden, data quality and contractual rights. Do not assume a free tier or select a vendor before a hands-on provider spike. |
| Direction handling | Both LONG and SHORT | Preserve bullish/bearish analysis in all supported contexts; emit actionable plans only when segment × horizon × direction policy permits. Unsupported bearish cases become non-actionable bias plus WAIT/NO_TRADE, not a fabricated SHORT plan. |
| API lifecycle | Synchronous | `POST /analyses` completes the analysis and returns the report in the same request. Bound workload and timeouts; no queue or job lifecycle in V1. |
| Charts and retention | Retain snapshots | Persist the normalized candle window used by each report when provider terms explicitly permit it. Snapshot retention, display and deletion rules are provider-specific and enforced by policy. |

### 2.2 Agreed architectural direction and review outcomes

| Topic | v0.2 direction |
|---|---|
| Initial market | NSE/BSE listed equities; segment-specific support matrix |
| Backend | Python + FastAPI (provisional) |
| Architecture | Modular monolith; no premature microservices |
| Workflow | Plain typed Python pipeline; no LangGraph/ADK in V1 |
| Persistence | PostgreSQL (provisional), including reports, evidence, provenance and permitted per-analysis candle snapshots |
| Quantitative calculations | Deterministic, independently tested code |
| LLM role | Interpret structured evidence; never calculate raw indicators or bypass validators |
| Chat | Report-scoped; shared application services; no autonomous tools or persistent agent memory |
| Execution | On-demand only; synchronous request/response; no order placement |
| Confidence | No uncalibrated numeric probability; remove scalar setup-quality score from V1 acceptance criteria |

### 2.3 Provisional technical choices to validate

- FastAPI, Pydantic, SQLAlchemy (or an alternative data-access approach), PostgreSQL.
- React + TypeScript frontend.
- Docker/container-based deployment to a cloud provider selected separately; no cloud vendor is committed by this EDD.
- `uv` for Python dependency and environment management.
- Pandas/NumPy plus a small, tested set of deterministic indicator implementations. Review maintenance, compatibility, license and numerical correctness before selection.
- One market-data provider for V1, selected after the provider spike. Candidate vendors previously discussed include Angel One SmartAPI, Upstox and TejHQ; none is selected or assumed to satisfy cost, entitlement, retention or display requirements.
- One LLM provider/model initially, behind a provider-neutral interface.

### 2.4 Deferred or unresolved decisions

- Exact market-data provider, plan, price, entitlements, rate limits, intervals, historical depth and storage/display rights.
- Hosting vendor, region, deployment topology, backup policy and operational budget.
- Whether V1 remains single-owner or expands to invited users; public registration is out of scope until approved.
- Exact supported segment × horizon × direction matrix and evidence that a short position is actionable for each combination.
- Whether derivatives should be added in a later version.
- Exact candle snapshot retention period, storage format and deletion schedule, to be set from provider contracts and privacy requirements.
- LLM provider and its prompt/data retention/training terms.
- Whether the next validation stage is historical backtesting or paper trading.
- Caching, a second provider, queues, background workers, streaming and scheduled analysis.

### 2.5 Implementation gates

Do not begin production provider integration or enable candle snapshot retention until the provider spike records, in an ADR, the selected API/product, account eligibility, pricing, actual interval/lookback coverage, sample data quality, authentication flow, rate limits, usage/display/storage/retention/deletion rights and credential-handling model. Do not expose trade-like outputs beyond the private owner-only deployment posture until the relevant legal/regulatory review is complete. These are gates, not assumptions that can be satisfied by adding a disclaimer.

## 3. Users and principal workflows

### 3.1 Primary user

An individual user who selects Indian equity instruments and configures technical-analysis preferences. The initial product may be single-user, but avoid design choices that make later multi-user support unnecessarily difficult.

### 3.2 Dashboard analysis workflow

1. User selects exchange and instrument.
2. User selects one or more timeframes and lookback windows.
3. User selects indicators and configures their parameters.
4. User selects analysis preferences: horizon, direction, strategy, risk constraints and analysis depth.
5. User chooses an AI provider/model from configured options (where enabled).
6. User submits an on-demand analysis request.
7. Backend validates the request and resolves the instrument.
8. Market-data adapter fetches required candles.
9. Data normalizer maps provider output to canonical candles.
10. Validation checks timestamps, OHLC consistency, duplicates, gaps, incomplete candles and session rules.
11. Quantitative engine computes indicators, patterns, market structure and per-timeframe evidence.
12. Synthesis layer creates a compact, typed evidence package.
13. LLM produces a structured interpretation and proposed scenario/trade plan.
14. Deterministic risk validator checks the proposal and may reject, downgrade or constrain it.
15. Report, evidence, provenance and any permitted candle snapshot are persisted; the synchronous response returns the completed report.
16. UI renders verdict, evidence, charts/tables, risks, invalidation and caveats.

### 3.3 Chat workflow

- User asks a question about an instrument, report or market setup.
- Chat resolves the relevant instrument and/or analysis context.
- It invokes the same application services used by dashboard analysis.
- It may request a new analysis when appropriate, but must not implement a second, divergent analysis engine.
- It must distinguish retrieved facts, computed evidence and LLM interpretation.
- It should cite or link to the relevant saved report and expose the timestamp/data freshness.
- Chat must not turn an informational response into an order or execution action.

---

## 4. Functional requirements

### 4.1 Instrument selection

- Support NSE and BSE equities initially.
- Search/select instruments by symbol and display name.
- Resolve symbols to canonical internal instrument identifiers; do not rely on ambiguous ticker strings alone.
- Maintain exchange, trading symbol, display name, instrument type, currency, tick size and lot/quantity metadata where available.
- Handle symbol changes, suspended instruments and delisted instruments as data-quality cases.
- Keep instrument types extensible for indices, ETFs, futures and options later.

### 4.2 Timeframes and candle settings

- Timeframes must be configurable, not hardcoded into analysis logic.
- Candidate initial intervals: 1m, 3m, 5m, 10m, 15m, 30m, 1h, 4h, 1d and 1w, but actual availability depends on provider capability and aggregation quality.
- User can choose primary and supporting timeframes.
- User can choose lookback periods appropriate to each timeframe.
- Distinguish closed candles from the currently forming candle. Default analysis should use closed candles unless the user explicitly opts into live/incomplete data.
- If a requested timeframe is not supplied by a provider, aggregate from a smaller supported base interval only when session alignment and completeness can be guaranteed.
- Never silently treat a partial candle as complete.

### 4.3 Indicator and analysis catalog

The UI should present categorized indicators with configurable parameters. Initial candidates:

- **Trend:** SMA, EMA, WMA, VWMA, Supertrend, ADX.
- **Momentum:** RSI, MACD, Stochastic, CCI, ROC, Williams %R.
- **Volatility:** Bollinger Bands, ATR, Keltner Channels, Donchian Channels.
- **Volume:** OBV, VWAP, MFI, CMF, Volume Profile (only if data granularity supports it).
- **Market structure:** higher highs/lows, lower highs/lows, support/resistance, break of structure (BOS), change of character (CHOCH).
- **Price action:** engulfing, doji, hammer, shooting star, pin bar and other explicitly defined patterns.
- **Other:** Fibonacci levels, pivot points, Ichimoku.

Requirements:
- Indicator definitions and parameters must be versioned.
- Each indicator implementation must document inputs, warm-up requirements, output semantics and edge cases.
- Avoid duplicate/conflicting calculations from different libraries.
- Indicator selection should not imply that every indicator has equal weight.
- A default profile should be available, but users can configure and save profiles.

### 4.4 Analysis preferences

Candidate configuration controls:
- Trading horizon: intraday, swing, positional.
- Preferred direction: long, short, both.
- Strategy family: trend-following, reversal, breakout, momentum, or all.
- Risk profile and minimum risk/reward ratio.
- Maximum risk per trade only if the user supplies an explicit risk budget; otherwise report price-distance/R:R geometry without implying portfolio sizing.
- Analysis depth: quick, standard, deep (bounded by synchronous request budget).
- Include alternative scenarios.
- Include/exclude supported indicators.
- Custom instructions, bounded by system policy, schema and evidence constraints.

V1 must not expose an arbitrary minimum setup-quality score. Instead, show a checklist of named gates (for example: data quality, higher-timeframe alignment, primary-timeframe trigger, liquidity/volume sufficiency, risk/reward, stop-distance sanity and short eligibility). Each gate is `PASS`, `FAIL` or `UNKNOWN` with a reason. A trade plan is not actionable if a mandatory gate fails or is unknown. The list and rules are versioned. A simple passed/total count may be displayed as a checklist summary, not as a probability or a weighted score.

### 4.5 AI settings

- Provider/model selection is configurable by the server operator; user-level model selection may be deferred.
- Provider/model changes must not require changes to quantitative or market-data modules.
- Store provider, model identifier, prompt/template version and relevant generation parameters with each report.
- Model-generated confidence must not be presented as a calibrated probability.
- V1 does not ship a scalar setup-quality score or a numeric score threshold. It uses a versioned deterministic gate checklist.
- A calibrated probability may be introduced only after outcome labels, adequate sample size, leakage controls, calibration analysis and out-of-sample validation. Qualitative LLM assessment remains explicitly non-probabilistic.
- Verify the LLM provider's data retention, training, regional processing and deletion terms before sending user-specific report context.

### 4.6 Analysis report

A report should include:
- Instrument, listing/exchange, segment and analysis timestamp.
- Data timestamp, freshness, source/provider and adjustment basis.
- Selected timeframes, lookback and configuration snapshot.
- **Directional bias:** bullish, bearish, neutral or mixed.
- **Actionability:** actionable, informational-only or blocked, with reason.
- **Verdict:** LONG, SHORT, WAIT or NO_TRADE. A directional bias does not force an actionable trade.
- Trading style/horizon and the segment/horizon policy decision.
- Thesis, supporting evidence and contradicting evidence.
- Entry zone, stop/invalidation and targets only when supported; otherwise explicit no-plan reason.
- Deterministically calculated risk/reward and relevant assumptions.
- Per-timeframe findings, conflicts and key indicator values.
- Risks, limitations, alternative scenarios and data-quality warnings.
- Named gate checklist with pass/fail/unknown reasons.
- Snapshot availability and retention status; link to the exact saved chart window when permitted.
- Model/provider/prompt metadata and deterministic validator outcome/diffs.

A report must be allowed to conclude WAIT or NO_TRADE. No trade plan may be fabricated to satisfy a requested direction.

## 5. Non-functional requirements

### 5.1 Correctness and safety

- No fabricated candle data or indicator values.
- No analysis from stale, incomplete or invalid data without an explicit warning and policy.
- No lookahead leakage in indicator/pattern calculations or any later evaluation.
- No LLM-created price levels accepted without deterministic validation.
- No claims of guaranteed returns or calibrated probability without evidence.
- Clear separation of market facts, computed metrics and model interpretation.

### 5.2 Maintainability and extensibility

- Modular monolith with explicit module boundaries.
- Provider adapters behind protocols/interfaces.
- Typed request/response/data contracts.
- Deterministic components independently unit-testable.
- Keep framework-specific orchestration code out of core domain logic.
- Add new providers, indicators and models without rewriting unrelated modules.

### 5.3 Performance and resilience

- Set measurable latency targets after benchmarking real provider and model calls.
- Apply timeouts, bounded retries and backoff to external providers.
- Respect provider rate limits and quotas.
- Avoid retrying non-idempotent operations blindly.
- Return partial-failure information where a timeframe/provider fails; do not silently omit it.
- Add request IDs and structured logs.
- Caching is optional and deferred; if added, define freshness and invalidation semantics.

### 5.4 Observability

- Structured application logs.
- Correlation/request ID across API, provider, analysis and LLM calls.
- Metrics for provider latency/failures, model latency/token usage/cost, analysis duration and validation failures.
- Persist enough diagnostic metadata to investigate a report without storing unnecessary secrets or full sensitive provider payloads.

---

## 6. Proposed high-level architecture

### 6.1 Logical components

1. **Frontend:** dashboard, configuration, chart/report views and report-scoped chat.
2. **API/security layer:** FastAPI routes, authentication, authorization, secure session handling, request validation and response serialization.
3. **Application services:** `CreateAnalysis`, `GetReport`, `AskReportQuestion`.
4. **Instrument catalog:** canonical security/listing identity, alias history and provider instrument mapping.
5. **Market-data domain:** provider interface, adapter, normalizer, validator, calendar/session alignment and aggregation.
6. **Quantitative analysis:** small indicator set, patterns/structure selected for V1, multi-timeframe evidence and gate checklist.
7. **AI reasoning:** provider-neutral LLM interface, evidence-only prompt construction and structured output parsing.
8. **Eligibility and risk validation:** deterministic direction × segment × horizon eligibility, trade geometry, tick-size and evidence-reference checks.
9. **Analysis pipeline:** plain typed Python stage functions with explicit `RunContext`; no graph/agent framework in V1.
10. **Persistence:** repositories for requests, reports, evidence, provenance, permitted candle snapshots, profiles and chat.
11. **Hosted operations:** secret management, TLS termination, database/storage encryption, backups, monitoring, rate/cost controls and deletion workflows.

### 6.2 Synchronous request flow

```text
Browser (authenticated session)
      |
      v
TLS / hosted ingress
      |
      v
FastAPI authentication + authorization
      |
      v
CreateAnalysis application service
      |
      +---- Resolve canonical instrument/listing
      +---- Preflight provider capabilities, entitlement and request budget
      |
      v
Typed AnalysisPipeline (same process)
      |
      +---- Fetch provider data -> normalize -> calendar/session validation
      +---- Persist permitted normalized candle snapshot + provenance
      +---- Compute deterministic indicators/evidence/gates
      +---- LLM reasoning over structured evidence
      +---- Direction/segment/horizon + deterministic risk validation
      |
      v
Persist report/evidence/model metadata/validator result
      |
      v
Synchronous HTTP response -> dashboard / report-scoped chat
```

### 6.3 Architectural constraints

- The pipeline is a normal typed Python call chain; each stage has explicit input/output contracts and can be unit-tested independently.
- `RunContext` carries `as_of`, correlation ID, authenticated owner/tenant ID, request budget, provider policy and stage timings.
- Per-timeframe computations may use bounded concurrency, but provider rate limits remain enforced per credential.
- Data-quality or entitlement failure short-circuits before LLM invocation.
- Core domain/application code must not depend on FastAPI, a specific provider, LLM SDK or orchestration framework.
- Synchronous execution is intentional for V1. Keep the pipeline boundary clean so a future job runner can invoke it, but do not implement async job lifecycle or queue infrastructure now.

## 7. Market-data architecture

### 7.1 Provider abstraction

Define a provider-neutral contract, for example:

```python
from datetime import datetime
from typing import Protocol, Sequence

class MarketDataProvider(Protocol):
    async def get_candles(
        self,
        instrument: "Instrument",
        timeframe: "Timeframe",
        start: datetime,
        end: datetime,
    ) -> Sequence["Candle"]:
        ...

    async def get_capabilities(self) -> "ProviderCapabilities":
        ...
```

The final interface may differ after review. It should support:
- Instrument lookup/resolution or a separate instrument master service.
- Historical candle retrieval.
- Provider capability discovery.
- Rate-limit and entitlement errors.
- Data-source metadata and request identifiers.
- Explicit distinction between unsupported interval, no data, authentication failure, throttling and provider outage.

Potential adapters (not committed; verify all claims against current official documentation and contract terms):
- Angel One SmartAPI.
- Upstox.
- TejHQ (potentially more suitable for EOD data depending on current product terms/capabilities).
- Other providers after official documentation and terms review.

### 7.2 Provider capability model

Represent, where discoverable:
- Exchanges and instrument types.
- Supported intervals.
- Maximum historical lookback.
- Whether volume and open interest are supplied.
- Whether data is delayed, real-time or end-of-day.
- Authentication and token-renewal requirements.
- Rate limits/quotas.
- Entitlement and account requirements.
- Known session/adjustment semantics.
- Usage, storage and redistribution restrictions.

Do not assume all providers have equivalent data quality or rights.

### 7.3 Canonical data model

The final schema must preserve source semantics rather than erase provider differences. At minimum, a normalized candle/batch must carry:
- Canonical `listing_id`, exchange, segment and instrument identity.
- Timeframe and explicit `bar_start_at` / `bar_end_at` in UTC, plus exchange timezone (`Asia/Kolkata`) and original provider timestamp/convention.
- OHLC values represented with a documented exact source representation (raw decimal text or scaled integer/tick representation) and a documented calculation representation. Avoid uncontrolled float round-tripping; round only for display using instrument tick size.
- Volume with provider-defined units/semantics; do not assume all providers mean the same thing.
- `is_complete`, `is_partial_session_bar`, `published_at`/provider availability where available, retrieval timestamp and provider batch ID.
- Adjustment basis (`unadjusted`, `split_adjusted`, `corporate_action_adjusted`, `unknown`) and adjustment as-of/version where supplied.
- Source provider, provider instrument key and mapping version.

Illustrative shape (not final code):

```python
class Candle(BaseModel):
    listing_id: str
    timeframe: str
    bar_start_at: datetime  # UTC
    bar_end_at: datetime    # UTC
    open_raw: str
    high_raw: str
    low_raw: str
    close_raw: str
    volume: int | None
    is_complete: bool
    is_partial_session_bar: bool
    adjustment_basis: str
    source_provider: str
    provider_batch_id: str
```

The numeric calculation layer converts raw values through a single documented conversion path and explicit tolerance rules. Store instrument tick size and price scale effective at the analysis time. `Security`, `Listing` and `ProviderInstrumentMap` are separate concepts; symbol/identifier mappings are effective-dated. ISIN may be an attribute but must not be the sole identity key.

### 7.3.1 Candle boundary and as-of policy

- Use one `as_of` instant per analysis run.
- Timeframes are session-anchored to the applicable exchange calendar, not arbitrary wall-clock multiples.
- Every candle has explicit start/end boundaries. Provider timestamp conventions are mapped and original values retained for diagnostics.
- A candle is eligible for closed-candle analysis only if provider completion evidence and the configured latency buffer show it was available by `as_of`; nominal wall-clock boundary alone is insufficient.
- Opening/closing partial intervals are represented explicitly and are not silently merged into full-length bars.
- NSE and BSE calendars are independent, versioned inputs. Special sessions, holidays, auctions and exceptional trading days must be represented. Calendar source and version are recorded on each report.
- Daily/weekly candles follow a documented exchange-session convention; do not assume a daily candle is complete solely because the local date changed.

### 7.3.2 Corporate actions

Each analysis must use a single explicit adjustment basis across all selected timeframes. Record provider adjustment semantics, adjustment as-of time/version and any known corporate actions affecting the lookback. Never mix adjusted and unadjusted candles in one calculation. If the provider cannot establish a trustworthy basis for an affected window, mark the data quality as degraded or fail the affected analysis; suppress price levels/indicators that would be misleading. Preserve the exact normalized input snapshot where permitted.

### 7.4 Data normalization and validation

Validation should cover:
- Timestamp parsing and timezone normalization.
- Duplicate candles and out-of-order records.
- OHLC invariants (`high >= max(open, close)`, `low <= min(open, close)`, `high >= low`).
- Negative or implausible prices/volume.
- Missing intervals and market-session gaps.
- Partial/current candle detection.
- Provider pagination and truncation.
- Corporate-action effects, where applicable.
- Empty responses and provider inconsistencies.

Indian equity session rules must be exchange-calendar aware, not hardcoded as a simple weekday/time check. Normal NSE equity trading is commonly 09:15–15:30 IST, but holidays, special sessions, auctions and changes must be handled through a maintained calendar/source. Verify the exact rules and data-provider semantics before implementation.

### 7.5 Candle aggregation

If the provider lacks a requested timeframe:
- Aggregate only from a smaller interval with sufficient coverage.
- Align boundaries to exchange sessions and the intended timeframe convention.
- Define treatment of opening/closing partial intervals.
- Preserve volume aggregation semantics.
- Do not aggregate across sessions unless the timeframe definition explicitly requires it.
- Mark incomplete aggregates.
- Test daylight/timezone and holiday boundaries even if the exchange currently uses IST.

### 7.6 Data retention, snapshots and caching

The owner has selected candle snapshots for historical charts and analysis reproducibility. V1 therefore defines two persistence tiers:

- **Tier A — always required:** immutable analysis request/configuration snapshot; exact typed evidence package supplied to the LLM; prompt/template version and rendered prompt where lawful; raw structured LLM response; validator findings and any deterministic downgrade/diff; provider, retrieval time, requested/actual range, candle counts, quality summary, adjustment basis, calendar version, content hash; engine/indicator/catalog versions; model/provider metadata and stage timings.
- **Tier B — candle snapshot, rights-gated:** the compact normalized candle window actually used for calculations and chart display, per listing/timeframe, stored per analysis rather than as an unrestricted market-data warehouse. Store snapshot schema/version, checksum, provider rights/policy ID, retention expiry and deletion status. Prefer compressed columnar/object storage for larger payloads, with PostgreSQL metadata and access control.

**Hard gate:** do not persist, display historically, export, or send snapshots to another service unless the selected provider's current contract and plan permit that specific use. Verify rights for storage duration, chart display, derived data, backups, user access, third-party LLM processing (where relevant), deletion and post-termination retention. If only short retention is permitted, enforce TTL deletion. If retention is prohibited, disable Tier B for that provider and clearly mark historical chart replay as unavailable; the provider may be rejected if this fails the product requirement.

Snapshots are immutable per report. A new provider fetch creates a new snapshot/version; it must not silently replace the data associated with an old report. Recompute/replay must reference the original snapshot and versioned calculation code. A hash alone is not a substitute for a snapshot.

Caching is deferred. If introduced later, cache entries must be scoped by provider/account entitlement, instrument, interval, adjustment basis, session/calendar version and freshness policy; cached data inherits the same provider usage restrictions and expiry.

## 8. Quantitative analysis engine

### 8.1 Principles

- All numerical indicator and risk calculations occur in deterministic code.
- LLM receives structured results, not responsibility for calculating RSI, ATR, MACD or price levels from raw candles.
- Each calculation must be independently testable against known fixtures/reference implementations.
- Store indicator configuration and implementation version with the report. Persist the normalized candle snapshot used by the run when licensed.
- Avoid lookahead: a calculation at time `t` may only use information available at or before `t`.
- Define warm-up periods, missing-data behavior and NaN handling explicitly.

### 8.2 Suggested internal layers

- `indicators/`: pure indicator functions and typed output.
- `patterns/`: explicit pattern definitions and detection.
- `market_structure/`: swings, support/resistance, BOS/CHOCH, regime features.
- `timeframes/`: timeframe-specific calculation and alignment.
- `synthesis/`: compare signals and conflicts across timeframes.
- `gates/`: deterministic, versioned eligibility and setup checklist; no scalar score in V1.
- `risk/`: deterministic trade geometry and risk/reward calculations.

### 8.3 Multi-timeframe synthesis

- Compute evidence independently per timeframe.
- Align observations to a common analysis timestamp.
- Distinguish closed higher-timeframe candles from partial higher-timeframe candles.
- Report conflicts rather than hiding them.
- Define explicit rules for timeframe hierarchy and signal weighting.
- Avoid arbitrary indicator voting or double-counting correlated indicators.
- Preserve both supporting and contradictory evidence.

### 8.4 Indicator correctness

For each indicator, specify formula/reference, parameters/defaults, input timeframe/history, warm-up, output scale, edge cases, missing values, unit tests and version ID. V1 should deliberately narrow the catalog to a small set proven against the selected provider's real candles. Proposed starting set: OHLCV evidence, SMA/EMA, RSI and ATR; add MACD or VWAP only if provider interval/volume semantics and test coverage justify them. Defer the broad catalog in v0.1 until after the first end-to-end pipeline works.

## 9. AI reasoning and orchestration

### 9.1 LLM responsibilities

The LLM may:
- Interpret structured quantitative findings.
- Explain agreement/conflict across timeframes.
- Describe plausible bullish, bearish and neutral scenarios.
- Identify missing evidence and risks.
- Formulate a conditional thesis and candidate levels when supported by supplied data.
- Explain why WAIT or NO_TRADE is appropriate.
- Answer follow-up questions grounded in the report and its evidence.

The LLM must not:
- Invent prices, candle values, indicator values or market events.
- Claim a probability that has not been calibrated.
- Override data-quality failures or deterministic risk constraints.
- Place orders.
- Treat natural-language user instructions as permission to bypass validation or safety controls.

### 9.2 Provider-neutral interface

Illustrative contract:

```python
class TradingReasoningProvider(Protocol):
    async def analyze(
        self,
        context: "TradingAnalysisContext",
    ) -> "TradingAnalysis":
        ...
```

Implement provider adapters behind a factory/registry. The application should record model/provider identifiers and generation metadata. Avoid leaking provider-specific request/response objects into domain modules.

### 9.3 Structured output

Use a typed schema (for example Pydantic) with:
- Instrument and analysis reference.
- Verdict, directional bias and actionability (with reason).
- Horizon/trading style and segment/horizon eligibility decision.
- Thesis.
- Entry zone (optional).
- Stop/invalidation (optional).
- Targets (optional list).
- Supporting and contradicting evidence IDs.
- Risks and alternative scenarios.
- Explanation and assumptions.
- Qualitative LLM assessment.
- Selected candidate price-level IDs and evidence references only.
- Named gate checklist with gate IDs, status and reasons.

Parsing failures should have bounded repair/retry behavior. A malformed model response must not be rendered as a valid trade plan.

### 9.4 Confidence and setup gates

V1 does not expose an aggregate numeric setup-quality score or a user-configurable score threshold. Instead, a deterministic, versioned checklist reports named gates as `PASS`, `FAIL` or `UNKNOWN`, each with evidence references and a reason. Mandatory gates include clean/eligible data, sufficient indicator warm-up, supported direction × segment × horizon, no unresolved critical timeframe conflict, liquidity/volume sufficiency where measurable, stop-distance sanity and minimum requested risk/reward. The application may show `x of y gates passed` as a checklist count, but must not call it confidence or probability.

LLM qualitative assessment is explanatory only. Calibrated probability is deferred until a statistically defensible labeled dataset, chronological out-of-sample evaluation, calibration analysis and monitoring exist. No 90/95/99% threshold is exposed in V1.

### 9.5 Orchestration: plain typed Python pipeline

V1 uses ordinary typed Python stage functions coordinated by an `AnalysisPipeline` / application service. The workflow is predominantly linear: resolve instrument, preflight capability, fetch, normalize/validate, compute evidence, invoke one LLM, validate, persist. This does not justify LangGraph or Google ADK in the initial release.

Use explicit stage inputs/outputs, a `RunContext` (`as_of`, request/owner IDs, correlation ID, deadline/budget, provider policy) and per-stage timing/outcome records. Parallelize independent timeframe computations only where bounded and safe. Add a durable workflow engine only if future requirements demonstrate human approval, durable checkpoints, complex branching, long-running jobs or multi-agent routing that cannot be handled cleanly by the pipeline.

### 9.6 Model evaluation

Benchmark candidate models using the same fixed cases and prompts. Evaluate:
- Schema compliance.
- Evidence-grounded reasoning.
- Multi-timeframe consistency.
- Correct use of supporting/contradictory evidence.
- Invalid or invented price levels.
- Appropriate WAIT/NO_TRADE behavior.
- Risk/reward correctness (with deterministic validator as final authority).
- Hallucination rate.
- Repeatability/variance.
- Latency, token usage and cost.

Build a versioned evaluation set. Avoid selecting a model based solely on generic benchmarks or a few anecdotal examples. Future outcome-based evaluation must use chronological train/validation/test splits and guard against lookahead and survivorship bias.

---

## 10. Direction eligibility and deterministic risk validation

The validator is a hard boundary between model output and user-visible trade plans. It performs two distinct checks: (1) whether the requested direction is actionable for this instrument/segment/horizon, and (2) whether the proposed levels are geometrically and evidentially valid.

### 10.1 Direction × segment × horizon policy

Represent eligibility as a versioned policy table, not scattered `if` statements. Conceptual dimensions: exchange, instrument type, segment/product, direction, holding horizon, and where required the provider/broker capability and applicable rules. Each combination returns one of:
- `ACTIONABLE`: the app may produce a conditional plan if evidence and risk gates pass.
- `BIAS_ONLY`: bullish/bearish analysis is allowed, but no actionable plan is emitted.
- `UNSUPPORTED`: reject the requested action or return a clear unsupported result.

For V1, cash-equity SHORT must not be assumed actionable for swing or positional holding. Intraday short may be considered only after the exact segment, broker/product access and applicable rules are verified. Where no valid short route exists, preserve `directional_bias=BEARISH`, set `actionability=BIAS_ONLY`, and return `WAIT` or `NO_TRADE` with a reason such as `short_not_actionable_for_segment_horizon`. Do not imply that a bearish view authorizes borrowing, delivery shorting or order execution. Derivatives are not automatically included merely because they could enable bearish exposure; they require separate scope, data and compliance approval.

LONG eligibility is also subject to instrument status, segment and data availability. The policy table and its source/version are persisted with each report. Legal/regulatory applicability and broker permissions must be verified before enabling a combination.

### 10.2 Price-plan validation

Checks include:
- Entry, stop and targets are numeric, finite, within plausible instrument bounds and aligned to tick-size rules.
- LONG: stop below entry; targets above entry. SHORT: stop above entry; targets below entry.
- Risk distance is non-zero; reward/risk is calculated by deterministic code.
- Targets/stops are ordered consistently and reference supplied candidate-level/evidence IDs.
- Every price level is selected from deterministic candidate levels supplied to the LLM or otherwise supported by explicit evidence. Prefer LLM selection among candidate IDs rather than free-form price invention.
- No level is accepted if it contradicts the data snapshot/current close without an explicit, validated rationale.
- Requested minimum R:R is satisfied or plan is downgraded to WAIT/NO_TRADE.
- No actionable plan is emitted when required data is stale, incomplete, invalid, insufficient or direction-ineligible.
- Validator output is structured: `ACCEPTED`, `DOWNGRADED`, `REJECTED`; record every finding and any deterministic change.

No execution occurs in V1. These checks validate an analytical scenario, not order placement, guaranteed fills or broker-specific execution behavior.

## 11. Persistence and data model

PostgreSQL is the provisional relational store. A separate object-storage bucket may hold compressed candle snapshots if the selected host and provider contract permit it. Object access must be private and owner-scoped; do not expose bucket URLs publicly.

### 11.1 Candidate entities

- `user` / `identity`: authenticated owner identity.
- `instrument_security`: canonical security identity and issuer-level metadata.
- `instrument_listing`: exchange, segment/series, symbol, tick size, currency, status and effective dates.
- `instrument_alias`: symbol/name history with valid-from/to timestamps.
- `provider_instrument_map`: provider-specific instrument key and mapping version/effective dates.
- `analysis_profile`: saved configuration and owner ID.
- `analysis_request` / `analysis_run`: request/config snapshot, owner ID, status/result, start/end, correlation ID and stage timings. In V1, run lifecycle is completed within one synchronous HTTP request; persistence may still record `RUNNING` during execution for diagnostics, but there is no public polling/job API.
- `data_provenance`: provider, plan/entitlement, retrieval time, requested/actual range, counts, quality summary, adjustment basis, calendar version, content hash and rights-policy ID.
- `candle_snapshot`: snapshot metadata, storage pointer or inline payload, schema/version, checksum, expiry and deletion status.
- `analysis_evidence`: typed per-timeframe findings, candidate price levels and gate outcomes.
- `analysis_report`: directional bias, actionability, verdict, thesis, plan, explanation and validation status.
- `model_invocation`: provider/model, prompt version, generation parameters, token/cost/latency metadata and structured response.
- `chat_session` / `chat_message`: report-scoped conversation, owner ID and report references.
- `retention_policy` / `deletion_audit`: provider rights, expiry and verified deletion records.

### 11.2 Persistence and tenancy principles

- Every user-owned row is scoped to an owner/tenant ID; every read/write query enforces that scope server-side.
- V1 may expose only one owner, but identity and ownership checks are still required for hosted deployment.
- Save immutable configuration, evidence, prompt/model metadata and validator findings with each report.
- Save the normalized candle snapshot used for each report only when permitted. Snapshot access, export, backup and deletion obey the same rights policy.
- Do not store API secrets in report tables or logs. Store references to secret-manager entries, not secret values.
- Define retention and deletion for reports, chat, prompts, snapshots, backups and user credentials. A deletion request must cascade or tombstone related objects according to law/contract and leave only the minimum audit record permitted.
- Use migrations, schema versioning, database encryption at rest and encrypted backups.

### 11.3 Reproducibility levels

- **Auditability (mandatory):** reconstruct what configuration, evidence, model/prompt, provider metadata, validator and policy versions were used.
- **Computational replay (target where permitted):** rerun deterministic calculations from the exact normalized candle snapshot and versioned engine.
- **LLM text replay (best effort only):** the same model/prompt may produce different prose over time; persist the original structured response and generation metadata. Do not promise bit-for-bit generation replay.

A content hash detects changes but cannot reconstruct input data. If provider terms prohibit snapshots, retain Tier A only and explicitly downgrade the historical chart/replay promise for that provider.

## 12. API design (synchronous V1)

All routes require an authenticated session. Use owner-scoped authorization for every resource. Exact payloads remain subject to OpenAPI/schema finalization.

| Method | Endpoint | Purpose |
|---|---|---|
| GET | `/api/v1/instruments` | Search supported instruments/listings |
| GET | `/api/v1/instruments/{listing_id}` | Listing details |
| GET | `/api/v1/market-data/capabilities` | Current provider/plan capability summary |
| GET | `/api/v1/indicators` | Supported indicator catalog and parameter schemas |
| GET | `/api/v1/analysis-profiles` | List owner profiles |
| POST | `/api/v1/analysis-profiles` | Create/update a profile |
| POST | `/api/v1/analyses` | Execute analysis synchronously and return completed report |
| GET | `/api/v1/reports/{report_id}` | Retrieve owner-scoped saved report |
| GET | `/api/v1/reports/{report_id}/candles` | Retrieve permitted retained chart snapshot |
| POST | `/api/v1/chat/sessions` | Create report-scoped chat session |
| POST | `/api/v1/chat/sessions/{session_id}/messages` | Ask a report-grounded question synchronously |

### 12.1 Synchronous lifecycle and limits

- `POST /analyses` does not return `202 Accepted` or a job ID for later polling in V1. It returns the completed report on success.
- The server enforces request deadlines, provider/LLM timeouts, maximum lookback, maximum intervals, indicator count, bounded parallelism and an overall cost budget.
- If a request cannot complete within the configured synchronous budget, return a typed timeout/degraded error with a correlation ID. Do not silently continue as a background task.
- Use an `Idempotency-Key` for client retries. Persist request identity so a retried request does not accidentally trigger duplicate paid LLM calls; define replay behavior and expiration.
- Retry only transient, idempotent provider reads, respecting `Retry-After`; do not retry auth, entitlement, invalid request or no-data errors. Bound retries and total time.
- Return clear typed errors for unsupported interval/lookback, entitlement failure, rate limit, provider outage, invalid/stale data, model failure and internal validation failure.
- A future async job API may be added if real latency/timeout measurements justify it; it is not part of V1.

### 12.2 Analysis request example

```json
{
  "listing_id": "opaque-listing-id",
  "timeframes": [
    {"interval": "15m", "lookback": "20d", "role": "primary"},
    {"interval": "1h", "lookback": "60d", "role": "confirmation"},
    {"interval": "1d", "lookback": "1y", "role": "context"}
  ],
  "indicators": [
    {"name": "rsi", "parameters": {"period": 14}},
    {"name": "ema", "parameters": {"period": 20}},
    {"name": "atr", "parameters": {"period": 14}}
  ],
  "preferences": {
    "horizon": "intraday",
    "direction": "both",
    "strategy": "all",
    "minimum_risk_reward": 2.0,
    "analysis_depth": "standard",
    "include_alternative_scenarios": true
  },
  "data_policy": {
    "use_closed_candles_only": true,
    "require_snapshot_if_permitted": true
  }
}
```

The API must not accept a free-form scalar confidence/setup-quality threshold in V1. Units, enums, lookback semantics, adjustment mode, defaults and validation rules must be finalized before implementation.

## 13. Frontend design

React + TypeScript is proposed, subject to review.

### 13.1 Main screens

1. **Analysis dashboard**
   - Instrument search and selection.
   - Exchange and instrument type.
   - Timeframe selection.
   - Lookback selection.
   - Indicator catalog and parameter controls.
   - Analysis preferences and AI settings.
   - Run analysis action.

2. **Analysis report**
   - Verdict and timestamp.
   - Data freshness/source and warnings.
   - Multi-timeframe summary.
   - Charts and indicator overlays where supported.
   - Supporting/contradictory evidence.
   - Entry/stop/targets and deterministic risk/reward.
   - Risks, invalidation and alternative scenarios.
   - Model and validation metadata.

3. **Analysis history**
   - Search/filter past analyses.
   - Compare reports/configurations where useful.

4. **Chat**
   - Ask questions about current or saved reports.
   - Clearly indicate which report/data timestamp is being discussed.
- Restrict session and report access to the authenticated owner; no free-running tools or autonomous trading actions.
   - Invoke shared backend application services.

5. **Settings**
   - Operator-managed market-data provider status/capabilities (not raw secret display).
   - LLM provider/model status and safe configuration.
   - Saved analysis profiles.
   - Account/session and data-retention information. Credential entry is disabled unless a provider-specific security design explicitly approves it.

### 13.2 UX constraints

- Do not overload users with every possible indicator by default; categorize and provide sensible presets.
- Show data-quality warnings prominently.
- Explain WAIT/NO_TRADE rather than treating it as a failure.
- Distinguish calculated metrics from model-generated narrative.
- Do not imply that a visually polished score is a statistically validated probability.

---

## 14. Hosted security, privacy and compliance gates

Hosted deployment materially changes the threat model. The minimum V1 controls are:

### 14.1 Identity, access and tenant isolation

- Require authentication for every application route except explicitly public health/readiness endpoints.
- Use a managed identity provider or a well-maintained authentication implementation; prefer secure, HTTP-only, SameSite cookies for browser sessions where applicable.
- Enforce authorization and owner/tenant scoping in the application/service/repository layer, not only in frontend routing.
- Disable public registration and sharing in the initial private single-owner release unless separately approved.
- Protect against CSRF, XSS, session fixation and credential stuffing; apply secure cookie flags, session expiry/rotation and rate limits.
- Configure strict CORS allowlists and TLS at ingress; do not expose database or object storage publicly.

### 14.2 Secrets and provider credentials

- Keep provider and LLM credentials server-side in a managed secrets service or encrypted secret store. Never return them to the browser or store plaintext in the application database.
- Prefer data-only/read-only API credentials. If a broker-linked API is unavoidable, explicitly assess the credential scope, MFA/TOTP lifecycle, account permissions, revocation and breach impact before selection.
- Do not collect trading passwords, PINs or TOTP seeds in the frontend by default. If a provider requires them, treat that as a provider-selection risk and require a separate approved design.
- Use least privilege, rotation, audit logging and per-provider credential rate limiting. Redact secrets from logs/traces/errors.

### 14.3 Data and model privacy

- Treat reports, prompts, watchlists and chat as sensitive financial-interest data.
- Encrypt database, object snapshots and backups at rest; use TLS in transit.
- Verify LLM provider retention/training/region terms before sending reports or user context. Minimize prompt payloads to the required structured evidence.
- Define retention and deletion for reports, chats, prompts, snapshots, logs and backups. Enforce provider snapshot TTLs and deletion on account removal/contract expiry.
- Keep private object storage with short-lived authorized access; log snapshot access and deletion events.

### 14.4 Application and operational security

- Validate and bound all user input, lookbacks, intervals, custom instructions, output size and model token budgets.
- Treat provider data and model output as untrusted. Do not interpolate provider-supplied text as instructions. Allowlist evidence IDs and candidate price-level IDs; validate every reference.
- Add dependency scanning, secret scanning, pinned dependencies, database migration controls and CI tests.
- Add rate limits and per-user/per-provider cost budgets to prevent abuse and surprise bills.
- Monitor authentication failures, authorization denials, provider errors, model spend, request latency, snapshot access and retention deletion failures.
- Maintain encrypted backups and test restoration. Define incident response and credential revocation steps before external access.

### 14.5 Legal, regulatory and data licensing

A disclaimer does not establish that the product's outputs or distribution are legally permitted. LONG/SHORT views and entry/stop/target levels may have different implications depending on intended users, distribution, personalization, compensation and jurisdiction. Before any access beyond the private owner-only hosted V1, obtain qualified India-specific advice on applicable securities/advisory/research rules and review the user's own jurisdiction if relevant. Separately verify market-data licensing for retrieval, storage, display, derived outputs, user access and redistribution. Regulatory classification and data-provider contractual rights are distinct gates.

## 15. Testing and quality strategy

### 15.1 Unit tests

- Indicator calculations against known fixtures.
- Candle normalization, timestamp boundaries, adjustment basis, provider timestamp mapping and validation.
- Session/timeframe aggregation.
- Pattern detection.
- Multi-timeframe alignment and synthesis.
- Risk/reward and long/short validation.
- Scoring determinism.
- Schema parsing and validation.

### 15.2 Contract and integration tests

- Provider adapter contract tests using recorded/synthetic fixtures that do not violate provider terms.
- Mock provider failure modes: timeout, throttling, malformed response, empty data, partial data, auth expiry.
- Database repository, owner/tenant isolation, migration, snapshot retention/expiry and deletion tests.
- LLM provider adapter tests with mocked responses.
- API request/response, synchronous timeout/idempotency and authorization tests.
- Chat-to-shared-service integration tests.

### 15.3 Evaluation tests

- Golden analysis cases with known input evidence.
- LLM schema compliance and evidence-grounding checks.
- Adversarial cases with contradictory indicators and incomplete data.
- Explicit no-trade cases.
- Model regression tests when prompts/models change.
- Cost and latency measurements.

### 15.4 Financial validation caveat

Historical backtesting is not part of V1. If later added, it must address lookahead bias, survivorship bias, corporate actions, transaction costs, brokerage, taxes/fees, slippage, liquidity, market impact, time alignment and realistic fill assumptions. Paper trading is a separate subsequent validation of live data and operational behavior. Decide the sequence later rather than silently treating one as a substitute for the other.

---

## 16. Hosted deployment and development workflow

### 16.1 Deployment posture

V1 is hosted, private and single-owner by default. Select the cloud provider/region separately based on cost, reliability, data residency, secret management, managed PostgreSQL/object storage, backups and operational simplicity. Do not assume AWS solely because it was previously considered for development. Use containerized deployment with externalized configuration.

Minimum hosted topology:
- HTTPS ingress/reverse proxy with TLS.
- One backend application service (FastAPI) running the synchronous pipeline.
- Static frontend hosted behind the same trusted origin where practical.
- Managed PostgreSQL with private networking and encrypted backups.
- Private object storage for permitted candle snapshots.
- Managed secrets service.
- Centralized logs/metrics/alerts with sensitive-data redaction.

No Redis, Celery, Kafka, Kubernetes, distributed tracing platform or multiple deployable services unless justified by measured requirements. A single backend process is sufficient initially, but deployment must support health checks, controlled restarts and graceful request timeouts.

### 16.2 Local development

- Python backend, React frontend and PostgreSQL via Docker Compose.
- `uv` for dependency/environment management.
- `.env.example` with names/placeholders only; real secrets remain outside version control.
- Migrations, formatting, linting, static typing and tests in CI.
- Separate development/test/prod credentials and databases. Synthetic fixtures for tests; do not commit provider data unless the provider permits it.

### 16.3 Operations

- Define request and provider/LLM timeout budgets and resource limits.
- Track p50/p95 end-to-end and stage latency, provider error/rate-limit frequency, model token usage/cost, snapshot storage growth and retention deletion outcomes.
- Set cost alerts and per-user request limits before exposing the hosted service.
- Test database/object-store backup restore and secret rotation.

## 17. Proposed repository layout

Illustrative layout; reviewers may recommend a simpler or more idiomatic alternative.

```text
trading-assistant/
├── backend/
│   ├── app/
│   │   ├── api/
│   │   │   ├── routes/
│   │   │   └── schemas/
│   │   ├── core/
│   │   │   ├── config.py
│   │   │   └── security.py
│   │   ├── domain/
│   │   │   ├── instruments/
│   │   │   ├── market_data/
│   │   │   ├── analysis/
│   │   │   └── reports/
│   │   ├── providers/
│   │   │   ├── market_data/
│   │   │   └── llm/
│   │   ├── application/
│   │   │   ├── services/
│   │   │   └── workflows/
│   │   ├── pipeline/
│   │   ├── persistence/
│   │   └── main.py
│   ├── tests/
│   ├── pyproject.toml
│   └── Dockerfile
├── frontend/
├── docs/
│   ├── EDD.md
│   ├── ADRs/
│   ├── reviews/
│   └── roadmap.md
├── docker-compose.yml
└── README.md
```

Keep domain and application code independent of FastAPI and specific providers wherever practical; V1 does not include an agent orchestration framework.

---

## 18. Implementation roadmap and release gates

### Phase 0 — Hosted/provider/legal design gates
- Decide the initial hosting vendor/region and private single-owner access model.
- Run a time-boxed provider spike against 2–3 liquid symbols plus corporate-action examples and the intended interval/lookback matrix.
- Verify current pricing, account eligibility, auth, API version, history depth, rate limits, volume semantics, timestamp boundaries, adjustments, data quality and contract rights for storage/display/retention/deletion.
- Verify LLM data handling terms.
- Create ADRs for provider, candle contract, retention tier, credential handling, deployment and direction eligibility.
- Obtain India-specific legal/regulatory advice before any wider distribution or marketing.

**Exit criteria:** one provider chosen with a passing capability/rights matrix; private hosted threat model and credential approach approved; remaining public-distribution gate explicitly documented.

### Phase 1 — Hosted foundation
- Repository, Python environment, FastAPI and frontend shell.
- Authentication/session management and owner-scoped authorization.
- PostgreSQL, private object storage, migrations and secret management.
- Structured logging, cost/rate limits, CI and deployment pipeline.

**Exit criteria:** private hosted application starts securely; unauthorized access and cross-owner access tests pass; health checks and restore procedure documented.

### Phase 2 — Instrument and market-data foundation
- Security/listing/alias/provider mapping model.
- MarketDataProvider protocol and one selected adapter.
- Capability preflight, request chunking, per-credential limiter and typed errors.
- Canonical candle/session/calendar/adjustment contract.
- Tier B candle snapshot persistence only after explicit provider permission; TTL/deletion enforcement.

**Exit criteria:** tested provider requests return validated canonical candles and a persisted permitted snapshot with provenance; unsupported/unauthorized cases fail clearly.

### Phase 3 — Quantitative engine
- Small initial indicator set (OHLCV, SMA/EMA, RSI, ATR; additions only after proof).
- Selected patterns/structure subset if time permits and definitions are testable.
- Multi-timeframe evidence and named gate checklist.
- Deterministic candidate price levels and risk calculations.

**Exit criteria:** deterministic evidence and gates generated from snapshot fixtures without an LLM; lookahead and session-boundary tests pass.

### Phase 4 — LLM reasoning and report
- Provider-neutral LLM interface and one adapter.
- Structured prompt/output schema over evidence IDs and candidate-level IDs.
- Direction × segment × horizon policy and deterministic risk validator.
- Persist reports, exact evidence/prompt/response metadata and snapshot references.
- Model evaluation baseline.

**Exit criteria:** synchronous analysis returns a validated report; invalid data or ineligible direction short-circuits/downgrades safely; WAIT/NO_TRADE works.

### Phase 5 — Dashboard, charts, history and chat
- Configurable analysis form.
- Chart views driven by the report's retained snapshot where permitted.
- Report history, provenance and snapshot-retention status.
- Report-scoped chat through shared services.

**Exit criteria:** owner can configure, run, inspect, revisit charts for permitted snapshots and ask grounded follow-ups.

### Phase 6 — Hardening and controlled release
- Security review, authorization tests, dependency/secret scanning.
- Failure-mode, timeout, idempotency, retention/deletion and backup-restore tests.
- Observability and cost/latency budgets.
- Documentation and incident response.

**Exit criteria:** all V1 acceptance criteria met for the private hosted release. Wider access remains gated on legal/data rights review.

No calendar estimates are committed until provider and hosting constraints are validated.

## 19. V1 acceptance criteria

V1 private hosted release is functionally complete when:

1. Authenticated owner can select a supported NSE/BSE equity listing through canonical identity resolution.
2. User can configure only provider-supported timeframes/lookbacks and the small supported indicator set.
3. Backend preflights entitlement/capability and fetches data from the selected low-cost provider.
4. Candles are normalized with explicit start/end, session/calendar, completeness, volume and adjustment semantics.
5. Invalid, stale, incomplete, unsupported or unauthorized data is surfaced and handled before LLM invocation.
6. Deterministic quantitative evidence and named gate checklist are independently tested; no scalar setup score or uncalibrated probability is presented.
7. Bullish and bearish analysis are supported; actionable LONG/SHORT plans are constrained by a versioned segment × horizon policy. Unsupported SHORT cases produce bias-only plus WAIT/NO_TRADE.
8. LLM interprets structured evidence and selects only supplied candidate price-level/evidence IDs.
9. Deterministic validator checks price geometry, tick size, evidence references and risk/reward.
10. Analysis executes synchronously and returns a completed report or a typed bounded error; no background job/queue is present.
11. Reports include configuration, evidence, provider/model/prompt/policy versions and validator findings.
12. The exact normalized candle snapshot used by the report is retained and available for chart replay **where the provider contract explicitly permits it**; retention expiry and deletion are enforced. Any provider-specific non-retaining mode is clearly disclosed.
13. Report history and chart access are owner-scoped; cross-owner access tests pass even if only one owner is enabled.
14. Chat is report-scoped and uses shared application services.
15. Provider/LLM secrets remain backend-only; hosted auth, authorization, TLS, encrypted persistence/backups, rate/cost controls and monitoring are enabled.
16. No live order execution, scheduled analysis, public registration or multi-user sharing exists in the initial release.
17. Local development, deployment and restore instructions are documented and tested.

## 20. Remaining open questions and ADRs

1. Which low-cost provider/plan passes the required API, history, reliability, data-quality and rights matrix?
2. What exact cloud provider/region and managed services best meet the private hosted cost/security needs?
3. Is V1 strictly one named owner, or are invited users required? Public registration remains out of scope pending approval.
4. What exact snapshot TTL, object format, backup treatment and deletion workflow are permitted by the selected provider contract?
5. What is the exact supported segment × horizon × direction policy, particularly for cash-equity intraday SHORT?
6. What exchange calendar source and versioning approach will be used for NSE and BSE, including special sessions?
7. Which corporate-action adjustment basis can the selected provider reliably supply and preserve?
8. Which small indicator/pattern set passes correctness tests against actual provider data?
9. Which LLM provider/model meets evidence-grounding, privacy, latency and cost requirements?
10. What synchronous request deadline and workload caps are acceptable after benchmarking?
11. What retention/deletion periods apply to reports, chat, prompts, snapshots, logs and backups?
12. What India-specific legal/regulatory constraints apply to private use and any future distribution/marketing, and what jurisdiction-specific advice is needed for the owner?
13. Should the next validation stage after V1 be historical backtesting or paper trading? These answer different questions.

### Required ADRs before implementation

- ADR-001: selected market-data provider, plan and rights matrix.
- ADR-002: canonical candle/session/calendar/adjustment contract.
- ADR-003: candle snapshot storage, TTL, display and deletion policy.
- ADR-004: hosted identity, owner/tenant boundary and credential model.
- ADR-005: supported direction × segment × horizon policy.
- ADR-006: synchronous API budgets, idempotency and failure semantics.
- ADR-007: hosting vendor/region and operational cost controls.

## Revision history

| Version | Date | Changes |
|---|---|---|
| 0.1 | 7 November 2026 | Initial draft for independent Claude and Codex architecture review. |
| 0.2 | 7 November 2026 | Incorporated owner decisions: hosted deployment, low-cost provider target, both LONG/SHORT with eligibility restrictions, synchronous execution, and retained candle snapshots subject to provider rights. Applied convergent review recommendations: plain typed pipeline, hosted security baseline, Tier A/Tier B persistence, canonical candle/session/adjustment semantics, identity mapping, no scalar setup score, directional bias/actionability separation, candidate price-level IDs, and implementation gates. |

## 21. Reviewer instructions and expected deliverables

Review this v0.2 as a skeptical senior/principal engineer with experience in hosted application security, backend systems, market-data pipelines, quantitative systems and LLM applications. Focus on whether the owner decisions are consistently reflected and whether the remaining gates are explicit.

### Required review output

Create a separate file named:
- `codex-review.md` for Codex, or
- `claude-review.md` for Claude.

Do not modify this EDD during the first review.

Use this structure:

1. **Executive assessment:** sound / sound with changes / not ready, with concise rationale.
2. **Critical blockers:** issues that must be resolved before implementation.
3. **High-priority improvements:** changes strongly recommended for V1.
4. **Deferred improvements:** useful but not necessary for V1.
5. **Disagreements:** decisions you would change, alternatives and trade-offs.
6. **Missing requirements / open questions:** anything material omitted.
7. **Financial/data correctness risks:** concrete failure scenarios and mitigations.
8. **Security and operational risks.**
9. **Simplification opportunities:** remove complexity that does not create V1 value.
10. **Proposed revised architecture:** only where a meaningful change is justified.
11. **Suggested schema/API changes:** concrete examples where useful.
12. **Prioritized action list:** severity, rationale, effort/impact and decision needed.

For every recommendation:
- Identify the exact EDD section.
- Explain the failure mode or benefit.
- State the consequence of not adopting it.
- Classify as **MUST FIX**, **SHOULD FIX**, **DEFER**, or **OPTIONAL**.
- State confidence and cite official/current sources for claims about APIs, provider terms, pricing, package support or framework capabilities.
- Separate evidence-backed facts from engineering judgment.
- Do not invent provider capabilities, free tiers, data entitlements or legal permissions.
- Do not introduce trading execution, scheduled analysis or microservices into V1 without a compelling requirement.
- Do not treat LLM confidence as calibrated probability.
- Do not rewrite the whole EDD merely to express stylistic preferences.

### Independence requirement

Perform your review independently. Do not request or inspect the other agent's review before completing yours. The two reviews will be reconciled afterward by the project owner.

### Review-only boundary

Do not write application code, scaffold the repository, install dependencies, edit the EDD, or implement your proposed changes. Your deliverable is the review report only.

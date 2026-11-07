Warning: truncated output (original token count: 12009)
Total output lines: 1024

# Engineering Design Document (EDD)
## AI-Assisted Indian Equity Market Analysis Platform

- **Document status:** Draft for independent architecture review
- **Version:** 0.1
- **Date:** 7 November 2026
- **Intended reviewers:** OpenAI Codex CLI and Claude Code
- **Decision authority:** Project owner, with review support from the agents

> **Review status:** This document captures the product direction and architectural decisions agreed so far. It is not implementation authorization. Reviewers must challenge assumptions, identify gaps, and distinguish required corrections from optional preferences. Do not edit this source document during the independent review.

---

## 1. Executive summary

The product is an AI-assisted market-analysis application, initially focused on Indian listed equities (NSE/BSE). A user configures an instrument, timeframes, indicators and analysis preferences, then requests an on-demand analysis. The application obtains market data from an external provider, normalizes and validates it, computes quantitative evidence deterministically, asks a configurable LLM to interpret the structured evidence, validates the proposed trade plan with deterministic risk rules, and presents a report. Users can also ask follow-up questions through a chat interface that uses the same application services and analysis context.

The product is an **analysis and decision-support tool**, not an automated trading system. V1 does not place orders, run scheduled analyses, or claim statistically calibrated probabilities unless calibration has actually been demonstrated.

The architecture should be modular and provider-independent without prematurely splitting the application into microservices. Python is the preferred backend language. FastAPI is the provisional API framework. LangGraph is the provisional orchestration framework, subject to review against simpler orchestration and Google ADK. PostgreSQL is the provisional persistence layer. A React/TypeScript frontend is proposed.

### 1.1 Product goals

1. Make configurable, evidence-backed technical analysis available on demand.
2. Support Indian equities first, while keeping the market-data and instrument model extensible.
3. Separate deterministic market calculations from probabilistic language-model interpretation.
4. Make data providers and LLM providers replaceable behind stable interfaces.
5. Persist reports and sufficient provenance to audit and understand past analyses.
6. Provide a dashboard and conversational interface over the same analysis capabilities.
7. Keep V1 achievable and maintainable for a small project team.

### 1.2 Non-goals for V1

- Placing, modifying, or cancelling live orders.
- Brokerage integration or custody of trading funds.
- Scheduled or unattended analysis.
- Full portfolio management, tax accounting or investment advice.
- Options, futures and other derivatives as first-class supported instruments (design should not block them).
- A sophisticated backtesting or paper-trading platform; revisit after V1.
- Permanent storage of all raw market candles.
- Microservices, message brokers, Kubernetes or distributed infrastructure without demonstrated need.

---

## 2. Confirmed decisions, provisional choices and open questions

Reviewers must preserve this distinction.

### 2.1 Agreed direction

| Topic | Agreed direction |
|---|---|
| Initial market | Indian equities, NSE/BSE |
| Backend language | Python preferred over Java/Spring |
| API style | FastAPI is the current proposal |
| Agent orchestration | LangGraph is the current preference, but must be challenged against Google ADK and a simpler workflow |
| Architecture shape | Modular monolith initially; avoid premature microservices |
| Market data | Start with a free/low-cost provider, subject to verification of terms, access, limits and data quality |
| Data persistence | Do not permanently persist raw candle history in V1 |
| Analysis evidence | Persist analysis requests, configuration snapshots, reports, structured findings and data/model provenance sufficient for auditability |
| Analysis execution | On demand only in V1 |
| Quantitative calculations | Deterministic code, not LLM calculations from raw candles |
| LLM role | Interpret structured evidence, explain scenarios and formulate a thesis |
| Provider independence | Abstract market-data and LLM providers |
| User experience | Configurable dashboard plus chat; chat calls the same application services |
| Verdicts | LONG / SHORT / WAIT / NO_TRADE, subject to deterministic validation and market/instrument constraints |
| Trading execution | Out of scope for V1 |

### 2.2 Provisional technical choices to validate

- FastAPI, Pydantic and SQLAlchemy (or an alternative ORM/data-access approach).
- PostgreSQL for persistence.
- LangGraph for orchestration.
- React + TypeScript for the frontend.
- Docker Compose for local development and reproducible deployment.
- `uv` for Python dependency and environment management.
- Pandas/NumPy and a carefully selected technical-analysis implementation. Package maintenance, compatibility, licensing and correctness must be checked before selection.
- A provider adapter such as Angel One SmartAPI as a candidate, not a committed provider. TejHQ and Upstox may be evaluated as alternatives. Do not assume a free tier, API entitlement or permitted usage without current official verification.

### 2.3 Deferred decisions

- Final market-data provider and any backup provider.
- Whether the first validation stage after V1 is historical backtesting or live paper trading. These answer different questions; revisit with explicit requirements.
- Hosting/cloud provider and production topology.
- Authentication approach and whether V1 is single-user/local-first or multi-user.
- Whether to introduce caching, and its invalidation policy.
- Whether to add scheduled jobs, notifications, streaming or background workers.
- Whether to support indices, ETFs, derivatives and additional markets.
- Whether to add model routing, multiple LLMs per request, or specialist agents.

---

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
15. Report is persisted with provenance and returned to the UI.
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
- Risk appetite/profile.
- Minimum risk/reward ratio.
- Maximum risk per trade (percentage or configured risk unit; clarify whether this is a user portfolio risk input or a generic scenario constraint).
- Minimum setup-quality threshold.
- Analysis depth: quick, standard, deep.
- Include alternative scenarios.
- Include/exclude specific indicators.
- Custom instructions, bounded by system safety and output schema.

### 4.5 AI settings

- Provider/model selection should be configurable.
- Model/provider changes must not require changes to quantitative or market-data modules.
- Store provider, model identifier, prompt/template version and relevant generation parameters with each report.
- Model-generated confidence must not be presented as a calibrated probability by default.
- The UI should distinguish:
  1. **Setup quality score:** a deterministic or explicitly defined heuristic score.
  2. **Calibrated probability/confidence:** only shown after statistical calibration and out-of-sample validation.
  3. **LLM qualitative assessment:** explanatory judgment, not a probability.
- User-selectable thresholds such as 90%, 95%, 98% or 99% must not be represented as meaningful probability thresholds unless a calibrated model supports them. Until then, expose a setup-quality threshold with clear labeling.

### 4.6 Analysis report

A report should include:
- Instrument, exchange and analysis timestamp.
- Data timestamp, freshness and source/provider.
- Selected timeframes and lookback.
- Configuration snapshot.
- Verdict: LONG / SHORT / WAIT / NO_TRADE.
- Trading style/horizon.
- Directional bias and thesis.
- Entry zone or explicit statement that no entry is justified.
- Stop-loss/invalidation level.
- One or more targets, with assumptions.
- Risk/reward calculation.
- Supporting evidence and contradicting evidence.
- Per-timeframe findings and conflicts.
- Key indicator values and interpretation.
- Market regime/context where implemented.
- Risks, limitations, edge cases and alternative scenarios.
- Data-quality warnings.
- Setup-quality score and calibration status, where available.
- Model/provider/prompt metadata.
- Deterministic validator outcome and any changes it made.

A report must be allowed to conclude WAIT or NO_TRADE. It must not force a trade recommendation.

---

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

1. **Frontend:** dashboard, configuration forms, chart/report views and chat.
2. **API layer:** FastAPI routes, authentication boundary, request validation and response serialization.
3. **Application services:** use cases such as `CreateAnalysis`, `GetReport`, `AskReportQuestion`.
4. **Instrument service/catalog:** canonical instrument resolution and metadata.
5. **Market-data domain:** provider interface, adapters, normalizers, validators and aggregation.
6. **Quantitative analysis:** indicators, patterns, market structure, multi-timeframe synthesis and deterministic scoring.
7. **AI reasoning:** provider-neutral LLM interface, prompt construction, structured output parsing and model metadata.
8. **Risk validation:** deterministic checks on proposed verdict and price levels.
9. **Orchestration:** workflow coordination; LangGraph is provisional and must not own business rules.
10. **Persistence:** repositories for analysis requests, reports, evidence and configuration profiles.
11. **Chat:** conversational interface that calls the same application services and can reference saved reports.

### 6.2 Suggested request flow

```text
React UI / Chat
      |
      v
FastAPI routes
      |
      v
Application service (CreateAnalysis)
      |
      +---- Instrument resolution
      |
      v
Orchestrator (provisional: LangGraph)
      |
      +---- MarketDataProvider
      |         |
      |         +---- Provider adapter
      |         +---- Normalize canonical candles
      |         +---- Validate / align / aggregate
      |
      +---- Quantitative engine
      |         +---- Indicators
      |         +---- Patterns / structure
      |         +---- Per-timeframe findings
      |         +---- Multi-timeframe synthesis
      |
      +---- LLM reasoning provider
      |         +---- Structured analysis
      |
      +---- Deterministic risk validator
      |
      v
Report + provenance persistence
      |
      v
API response -> Dashboard / Chat
```

### 6.3 Architectural constraint

The application must remain useful and testable without LangGraph. Core services should be callable directly from tests and non-agent workflows. LangGraph (or ADK) should coordinate steps, not become the only place where domain logic exists.

---

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

Potential adapters (not committed):
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

Illustrative Pydantic model (refine during review):

```python
from datetime import datetime
from decimal import Decimal
from pydantic import BaseModel

class Candle(BaseModel):
    instrument_id: str
    exchange: str
    timeframe: str
    timestamp: datetime  # canonical timezone policy must be specified
    open: Decimal
    high: Decimal
    low: Decimal
    close: Decimal
    volume: Decimal | None = None
    open_interest: Decimal | None = None
    is_complete: bool
    source_provider: str
```

Reviewers should challenge:
- Whether timestamps should be UTC internally with exchange timezone metadata.
- Whether price/volume types should be Decimal, integer-scaled or float for numerical libraries.
- Whether candle identity needs a composite key.
- How corporate actions and adjusted/unadjusted prices are represented.
- Whether source metadata belongs on each candle or in a batch-level provenance object.

Raw provider payloads should remain inside adapters or short-lived diagnostics; avoid persisting all raw candles in V1.

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

### 7.6 Data retention and caching

V1:
- Fetch candles on demand.
- Do not maintain a permanent raw-candle warehouse.
- Persist the request window, provider, retrieval timestamp, candle count, time range, data-quality summary and preferably a content hash or compact evidence snapshot sufficient to identify the exact inputs used.
- Persist derived evidence and report.
- Decide whether to retain a compact candle snapshot for reproducibility; this is an open design trade-off because a hash alone cannot reconstruct the original input.
- Caching is deferred until latency, quota or cost measurements justify it.

**Important review question:** Is the proposed evidence/provenance sufficient to reproduce a historical report without storing all raw candles? If not, propose a storage strategy that respects provider licensing and retention terms.

---

## 8. Quantitative analysis engine

### 8.1 Principles

- All numerical indicator and risk calculations occur in deterministic code.
- LLM receives structured results, not responsibility for calculating RSI, ATR, MACD or price levels from raw candles.
- Each calculation must be independently testable against known fixtures/reference implementations.
- Store indicator configuration and implementation version with the report.
- Avoid lookahead: a calculation at time `t` may only use information available at or before `t`.
- Define warm-up periods, missing-data behavior and NaN handling explicitly.

### 8.2 Suggested internal layers

- `indicators/`: pure indicator functions and typed output.
- `patterns/`: explicit pattern definitions and detection.
- `market_structure/`: swings, support/resistance, BOS/CHOCH, regime features.
- `timeframes/`: timeframe-specific calculation and alignment.
- `synthesis/`: compare signals and conflicts across timeframes.
- `scoring/`: transparent setup-quality score (not a probability).
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

For each indicator, specify:
- Formula and source/reference.
- Parameters and defaults.
-…9 tokens truncated…tory.
- Warm-up length.
- Output scale and interpretation.
- Edge cases and missing values.
- Unit tests with deterministic fixtures.
- Version identifier.

The choice of pandas/NumPy and any technical-analysis library remains provisional. Review maintenance status, compatibility with the target Python version, license, reproducibility and numerical correctness before selecting a dependency.

---

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
- Verdict and directional bias.
- Horizon/trading style.
- Thesis.
- Entry zone (optional).
- Stop/invalidation (optional).
- Targets (optional list).
- Supporting and contradicting evidence IDs.
- Risks and alternative scenarios.
- Explanation and assumptions.
- Qualitative LLM assessment.
- Setup-quality score reference, if computed separately.

Parsing failures should have bounded repair/retry behavior. A malformed model response must not be rendered as a valid trade plan.

### 9.4 Confidence and scoring

Keep these distinct:
- **Setup quality:** transparent rule-based score with documented components and weights.
- **LLM assessment:** qualitative reasoning, not probability.
- **Calibrated probability:** only after outcome labels, sufficient samples, leakage controls, calibration analysis and out-of-sample validation.

Do not present a user-selected “99% confidence” setting as a real 99% chance of success. Until calibration exists, the UI should use a clearly named minimum setup-quality threshold.

### 9.5 LangGraph vs Google ADK vs simpler orchestration

LangGraph is the provisional choice because the workflow has explicit stages, conditional branches, potential parallel timeframe processing and typed state. However:
- The workflow is mostly deterministic; a simple application-service pipeline may be sufficient for V1.
- Google ADK is a credible alternative and should be compared on model-provider neutrality, workflow control, typed state, testing, observability, deployment fit, ecosystem maturity and lock-in.
- Review whether any agent framework is needed at all in V1.
- Do not use multiple agents for individual indicators. Indicators are deterministic functions. Start with one reasoning call over synthesized evidence unless evaluation demonstrates a measurable benefit from additional agents.
- Framework orchestration must remain replaceable.

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

## 10. Deterministic risk validation

The risk validator is a hard boundary between model output and user-visible trade setup.

Examples of checks:
- Entry, stop and targets are numeric, finite and within plausible instrument price bounds.
- LONG: stop should be below entry; targets should be above entry, subject to explicitly supported order/strategy types.
- SHORT: stop should be above entry; targets should be below entry, subject to instrument and holding-period constraints.
- Risk distance is non-zero and reward/risk is calculated by code.
- Targets and stops are ordered consistently.
- Proposed levels do not contradict the supplied current/last close without an explicit rationale.
- Requested minimum risk/reward is satisfied or verdict is downgraded to WAIT/NO_TRADE.
- No trade plan is emitted when required data is invalid or stale.
- Long/short availability and holding-period constraints are market/instrument-specific.

The validator should return structured findings and a clear outcome: accepted, corrected only through deterministic rules, downgraded, or rejected. It must not silently rewrite model levels without recording the change.

Indian cash-equity short-selling and overnight holding rules are different from intraday short positions and derivatives. Do not hardcode generic shorting assumptions; verify applicable exchange/regulatory and broker constraints before any future feature relies on them. No execution is in V1.

---

## 11. Persistence and data model

PostgreSQL is the provisional database. Review whether the proposed entities and retention are sufficient.

### 11.1 Candidate entities

- `instrument`: canonical instrument identity and exchange metadata.
- `analysis_profile`: saved user configuration.
- `analysis_request`: requested instrument, timeframe range, settings and request status.
- `analysis_run`: execution metadata, start/end times, status and correlation ID.
- `data_provenance`: provider, retrieval time, requested range, actual range, counts, data-quality summary, content hash and license/retention metadata where appropriate.
- `analysis_evidence`: structured per-timeframe indicator/pattern/market-structure findings.
- `analysis_report`: final verdict, thesis, risk plan, explanation and validation status.
- `model_invocation`: provider/model, prompt version, generation parameters, token/cost/latency metadata where available.
- `chat_session` / `chat_message`: conversational context and report references, if chat history is persisted.

### 11.2 Persistence principles

- Save a configuration snapshot with each analysis; later profile edits must not alter past reports.
- Save algorithm/indicator version and prompt version.
- Store report and structured evidence, not just rendered prose.
- Store provenance and freshness.
- Do not store provider secrets or unnecessary raw payloads.
- Decide whether compact normalized candle snapshots are required for reproducibility and whether provider terms permit retention.
- Define retention/deletion policy.
- Use migrations and explicit schema versioning.

### 11.3 Reproducibility limitation

If raw candles are not retained, a report may not be exactly reproducible if the provider revises historical data or changes corporate-action adjustments. The design must state whether it targets:
1. **Auditability:** explain what data/config/model were used and preserve derived evidence.
2. **Exact computational reproducibility:** preserve sufficient normalized inputs (subject to licensing) to rerun calculations.
These are not identical. Reviewers must recommend a practical V1 balance.

---

## 12. API design (initial proposal)

Exact routes and payloads are open to review. Candidate endpoints:

| Method | Endpoint | Purpose |
|---|---|---|
| GET | `/api/v1/instruments` | Search/list supported instruments |
| GET | `/api/v1/instruments/{instrument_id}` | Instrument details |
| GET | `/api/v1/market-data/capabilities` | Provider/timeframe capability summary |
| GET | `/api/v1/indicators` | Indicator catalog and parameter schemas |
| GET | `/api/v1/analysis-profiles` | List saved profiles |
| POST | `/api/v1/analysis-profiles` | Create/update a profile |
| POST | `/api/v1/analyses` | Start on-demand analysis |
| GET | `/api/v1/analyses/{analysis_id}` | Analysis status/result |
| GET | `/api/v1/reports/{report_id}` | Retrieve saved report |
| POST | `/api/v1/chat/sessions` | Create chat session |
| POST | `/api/v1/chat/sessions/{session_id}/messages` | Ask a question using shared services |

Consider synchronous request/response for a first implementation if provider/model latency permits. If analysis becomes long-running, introduce a job/status pattern without prematurely adding a queue. Define idempotency, timeouts, cancellation and partial-failure semantics.

### 12.1 Analysis request example

```json
{
  "instrument_id": "NSE:RELIANCE",
  "timeframes": [
    {"interval": "15m", "lookback": "20d", "role": "primary"},
    {"interval": "1h", "lookback": "60d", "role": "confirmation"},
    {"interval": "1d", "lookback": "1y", "role": "context"}
  ],
  "indicators": [
    {"name": "rsi", "parameters": {"period": 14}},
    {"name": "macd", "parameters": {"fast": 12, "slow": 26, "signal": 9}},
    {"name": "atr", "parameters": {"period": 14}}
  ],
  "preferences": {
    "horizon": "swing",
    "direction": "both",
    "strategy": "all",
    "minimum_risk_reward": 2.0,
    "minimum_setup_quality": 70,
    "analysis_depth": "standard",
    "include_alternative_scenarios": true
  },
  "data_policy": {
    "use_closed_candles_only": true
  }
}
```

This is illustrative, not a finalized API contract. Units, enums, defaults, validation and lookback semantics must be specified before implementation.

---

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
   - Invoke shared backend application services.

5. **Settings**
   - Market-data provider configuration.
   - LLM provider/model configuration.
   - Saved analysis profiles.
   - Security/credential management.

### 13.2 UX constraints

- Do not overload users with every possible indicator by default; categorize and provide sensible presets.
- Show data-quality warnings prominently.
- Explain WAIT/NO_TRADE rather than treating it as a failure.
- Distinguish calculated metrics from model-generated narrative.
- Do not imply that a visually polished score is a statistically validated probability.

---

## 14. Security and privacy

- Keep provider and LLM API keys on the backend; never expose secrets to browser code.
- Use environment variables or a secrets manager; do not commit `.env` files.
- Redact credentials and sensitive provider payloads from logs.
- Validate all user input and bound lookback, indicator count and request size.
- Add authentication/authorization before exposing the app beyond trusted local use.
- Apply rate limits and cost controls to model calls.
- Treat market-data and model outputs as untrusted inputs.
- Prevent prompt injection through provider data, news text or user-supplied content; data must not be interpreted as instructions that override system policy.
- Define CORS, CSRF/session handling and secure cookie/token strategy based on deployment model.
- Avoid collecting personal financial account credentials in V1.
- Document data retention and deletion.

---

## 15. Testing and quality strategy

### 15.1 Unit tests

- Indicator calculations against known fixtures.
- Candle normalization and validation.
- Session/timeframe aggregation.
- Pattern detection.
- Multi-timeframe alignment and synthesis.
- Risk/reward and long/short validation.
- Scoring determinism.
- Schema parsing and validation.

### 15.2 Contract and integration tests

- Provider adapter contract tests using recorded/synthetic fixtures that do not violate provider terms.
- Mock provider failure modes: timeout, throttling, malformed response, empty data, partial data, auth expiry.
- Database repository and migration tests.
- LLM provider adapter tests with mocked responses.
- API request/response tests.
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

## 16. Deployment and development workflow

Provisional local setup:
- Python backend.
- React frontend.
- PostgreSQL.
- Docker Compose for local dependencies and repeatable startup.
- `uv` for Python package management.
- `.env.example` with names/placeholders only.
- Migrations.
- Formatting, linting, static typing and tests in CI.

Do not add Redis, Celery, Kafka, Kubernetes or multiple deployable services until requirements and measurements justify them.

Cloud deployment is undecided. Keep configuration externalized and container-friendly so a future AWS or other cloud deployment is possible.

---

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
│   │   ├── orchestration/
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

Keep domain and application code independent of FastAPI, LangGraph and specific providers wherever practical.

---

## 18. Implementation roadmap (proposed, subject to review)

### Phase 0 — Design validation
- Complete independent Codex and Claude reviews.
- Resolve critical disagreements.
- Finalize provider selection after official documentation, terms and hands-on API tests.
- Finalize schemas and API contracts.

**Exit criteria:** approved EDD v1.0, ADRs and first milestone scope.

### Phase 1 — Project foundation
- Repository and Python environment.
- FastAPI skeleton and configuration.
- PostgreSQL and migrations.
- Logging, error model and test setup.
- Frontend shell and local development workflow.

**Exit criteria:** application starts reproducibly; health endpoint, database connection and CI tests work.

### Phase 2 — Instrument and market-data foundation
- Canonical instrument model.
- MarketDataProvider protocol.
- One real provider adapter.
- Normalization, session-aware validation and timeframe support.
- Provider contract tests and clear failure handling.

**Exit criteria:** selected instrument/timeframe returns validated canonical candles with provenance and data-quality summary.

### Phase 3 — Quantitative engine
- Initial indicator set.
- Pattern/market-structure subset selected for V1.
- Multi-timeframe evidence model.
- Deterministic scoring and risk calculations.
- Unit/golden tests.

**Exit criteria:** reproducible structured evidence generated from fixture and provider data without an LLM.

### Phase 4 — LLM reasoning and report
- Provider-neutral LLM interface.
- One model adapter initially.
- Prompt/schema and structured parsing.
- Deterministic risk validator.
- Persisted reports and provenance.
- Model evaluation baseline.

**Exit criteria:** an on-demand analysis returns a validated report and safely returns WAIT/NO_TRADE when evidence is insufficient.

### Phase 5 — Dashboard and chat
- Configurable analysis form.
- Report visualization and history.
- Chat integration through shared application services.
- User-facing data freshness and warnings.

**Exit criteria:** user can configure, run, inspect, save and ask follow-up questions about an analysis.

### Phase 6 — Hardening
- Security and credential handling.
- Failure-mode tests.
- Observability and cost/latency measurement.
- Documentation and reproducible deployment.

**Exit criteria:** V1 acceptance criteria met; known limitations documented.

No calendar estimates are committed until the scope and provider constraints are validated.

---

## 19. V1 acceptance criteria

V1 is considered functionally complete when:

1. User can select a supported NSE/BSE equity instrument.
2. User can configure supported timeframes, lookbacks and indicator parameters.
3. The backend fetches data from the selected provider and normalizes/validates it.
4. Incomplete, stale or invalid data is surfaced and handled according to explicit policy.
5. Quantitative calculations are deterministic and independently tested.
6. Multi-timeframe evidence is generated with conflicts preserved.
7. A configurable LLM interprets the evidence and returns schema-valid output.
8. Deterministic validation checks trade geometry and risk/reward.
9. The system can return WAIT/NO_TRADE rather than forcing a trade.
10. Reports include evidence, provenance, configuration and model/prompt metadata.
11. Reports can be retrieved from history.
12. Chat uses the same application services and can discuss a saved report.
13. No live order execution or scheduled analysis exists in V1.
14. Local development and tests can be run from documented instructions.

---

## 20. Open questions requiring review

Reviewers should explicitly answer these, not merely repeat the proposed design.

1. Is a modular monolith the right boundary for V1? What modules are too granular or missing?
2. Is LangGraph justified, or is a plain typed Python workflow better initially? Compare Google ADK as well.
3. Is FastAPI + Pydantic + PostgreSQL an appropriate stack? Any simpler/better alternatives?
4. What is the right canonical representation for prices, volume, timestamps and candle identity?
5. How should NSE/BSE instrument masters and symbol changes be handled?
6. What exchange calendar/session source should be used, and how should special sessions be represented?
7. What exact data must be persisted to make reports auditable and/or reproducible while respecting provider terms?
8. Should normalized candles be retained as compact snapshots, or should V1 retain only derived evidence and hashes?
9. What is the minimum viable indicator/pattern catalog? Which candidates should be deferred?
10. How should multi-timeframe conflicts be represented without arbitrary indicator voting?
11. What is a defensible setup-quality score for V1, or should scoring be deferred until an evaluation set exists?
12. What deterministic risk rules are essential for a useful first release?
13. Should analysis be synchronous initially or use a job/status model?
14. Is chat history required in V1? How should report context be bounded and referenced?
15. What provider(s) should be tested first based on current official access, historical intervals, reliability, terms, rate limits and actual data quality?
16. What security controls are necessary for a local-first single-user V1 versus a hosted multi-user release?
17. Which features should be explicitly excluded to protect scope?
18. What are the biggest financial-domain correctness risks not covered here?

---

## 21. Reviewer instructions and expected deliverables

Review this as a skeptical senior/principal engineer with experience in backend systems, market-data pipelines, quantitative systems and LLM applications.

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

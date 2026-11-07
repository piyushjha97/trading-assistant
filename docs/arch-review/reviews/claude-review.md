Warning: truncated output (original token count: 12340)
Total output lines: 483

# Independent Architecture Review: AI-Assisted Indian Equity Analysis Platform

Nov 7, 2026 · @Piyush

Verdict: sound with changes. The principles hold, but seven blockers (provider terms, reproducibility, corporate actions, candle boundaries, scoring, credentials, regulatory posture) must be resolved before building.

## Scope and conventions

This is a review only of EDD v0.1 (7 Nov 2026), README.md and REVIEW\_PROMPT.md: no code, no EDD edits. I did not verify provider documentation, terms, pricing or package status against official sources in this session, so every external-fact claim is marked **\[UNVERIFIED\]** and comes from training knowledge (reliable to roughly mid-2026). Section 7 includes a verification checklist for a provider spike. Everything else is engineering judgment on the EDD itself.

- **Severity:** MUST FIX / SHOULD FIX / DEFER / OPTIONAL
- **Confidence:** High / Medium / Low
- **Judgment:** engineering opinion, not an external fact

## 1. Executive assessment

**Verdict: sound with changes.** The EDD gets the hardest conceptual separations right: deterministic computation is kept apart from LLM interpretation, setup quality is kept apart from calibrated probability, the LLM is not trusted for price levels, WAIT/NO\_TRADE is a first-class outcome, and framework code stays out of the domain layer.

Most of the risk is in what the document leaves unspecified. The seven findings that matter most:

1. **The provider and its terms are the root dependency.** Data schema, retention, reproducibility, timeframes, authentication and legality all depend on one unresolved choice. The roadmap decides it *after* "finalize schemas and API contracts" (§18 Phase 0), which is backwards.
2. **"No raw-candle storage" contradicts the report UI.** The report view needs charts (§13.1) and history must re-render them. A hash cannot do that, and re-fetching returns revised or re-adjusted data (§7.6, §11.3).
3. **Corporate-action policy, candle-boundary conventions and lookahead-safe market structure are named but not decided.** For Indian equities these determine whether signals are correct.
4. **LangGraph is not justified for V1.** The workflow is a linear deterministic pipeline with one LLM call. A plain typed Python pipeline is better, and Google ADK is not warranted either (D-1).
5. **The LLM should select from deterministically generated levels, not invent them.** This removes a class of failure and shrinks the validator's burden (H1).
6. **Several conflicts are unflagged:** brokerage-login credentials versus "no personal financial credentials" (§14), "no scheduled jobs" versus instrument-master and calendar freshness, and positional SHORT versus cash-equity constraints.
7. **Regulatory posture is absent.** Output in the form LONG/SHORT + entry/stop/targets may be treated differently under Indian rules depending on who uses it and how it is distributed **\[UNVERIFIED\]**. It needs a decision, not necessarily a legal opinion yet.

The design can proceed once the five owner decisions at the end are made. None of the blockers requires abandoning the architecture.

## 2. Critical blockers

All seven are MUST FIX before implementation.

### B1. Provider selection, entitlement and terms precede schema/API design

- **EDD:** §2.2, §2.3, §7.1–7.2, §18 Phase 0
- **Issue:** Angel One SmartAPI, Upstox and TejHQ differ in authentication, interval sets, historical depth per request, rate limits, symbol identifiers, adjustment semantics and permitted use **\[UNVERIFIED for all\]**. The canonical model, `ProviderCapabilities`, retention policy and timeframe list all depend on the answers.
- **Failure mode:** Mid-build discoveries such as "free tier doesn't permit storing or passing data to third parties", "intraday history is shorter than the example lookbacks", or "daily login requires a brokerage TOTP secret".
- **Recommendation:** Run a time-boxed, pass/fail provider spike *before* finalizing schemas (checklist in section 7), hands-on on 2–3 liquid symbols and 1–2 corporate-action symbols. Output one ADR.
- **If not adopted:** Rework of the canonical model, persistence and timeframes; possible terms violation shipped into V1.
- **Confidence:** High (judgment); provider facts Low until verified.

### B2. Reproducibility strategy is undecided and "hash-only" is not viable

- **EDD:** §7.6, §11.3, §13.1, §20 Q7–8
- **Issue:** A hash cannot reconstruct inputs. More importantly, the report screen needs candles for charts, and history re-opens old reports. Without stored candles, charts are either re-fetched (providers may revise or re-adjust, so the chart no longer matches the evidence) or omitted from history.
- **Failure mode:** An audit trail saying "RSI was 71.2" beside a chart of different candles undermines trust in the product.
- **Recommendation:** Two explicit tiers.
  - **Tier A (always stored, no licensing concern):** configuration snapshot, the exact typed evidence package given to the LLM, the rendered prompt and raw LLM response (compressed), model/prompt/engine/indicator-catalog versions, validator findings and diffs, and provenance (provider, retrieval time, requested/actual range, counts, quality summary, hash). This makes the *report* auditable and replayable at the LLM and validator layers.
  - **Tier B (gated by the provider spike):** a compact normalized candle *window snapshot* (only bars fed to computation and display, per timeframe, compressed Parquet or JSONB) with a retention TTL and a per-provider `may_retain` capability flag. A per-report snapshot is not a warehouse, so it respects the "no permanent raw-candle warehouse" boundary.
  - State honestly that exact LLM reproduction is impossible (non-determinism). What can be reproduced exactly is the deterministic evidence and validator outcome, given Tier B.
- **If not adopted:** Unverifiable history, charts that drift from evidence, no way to debug a bad past report.
- **Confidence:** High (judgment); provider retention permission Low/unverified.

### B3. Corporate-action and price-adjustment policy is absent

- **EDD:** §7.3, §7.4, §4.1
- **Issue:** `Candle` has no `adjustment_basis`. Indian equities see frequent splits, bonuses, rights issues and demergers. Providers differ on whether daily/weekly history is adjusted, and intraday history is often unadjusted **\[UNVERIFIED\]**. A 1y daily lookback spanning a 1:5 split produces a false \~80% gap that corrupts ATR, Bollinger, RSI, swings and support/resistance.
- **Failure mode:** Confident, wrong signals with no visible error.
- **Recommendation:**
  - Add `adjustment_basis` (`RAW | SPLIT_BONUS_ADJUSTED | FULLY_ADJUSTED | UNKNOWN`) to batch provenance and candle identity.
  - Add a validation check for abnormal overnight discontinuities (gap beyond a threshold with a volume anomaly), cross-checked against an actions list where available.
  - **Fail closed:** `UNKNOWN` basis or an unexplained discontinuity inside the lookback is a data-quality failure, so NO\_TRADE with explanation, or truncate the lookback to after the event with an explicit warning.
  - Never mix adjusted and unadjusted data across timeframes in one analysis.
- **If not adopted:** Silent wrong evidence on a predictable fraction of instruments.
- **Confidence:** High (judgment); provider adjustment behavior unverified.

### B4. Candle-boundary, timestamp and "as-of" conventions are undefined

- **EDD:** §4.2, §7.3–7.5, §8.3
- **Issue:** The EDD says "closed candles" but defines neither the convention nor the as-of instant.
  - The NSE normal session is 09:15–15:30 IST, 375 minutes **\[UNVERIFIED, verify\]**. 15m, 5m, 3m and 1m tile it; **30m, 1h and 10m leave a partial final bar** (1h bars start 09:15, 10:15, … 15:15, so the last is 15 minutes long). **4h cannot tile a 375-minute session** and yields a cross-session bar or a stub. Weekly bars depend on holidays and anchoring.
  - Providers differ on whether a timestamp is bar open or close, and whether it carries a timezone **\[UNVERIFIED\]**.
  - "Closed" depends on the wall clock, the exchange calendar and provider latency. The 1h bar ending 11:15 is not usable at 11:15:02 if the provider publishes with delay.
- **Recommendation:**
  - `bar_open_ts` (UTC-aware) is the canonical key; `bar_close_ts` is explicit; intervals are half-open `[open, close)`.
  - Define each timeframe as a **session-anchored** bucket, and decide explicitly whether a session's short last bar is kept, merged or dropped, and mark it.
  - **Drop 4h from V1** unless a session-anchored definition is written down.
  - One `as_of` instant (UTC) per run, and a `closed_at_or_before(as_of - provider_latency_buffer)` rule applied to *every* timeframe, including daily and weekly.
  - Staleness rule: the last closed bar must be within N bars of the calendar's expected last close, else a data-quality failure.
- **If not adopted:** Intermittent, hard-to-reproduce analysis on partial bars; misaligned multi-timeframe evidence.
- **Confidence:** High on the arithmetic and the need; session hours Medium (verify).

### B5. Setup-quality score has no methodology and a misleading default

- **EDD:** §4.4, §4.5, §8.2, §9.4, §12.1 (`minimum_setup_quality: 70`), §20 Q11
- **Issue:** A 0–100 number with a default threshold of 70 will be read as a probability regardless of labeling. The EDD's own principle (§4.5) forbids this, and the example request quietly violates it. No components, weights or validation exist.
- **Recommendation:** **Do not ship a scalar score in V1.** Use a deterministic **setup checklist of named gates**, each pass/fail/unknown with a reason: higher-timeframe bias aligned; trigger present on primary timeframe; risk/reward at least the user minimum; stop distance within an ATR band; volume/liquidity adequate; data quality clean; no unresolved timeframe conflict. Show "x of y gates passed" with the list. If a scalar is wanted, define named components with documented weights, version it, show the breakdown, label it "heuristic, uncalibrated", and drop the default threshold.
- **If not adopted:** Pseudo-precision that users treat as probability; arbitrary weights nobody can defend.
- **Confidence:** High (judgment).

### B6. Candidate providers' authentication conflicts with §14

- **EDD:** §14, §2.2, §13.1.5
- **Issue:** Broker-API providers such as Angel One SmartAPI typically require brokerage client ID, PIN/password and a TOTP secret or code, with daily token expiry **\[UNVERIFIED\]**. Upstox uses OAuth with short-lived tokens **\[UNVERIFIED\]**. Either way the app holds brokerage-linked credentials, contradicting §14 ("avoid collecting personal financial account credentials"), and a Settings screen that collects them (§13.1.5) is a significant security surface.
- **Recommendation:** Decide explicitly. (a) Accept brokerage-linked credentials, stored only via environment/secrets manager, never entered in the UI, never logged, using a read-only/market-data-only key where the provider offers one; or (b) choose a data-only vendor with API-key auth. Remove credential entry from the V1 Settings UI.
- **If not adopted:** Security posture contradicts stated principles; harder to ever host or share.
- **Confidence:** Medium (pattern well known; specifics unverified).

### B7. Regulatory and usage posture is not stated

- **EDD:** §1, §1.2, §3.1, §4.6
- **Issue:** The product emits directional recommendations with entries, stops and targets. Whether it is personal analysis tooling or something that could fall under SEBI's investment-adviser or research-analyst regimes depends on whether it is offered to third parties, charged for, or distributed **\[UNVERIFIED; I am not a lawyer\]**. Exchange data terms may also restrict display or redistribution.
- **Recommendation:** State in the EDD that V1 is a single-user personal-use tool and that any hosting or sharing is gated by legal and data-licensing review. Add a standing disclaimer to reports and a decision-log entry.
- **If not adopted:** A hosted multi-user release could be built before anyone checks whether it can be offered.
- **Confidence:** Medium that it needs deciding; Low on specifics.

## 3. High-priority improvements

All are SHOULD FIX unless noted.

### H1. LLM selects deterministic candidate levels instead of inventing prices

- **EDD:** §9.1, §9.3, §10 · **Strongly recommended**
- **Issue:** The EDD lets the LLM formulate candidate levels, then validates them. Validation catches geometry errors, not plausible-but-arbitrary levels that satisfy geometry.
- **Recommendation:** The quant engine emits a **candidate level set** with IDs and provenance (e.g. `L-S1` confirmed swing low, `L-ATR2` entry − 1.5×ATR, `L-R1` prior resistance, `L-PIV` pivot). The LLM refers to level IDs (optionally with a bounded offset in ticks or ATR units) for entry zone, stop and targets. The validator verifies and computes R/R from the referenced levels. Free-form numeric levels are rejected.
- **Why:** A hallucinated price becomes a schema impossibility, prompts and outputs shrink, and every level is traceable to evidence.
- **If not adopted:** More validator rejections and repair calls, and plausible but unanchored stops.
- **Confidence:** High (judgment).

### H2. Plain typed pipeline instead of LangGraph

- **EDD:** §2.2, §9.5, §6.3. See D-1 in section 5.

### H3. Async job/status model from day one, no queue

- **EDD:** §12, §20 Q13
- **Issue:** One analysis involves several provider calls (chunking, rate-limit waits) plus an LLM call. Latency is plausibly tens of seconds (judgment; benchmark), risking gateway and browser timeouts. The EDD already has `analysis_request`/`analysis_run` and `GET /analyses/{id}`.
- **Recommendation:** `POST /analyses` returns `202` with `analysis_id` and requires an `Idempotency-Key`. Run it as an in-process `asyncio` task (no broker). The UI polls `GET /analyses/{id}` (or SSE for stage progress). On startup, mark any `RUNNING` rows `FAILED(interrupted)`. Add a per-run wall-clock budget and a cancel endpoint.
- **Trade-off:** Slightly more UI work than a blocking call, but changing a synchronous contract to async later breaks clients and tests.
- **Confidence:** Medium-High.

### H4. Lookahead-safe swing and structure features by construction

- **EDD:** §4.3, §5.1, §8.1 · MUST FIX for any later backtesting
- **Issue:** Swing highs/lows, support/resistance, BOS/CHOCH, Fibonacci anchors and many patterns are only *confirmable* k bars after they occur. Computing them over the full window and handing them to the LLM as present facts presents unconfirmed swings as confirmed. Ichimoku's lagging-span shift is another trap.
- **Recommendation:** Every structural feature carries `occurred_at` and `confirmed_at`. Features not confirmed at `as_of` appear only as `tentative`. The golden test suite includes a "truncate history at t, recompute, assert identical" property test for every indicator and feature.
- **If not adopted:** Systematic overconfidence in structure; future backtests invalid.
- **Confidence:** High.

### H5. Instrument identity: opaque ID, ISIN, alias history, provider tokens

- **EDD:** §4.1, §12.1 (`"NSE:RELIANCE"`), §20 Q5
- **Issue:** `NSE:RELIANCE` is a ticker string, which §4.1 says not to rely on. Symbols change, series differ (EQ/BE/etc.), companies are dual-listed, and provider identifiers are provider-specific **\[UNVERIFIED\]**.
- **Recommendation:** `instrument` (opaque internal ID, ISIN, exchange, segment/series, status) + `instrument_alias` (symbol, valid\_from/valid\_to) + `provider_instrument_map` (provider, key, valid range). ISIN is useful but not infallible (it can change on certain corporate actions) **\[UNVERIFIED in detail\]**. The API accepts the internal ID only; search returns candidates. Pick a primary listing for dual-listed companies and state which exchange's data an analysis used.
- **If not adopted:** Wrong-instrument data after symbol changes; broken history links.
- **Confidence:** Medium-High.

### H6. Resolve "no scheduled jobs" for reference data

- **EDD:** §1.2, §7.4, §2.3
- **Issue:** The instrument master and exchange calendar need periodic refresh. Without a scheduler they go stale silently, breaking "is this bar complete?" and symbol resolution.
- **Recommendation:** Lazy refresh with staleness metadata: check at startup and request time; if older than a threshold, refresh inline or fail with a clear message. Store `reference_data_version` and `fetched_at` in provenance.
- **If not adopted:** Stale calendar or master causing mis-flagged candles or unresolvable symbols.
- **Confidence:** High.

### H7. Adapter request-budget and chunking layer

- **EDD:** §5.3, §7.1–7.2
- **Issue:** Providers cap candles or days per historical request and impose per-second and per-minute limits **\[UNVERIFIED specifics\]**. The example request (15m×20d, 1h×60d, 1d×1y) may need several chunks per timeframe, and chunk boundaries create duplicate or missing bars. Concurrent timeframes plus chat-triggered analyses contend for one rate limit and one session token.
- **Recommendation:** A per-provider token-bucket limiter and single-flight session/token manager inside the adapter. The adapter owns chunking, stitching, de-duplication and truncation detection, and returns one verified batch. Add a pre-flight check of estimated request count against the capability model, failing early with "lookback X unsupported for interval Y".
- **If not adopted:** Throttling failures; truncated history presented as complete.
- **Confidence:** Medium-High.

### H8. Direction × horizon × instrument constraint matrix before the validator

- **EDD:** §4.4, §10
- **Issue:** The EDD warns against generic shorting assumptions but still offers SHORT across intraday/swing/positional horizons. In Indian cash equities, shorting is commonly limited to intraday (same-day square-off), and delivery-based short selling is not generally available to retail **\[UNVERIFIED; verify with exchange, regulator and broker\]**. A swing or positional SHORT on a cash equity may be non-actionable.
- **Recommendation:** A versioned, data-driven table `(segment, horizon, direction) → allowed | not_actionable | requires_derivatives`. A bearish view at a non-actionable combination becomes `NO_TRADE` with `bias=BEARISH` and reason `short_not_actionable_in_cash_segment`. Keep bearish *analysis* separate from an actionable SHORT.
- **If not adopted:** Non-actionable trade plans delivered with a validated stamp.
- **Confidence:** Medium on the market rule; High on needing the table.

### H9. Instrument-quality and event gates before the LLM

- **EDD:** §10, §7.4
- **Issue:** Indian equities have price bands/circuit limits, surveillance-stage restrictions, illiquid names and large overnight gaps around results **\[UNVERIFIED specifics\]**. A stop in a circuit-locked or illiquid stock cannot be assumed executable, and a swing setup straddling earnings is a different risk class.
- **Recommendation:** Pre-LLM gates: minimum average traded value over N days; zero-volume bar ratio; circuit/band status where exposed; stop distance versus the typical overnight gap distribution; an `event_risk` field (earnings date if obtainable, otherwise an explicit "unknown event calendar" caveat in the report).
- **If not adopted:** Stops that are fictions in illiquid or gapping names.
- **Confidence:** Medium.

### H10. Short-circuit before the LLM when data or gates fail

- **EDD:** §3.2, §9, §10
- **Recommendation:** If data quality fails hard policy (B3, B4), emit a deterministic NO\_TRADE report with reasons and do **not** call the LLM. If checklist gates fail, optionally call the LLM only for explanation (cheaper model), constrained to the deterministic verdict.
- **If not adopted:** Cost, and persuasive prose around invalid data.
- **Confidence:** High.

## 4. Deferred improvements

Ten items are useful but not needed for V1.

| ID | EDD § | Item | Severity | Rationale |
| --- | --- | --- | --- | --- |
| DF-1 | §4.3 | Volume Profile, Ichimoku, Keltner, Donchian, Fibonacci, CHOCH/BOS, WMA, VWMA, CCI, ROC, Williams %R, MFI, CMF | DEFER | Correlated or subjectively defined; each adds definition, fixture and review burden. Minimum set in section 9. |
| DF-2 | §3.2, §13.1.3 | Report comparison UI | DEFER | History list and view suffice for V1. |
| DF-3 | §9.6 | Multi-model benchmark harness beyond a small eval set | DEFER (build the small set now) | A versioned 20–40 case golden set is enough. |
| DF-4 | §2.3 | Caching | DEFER | Agree with the EDD; measure first. |
| DF-5 | §2.3 | Backup provider / failover | DEFER | Keep the interface; do not build failover. |
| DF-6 | §4.2 | 1m, 3m, 10m, 4h timeframes | DEFER | Highest noise and boundary risk (B4). |
| DF-7 | §15.4 | Backtesting vs paper trading | DEFER | Agree. Backtesting will need point-in-time historical data that V1's design does not provide. |
| DF-8 | §14 | Multi-user auth, CSRF/cookie design | DEFER | Gated on the hosting decision. |
| DF-9 | §11.1 | Chat history persistence beyond the current session | DEFER / OPTIONAL | See section 6, item 7. |
| DF-10 | §5.4 | Full Prometheus/OpenTelemetry stack | DEFER | Structured logs plus per-run rows in `model_invocation` / `analysis_run` suffice. |

## 5. Disagreements and alternatives

### D-1. Plain Python pipeline over LangGraph and Google ADK (SHOULD FIX)

- **EDD:** §2.2, §6.3, §9.5, §20 Q2
- **Assessment (judgment):**
  - The workflow is linear: resolve, fetch, validate, compute, synthesize, *one* LLM call, validate, persist. Per-timeframe parallelism is `asyncio.gather`. The only branch is "short-circuit on data failure". None of this needs a graph runtime.
  - LangGraph's real strengths are durable checkpointed execution, human-in-the-loop interrupts, long-running agent loops and streaming of intermediate state. V1 needs none of these. Its costs are a heavy dependency surface, API churn **\[UNVERIFIED current state\]**, state-schema coupling and harder debugging than a call stack.
  - Google ADK is built around agent workflows with first-class Gemini/Vertex integration, and supports other models through adapters **\[UNVERIFIED current capabilities\]**. For a deterministic pipeline with one reasoning call it adds more concept overhead than LangGraph and a stronger pull toward one ecosystem. It is not warranted for V1.
  - Neither is *needed*: EDD §6.3 already requires the application to be useful and testable without one.
- **Recommendation:** An `AnalysisPipeline` class with typed stage functions (`Stage[In, Out]`), an explicit `RunContext` (as\_of, correlation ID, budgets) and a result object recording stage timings and outcomes. Keep stage boundaries clean enough that wrapping them as LangGraph nodes later is mechanical.
- **Chat:** The one genuine agent loop is chat (decide, call `get_report` / `run_analysis` / `get_evidence`, answer). Implement it as a small bounded tool-calling loop (max N calls, a closed tool set) on the provider-neutral LLM interface. This still does not require a graph framework.
- **Revisit LangGraph if:** durable resume after crash, human approval gates, measured multi-agent benefit, or long-running scheduled analyses become real requirements.
- **If not adopted:** Extra dependency and abstraction with no V1 benefit, and some risk of domain logic leaking into node functions despite §6.3.
- **Confidence:** High that no framework is needed; Medium on framework-specific characterizations (unverified).

### D-2. PostgreSQL vs SQLite for a local-first single-user V1 (OPTIONAL)

- **EDD:** §2.2, §11, §16
- If V1 is truly single-user local, SQLite via SQLAlchemy removes a container and all V1 data is small. PostgreSQL is better if hosting or multi-user is likely soon (JSONB, constraints, migrations). Since Docker Compose is already planned, keeping PostgreSQL is defensible. De…340 tokens truncated…ge-local session dates (a `session_date` field), not midnight UTC conversion, a classic off-by-one-day source. IST has no DST today, so the EDD's DST test requirement (§7.5) is mostly about not hardcoding +05:30 arithmetic. **Confidence:** High.

### D-6. Exchange calendar source (SHOULD FIX)

- **EDD:** §7.4, §20 Q6
- Use a maintained calendar library as a baseline (e.g. `exchange_calendars` or `pandas_market_calendars`; confirm NSE/BSE coverage **\[UNVERIFIED\]**), plus a **versioned override table** for special sessions (Muhurat trading, ad-hoc Saturday sessions) and late-announced holidays. Add a self-check: if the calendar says "closed" but the provider returns bars (or vice versa), raise a calendar-conflict warning. Exchange circulars remain authoritative. Represent sessions as `(session_date, open_ts, close_ts, session_type)` with `session_type` in `NORMAL | SPECIAL | MUHURAT | HALF`. **Confidence:** Medium.

### D-7. Technical-analysis library choice (SHOULD FIX)

- **EDD:** §2.2, §8.4
- Implement the small V1 indicator set **in-house** in NumPy/pandas with exact documented definitions, and use a mature reference (e.g. TA-Lib, if installable on the target platform **\[UNVERIFIED\]**) *only as a dev-time test oracle*. Libraries disagree on Wilder smoothing vs EMA seeding and NaN handling, so "RSI(14)" differs by library, and several popular pandas-based TA packages have had uncertain maintenance **\[UNVERIFIED current status\]**. Recursive smoothers (RSI, ATR, ADX) need roughly 5–10× the period of history before seeding effects fade, so the engine should require `lookback >= warm_up + analysis_window` and report the effective valid range. **Confidence:** High on the approach; Low on package statuses.

### D-8. LLM provider chosen per request (OPTIONAL)

- **EDD:** §3.2 step 5, §4.5
- Make the model a configuration-level choice in V1, not a per-request UI control. Per-request choice multiplies the evaluation matrix (§9.6) with no validated benefit. Keep the abstraction and the `model_invocation` record.

### D-9. Analysis depth and custom instructions (SHOULD FIX: define or drop)

- **EDD:** §4.4
- Define what depth changes (indicator count, prompt size, number of scenarios). If it only changes verbosity, drop it. Custom instructions are a prompt-injection and validator-bypass vector (§14): treat them as untrusted text in a clearly delimited, lower-priority slot, length-capped, never able to alter schema, gates or the validator. State this in the EDD.

### D-10. Module structure (OPTIONAL)

- **EDD:** §17
- Drop `orchestration/` as a separate top-level package if D-1 is adopted (it duplicates `application/workflows/`). Consider a top-level `quant` package with zero imports from `api`, `persistence` or `providers`, enforced with an import-linter style check in CI. Otherwise the layout is reasonable for a modular monolith, and I see no missing or excessively granular modules beyond this.

## 6. Missing requirements and open questions

1. **Single-user vs multi-user, and hosting** (§2.3). It drives auth, database choice, legal posture and data-licensing exposure. Decide now, even if implementation is deferred (B7).
2. **Regulatory and licensing posture** (B7).
3. **LLM data egress:** derived market data goes to a third-party LLM. Check the data provider's terms on passing derived data to third parties **\[UNVERIFIED\]**, and the LLM vendor's retention and training terms.
4. **Cost budget and caps:** per-analysis token ceiling, per-day spend cap, and behavior at the cap (§14 mentions rate limits but not budgets).
5. **Evidence-package schema and size:** the contract between quant output and the LLM is the heart of the system, yet the EDD has no schema for it. Define `EvidencePackage` early (per-timeframe regime, indicator readings with semantic labels, structural levels with IDs, conflict matrix, data-quality flags); its size drives cost and quality.
6. **Evaluation set ownership:** who builds the golden cases, how many, and how WAIT/NO\_TRADE behavior is judged (§9.6). Tie it to an acceptance criterion.
7. **Chat scope** (§3.3, §20 Q14): V1 chat answers questions grounded in a saved report's evidence package. Triggering a new analysis from chat requires an explicit confirmation step (cost and quota). Questions needing fresh data ("what's RSI now?") go through the shared service with a stated as-of, never answered from memory. Persist chat per report session, minimally; bound context to the evidence package plus the last N messages.
8. **Timezone, locale and currency display** (INR formatting, IST rendering).
9. **Data retention and deletion policy**, and a DB backup approach even for local use.
10. **Clock correctness:** an NTP assumption for the host, and `as_of` derived from a single clock source.
11. **Disclaimers and "not advice" copy** in every report and chat reply (§1.2).
12. **User-visible error taxonomy:** unsupported lookback, instrument suspended, stale data, calendar conflict, provider throttled, LLM schema failure.
13. **Accessibility and mobile** for the frontend: likely OPTIONAL for V1, but state the position.
14. **Fundamental and news inputs:** explicitly out of V1. Say so, and have the LLM prompt forbid referencing news or fundamentals it was not given.

## 7. Financial and market-data correctness risks

Eighteen concrete failure scenarios, each with a mitigation.

| # | Risk | Failure scenario | Mitigation | EDD § | Severity |
| --- | --- | --- | --- | --- | --- |
| F1 | Unadjusted history across split/bonus | A 1:5 split appears as an \~80% crash; ATR explodes; false breakdown | B3 policy, discontinuity detection, fail closed | §7.3–7.4 | MUST FIX |
| F2 | Partial bar treated as closed | 15m analysis at 11:10 uses an incomplete 1h bar; RSI differs from the later final value | B4 as-of rule applied to all timeframes | §4.2, §8.3 | MUST FIX |
| F3 | Session-misaligned aggregation | 1h bars built from 15m without aligning to 09:15 give 09:00/10:00 buckets spanning pre-open | Session-anchored buckets; aggregate only from validated complete base data; consider no aggregation in V1 | §4.2, §7.5 | MUST FIX |
| F4 | 4h and 10m do not tile the session | Stub bars distort volatility and indicator inputs | Drop 4h/10m for V1 or define stub handling | §4.2 | SHOULD FIX |
| F5 | Pivot/structure lookahead | "Confirmed" swing low is just the latest bar's minimum; stop placed at an unconfirmed level | H4 `confirmed_at`, truncation property test | §4.3, §8.1 | SHOULD FIX |
| F6 | Indicator definition drift | Wilder vs EMA RSI; insufficient warm-up; library upgrade shifts values | In-house versioned implementations, oracle tests, warm-up enforcement | §8.4 | SHOULD FIX |
| F7 | VWAP misuse | Session VWAP computed over multiple days, or applied to daily bars | VWAP only on intraday, anchored per session; refuse otherwise | §4.3 | SHOULD FIX |
| F8 | Volume semantics | Provider volume may be exchange-specific or delayed; zero-volume bars in illiquid stocks distort OBV/MFI | Record volume source in provenance; zero-volume ratio gate | §7.2, §7.4 | SHOULD FIX |
| F9 | Dual-listing confusion | NSE and BSE price/volume mixed in one analysis | One exchange per analysis, stated in the report | §4.1 | SHOULD FIX |
| F10 | Gap/slippage vs stop | Overnight gap through the stop; risk understated | Gap-risk gate (H9); state that a stop is not a guaranteed exit | §10 | SHOULD FIX |
| F11 | Entry far from last close | LLM entry zone 4% from last price labelled valid; fill unlikely | Validator rule: entry distance in ATR units from last close; classify as conditional/limit setup | §10 | SHOULD FIX |
| F12 | Tick/price-band violations | Levels off the tick grid or outside the circuit band | Tick rounding; circuit-band check where data exists | §10 | SHOULD FIX |
| F13 | Provider revisions | History re-adjusted later; report no longer matches data | B2 Tier B snapshot, or an explicit non-reproducibility statement | §11.3 | MUST FIX |
| F14 | Survivorship in future evaluation | Evaluation only on currently listed names | Defer, but record in the evaluation design | §9.6, §15.4 | DEFER |
| F15 | Correlated-indicator double counting | RSI, Stochastic, Williams %R and CCI treated as independent confirmations | Cap one signal per indicator family; minimal set (section 9) | §8.3 | SHOULD FIX |
| F16 | Regime blindness | Trend-following applied in a range; mean-reversion in a trend | Explicit regime feature (ADX/ATR-percentile) feeding the strategy gate | §4.6, §8.2 | SHOULD FIX |
| F17 | LLM confidence leakage | Report text says "high probability" | Output schema has no probability field; post-filter prose for probability language; UI copy | §4.5, §9.4 | SHOULD FIX |
| F18 | Stale instrument status | Suspended or delisted symbol returns old candles | Status check plus staleness gate | §4.1 | SHOULD FIX |

### Provider spike checklist

Verify from official sources and hands-on; everything below is currently **\[UNVERIFIED\]**. Candidates: Angel One SmartAPI, Upstox, TejHQ, and optionally an EOD-only official source such as NSE's published end-of-day files.

1. Is market-data API access free or paid today, and what account is required?
2. Authentication flow, credential type, token lifetime, and whether automation is permitted.
3. Exchanges, segments and instruments covered; instrument-master format and refresh cadence.
4. Supported intervals; maximum bars or days per request per interval; total history depth per interval.
5. Rate limits (per second, minute, day) and behavior on breach.
6. Adjustment semantics for daily and intraday data; behavior around a known recent split or bonus.
7. Timestamp convention (open vs close, timezone), volume source, and whether the current bar is included and flagged.
8. Latency between bar close and availability.
9. Terms: personal vs commercial use, storage and caching, display, derived-data sharing, passing data to third-party AI services, redistribution.
10. Reliability and parity against a second source on 3 symbols × 3 intervals × 30 sessions.

Outcome: an ADR with the chosen provider, the V1 supported-interval list and the Tier B retention permission.

**Practical caution (judgment):** Unofficial scrapers of NSE data are widely used by hobbyists but generally rely on unsanctioned access and unstable endpoints. I would not build V1's data layer on one, though one might serve as a throwaway *comparison* source during the spike if its terms allow.

**Possible scope simplification (judgment):** If no suitable intraday source passes the spike, V1 can ship on 1d/1w (and perhaps 1h) only. The architecture is unchanged, and the report must say what it does not cover.

## 8. Security and operational risks

Thirteen findings; the credential decision (S1) is the only one that blocks design.

| # | Finding | EDD § | Severity | Recommendation | Confidence |
| --- | --- | --- | --- | --- | --- |
| S1 | Brokerage-linked credentials (B6) | §14 | MUST FIX (decision) | Env/secret store only, no UI entry, never logged, read-only keys where possible | Medium |
| S2 | Local-first still needs a safe default | §14, §20 Q16 | SHOULD FIX | Bind to `127.0.0.1`, strict CORS allow-list, a static API token or session even locally, Compose ports not exposed on all interfaces, no default DB password | High |
| S3 | LLM cost and abuse | §14 | SHOULD FIX | Per-run token cap, daily spend cap, request-size caps (lookback × indicators × timeframes), concurrency limit | High |
| S4 | Prompt-injection surface | §14 | SHOULD FIX | Narrower than the EDD implies: V1 data inputs are numeric, so injection mainly enters via custom instructions and chat. Delimit user text, forbid it from modifying schema/gates, schema-validate output, escape rendered output (XSS) | Medium-High |
| S5 | Stored prompts and responses | §11 | SHOULD FIX | Store them (needed for audit); they hold only derived evidence plus user text. Keep secrets out of prompts; redact logs | High |
| S6 | In-process async jobs lose state on restart | H3 | SHOULD FIX | Startup sweep marking `RUNNING` as `FAILED(interrupted)`; idempotency keys | High |
| S7 | One provider session shared across requests | H7 | SHOULD FIX | Single-flight token refresh; avoid parallel logins invalidating each other | Medium |
| S8 | Partial-failure semantics | §5.3 | SHOULD FIX | If a *context* timeframe fails, proceed with a flagged degraded report; if the *primary* fails, NO\_TRADE. Record per-timeframe status in the report | High |
| S9 | Retry on non-idempotent calls | §5.3 | OPTIONAL | Provider history reads are idempotent; LLM calls cost money. Bound retries and count them in cost | High |
| S10 | Supply chain (Python + JS dependencies) | §16 | SHOULD FIX | Lockfiles (`uv.lock`, package lock), dependency audit in CI, minimal frontend dependencies | High |
| S11 | Logging of user prompts and financial intent | §5.4 | OPTIONAL | Document what is logged; set a retention window | Medium |
| S12 | Observability scale | §5.4 | DEFER | Structured logs, correlation ID and DB rows for run/stage/invocation metrics are enough | High |
| S13 | Backups and data deletion | §11.2 | SHOULD FIX | Document DB backup and a delete-report path; purge Tier B snapshots by TTL | Medium |

## 9. Simplification opportunities

1. **Orchestration framework to plain pipeline** (D-1). Removes a major dependency.
2. **Merge `analysis_request` and `analysis_run`** into one `analysis` row for V1 (1:1 in practice), keeping `status`, timings and correlation ID on it. Keep `data_provenance` per timeframe, `analysis_evidence`, `analysis_report` and `model_invocation`; chat tables are optional.
3. **Config snapshot as one JSONB column** with `schema_version`, rather than normalized settings tables.
4. **Trim the V1 indicator and structure catalog** (EDD §20 Q9). Proposed minimum:
   - Trend: SMA, EMA, ADX (+DI/−DI); Supertrend later.
   - Momentum: RSI and MACD; add Stochastic only if justified.
   - Volatility: ATR, Bollinger Bands.
   - Volume: volume ratio vs rolling median, OBV, intraday session-anchored VWAP.
   - Structure: confirmed swing highs/lows, support/resistance from clustered confirmed pivots, regime classification (trending/ranging via ADX and ATR percentile), previous day/week high-low and pivot points.
   - Patterns: engulfing, hammer/shooting star, doji, each with a written numeric definition, flagged as low-weight context.
   - Defer: BOS/CHOCH (subjective), Ichimoku, Volume Profile, Fibonacci, Keltner/Donchian, WMA/VWMA, CCI/ROC/Williams %R/MFI/CMF.
5. **Reduce timeframes to those with native provider support and clean session tiling** (e.g. 5m, 15m, 1h, 1d, 1w), and avoid aggregation in V1 where possible (F3).
6. **Cut:** credential-entry UI, per-request model picker, report comparison, and depth tiers unless defined (D-8, D-9, DF-2).
7. **Observability** via logs plus DB metrics (S12).
8. **Chat:** report-grounded Q&A first; fresh analysis only via explicit confirmation (section 6, item 7).
9. **Skip Redis/Celery** (agreed). In-process async tasks are enough (H3).

## 10. Proposed revised architecture

Still a modular monolith: FastAPI returns `202` with status polling and an idempotency key, application services (`CreateAnalysis`, `GetAnalysis`, `GetReport`, `AskReportQuestion`) call one plain typed `AnalysisPipeline`, and the UI and chat read the saved report.

1. **Resolve instrument** (instrument, alias and provider map).
2. **Establish `RunContext`** (as\_of UTC, correlation ID, budgets).
3. **Fetch via `MarketDataProvider`** (adapter owns auth, rate limit, chunking, stitching).
4. **Normalize to `CandleBatch`** (UTC bar open/close, adjustment basis, provenance).
5. **Validate** (OHLC, duplicates, gaps vs calendar, partial bars, corporate-action discontinuity, staleness). **Hard fail: emit a deterministic NO\_TRADE report and skip the LLM.**
6. **Quant engine, per timeframe in parallel** (`asyncio.gather`): indicators, patterns, confirmed structure, regime, candidate levels with IDs.
7. **Multi-timeframe synthesis** (hierarchy rules, conflict matrix, one signal per indicator family).
8. **Pre-LLM gates / setup checklist** (liquidity, event caveat, direction × horizon matrix).
9. **LLM reasoning, one call:** selects candidate level IDs and explains; no probability field.
10. **Deterministic risk validator** (geometry, tick grid, R/R by code, entry distance, diff log).
11. **Persist** report, evidence, prompt/response and provenance, plus the Tier B snapshot if permitted.

Key changes versus the EDD:

- No LangGraph; an explicit `RunContext` with a single as-of.
- Candidate-level generation in the quant engine; the LLM selects by ID.
- Deterministic short-circuit before the LLM.
- Gate checklist replaces the scalar score.
- Tier A/B persistence.
- Reference data (calendar, instrument master) with lazy refresh and versioning.

## 11. Suggested schema and API changes

These are illustrative shapes for the next EDD revision, not code to implement.

### 11.1 Canonical models

```text
CandleBatch
  batch_id, instrument_id, provider, provider_request_ids[], retrieved_at (UTC),
  timeframe, requested_start/end, actual_start/end, bar_count,
  adjustment_basis, volume_source, content_sha256, quality_summary{...}, calendar_version

Candle  (key: instrument_id, timeframe, bar_open_ts_utc, adjustment_basis)
  bar_open_ts_utc, bar_close_ts_utc, session_date,
  open, high, low, close: Decimal,  volume: int | None,
  is_complete: bool, is_stub_bar: bool

Instrument / InstrumentAlias / ProviderInstrumentMap   (see H5)

Level (candidate)
  level_id, kind {SWING_LOW, SWING_HIGH, SR_CLUSTER, ATR_STOP, PIVOT, PDH, PDL, ...},
  price, timeframe, derived_from (evidence ids), confirmed_at, tick_rounded

EvidenceItem
  evidence_id, timeframe, family {TREND, MOMENTUM, VOLATILITY, VOLUME, STRUCTURE, PATTERN},
  name, params, value(s), interpretation_label, valid_from_bar, confirmed_at, impl_version
```

### 11.2 Persistence (V1 minimal)

- `analysis` (merged request/run): id, instrument\_id, status, as\_of, config\_snapshot JSONB (+ schema\_version), engine\_version, indicator\_catalog\_version, correlation\_id, timings, error.
- `data_provenance` (per timeframe, CandleBatch metadata) and optional `candle_snapshot` (Tier B; zstd Parquet/JSONB; `expires_at`).
- `analysis_evidence` and `analysis_report` (immutable; a re-run creates a new analysis with `parent_analysis_id`).
- `model_invocation`: provider, model, prompt\_version, params, rendered\_prompt, raw\_response (compressed), tokens, cost, latency, parse/repair attempts.
- `reference_data_version`: calendar and instrument-master versions and fetched\_at.
- `chat_session` / `chat_message`: optional, tied to a `report_id`.

### 11.3 API changes

- `POST /api/v1/analyses` returns `202 {analysis_id, status_url}`, requires an `Idempotency-Key`, and takes the opaque internal `instrument_id`.
- `GET /api/v1/analyses/{id}` returns `status` in `QUEUED | FETCHING | VALIDATING | COMPUTING | REASONING | VALIDATING_PLAN | COMPLETE | FAILED | CANCELLED`, per-timeframe status, and `report_id` when complete.
- `POST /api/v1/analyses/{id}/cancel`.
- `GET /api/v1/reports/{id}/candles?timeframe=` serves the Tier B snapshot for charts; 404 with an explicit reason if not retained.
- `GET /api/v1/reference-data/status` reports calendar and instrument-master freshness.
- Request: replace `minimum_setup_quality` with `required_gates` or a named profile; add a server-set `as_of` (returned); `data_policy` gains `max_staleness_bars` and `adjustment_policy`.
- Report: `verdict`, `bias`, `actionability`, `gates[]` (name, status, reason), `levels_used[]` (IDs), `validator{outcome, findings[], diffs[]}`, `caveats[]`, `data_quality{}`, and no probability field.

## 12. Prioritized action list

Actions 1 to 7 are MUST FIX and gate Phase 1; the rest can proceed in parallel with spec work.

| # | Action | Ref | Severity | Effort / impact | Decision needed |
| --- | --- | --- | --- | --- | --- |
| 1 | Provider spike and ADR (checklist in section 7) | B1 | MUST FIX | M / Very high | Provider, V1 interval set, retention permission |
| 2 | Decide single-user personal-use scope and the legal/licensing gate | B7, §6.1 | MUST FIX | S / Very high | Owner |
| 3 | Decide credential handling model | B6 | MUST FIX | S / High | Brokerage-linked credentials or data-only vendor |
| 4 | Adopt Tier A/B persistence; solve chart/history | B2 | MUST FIX | M / High | Retain candle snapshots or not |
| 5 | Specify adjustment basis and corporate-action policy | B3 | MUST FIX | M / Very high | Fail closed vs truncate |
| 6 | Specify bar, timestamp, as-of and staleness conventions; drop 4h/10m | B4 | MUST FIX | M / Very high | Timeframe list |
| 7 | Replace scalar score with gate checklist | B5 | MUST FIX | S / High | Score or checklist |
| 8 | LLM selects candidate level IDs | H1 | SHOULD FIX | M / High | None |
| 9 | Plain pipeline instead of LangGraph/ADK | D-1 | SHOULD FIX | S / Medium | Confirm |
| 10 | Async 202 job model with idempotency | H3 | SHOULD FIX | S–M / High | None |
| 11 | Lookahead-safe structure (`confirmed_at`) and truncation property tests | H4 | SHOULD FIX | M / High | None |
| 12 | Instrument identity model | H5 | SHOULD FIX | M / High | None |
| 13 | Reference-data lazy refresh and versioning | H6, D-6 | SHOULD FIX | S–M / High | Calendar source |
| 14 | Adapter rate-limit and chunking layer | H7 | SHOULD FIX | M / Medium-High | None |
| 15 | Direction × horizon × segment constraint table | H8 | SHOULD FIX | S / High | Verify rules |
| 16 | Liquidity, gap and event gates | H9 | SHOULD FIX | M / Medium | None |
| 17 | Deterministic short-circuit before the LLM | H10 | SHOULD FIX | S / Medium | None |
| 18 | In-house indicators with oracle tests; trimmed catalog | D-7, §9 | SHOULD FIX | M / High | Catalog scope |
| 19 | Price, timestamp and key conventions | D-3 to D-5 | SHOULD FIX | S / High | None |
| 20 | Security baseline for local-first | S2–S4, S10 | SHOULD FIX | S / Medium | None |
| 21 | Define or drop depth tiers; constrain custom instructions | D-9 | SHOULD FIX | S / Low-Medium | None |
| 22 | Postgres vs SQLite decision | D-2 | OPTIONAL | S / Low | Hosting plan |
| 23 | Deferred items (section 4) | None | DEFER | None | None |

## Five decisions the project owner must make before implementation

1. **Provider and data rights:** which provider(s), under what terms, and whether per-report candle snapshots may be retained and sent (as derived data) to an LLM vendor. This is the output of the spike.
2. **Usage scope:** a strictly single-user personal tool for V1, or a product that may be hosted for others. This determines legal review, data licensing, authentication and database choice.
3. **Credential model:** whether the app may hold brokerage-linked credentials, or only a data-only API key.
4. **Reproducibility target:** Tier A (auditability) only, or Tier A plus Tier B snapshots (needed for faithful chart and history rendering).
5. **Scoring and trade-plan contract:** gate checklist versus heuristic score, and whether the LLM selects deterministically generated level IDs (my recommendation) or proposes free-form levels.

A close sixth: the timeframe list and session-tiling policy, with the corporate-action fail-closed policy. These fall out of the provider spike but need an explicit decision.

## Verdict

**Not ready to start building yet, but close.** The architecture is sound in its principles and boundaries, and the modular-monolith shape is right. Once the five decisions above and the MUST FIX items B1–B7 are resolved, the design can proceed to Phase 1. The recommended simplifications (plain pipeline, trimmed catalog, gates instead of a score, no credential UI) make V1 more achievable and more defensible. Re-review the amended EDD (v0.2) briefly against the provider ADR before Phase 2, since the market-data section will change the most.

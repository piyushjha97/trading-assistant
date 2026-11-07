Warning: truncated output (original token count: 12066)
Total output lines: 425

# Independent Architecture Review

**Reviewed:** 7 November 2026  
**Scope:** EDD v0.1 and `REVIEW_PROMPT.md`; architecture review only.  
**Evidence note:** External facts below were checked against official documentation available on the review date. Provider documentation can change; the selected provider's live terms and entitlements still need direct confirmation. **Confidence** describes confidence in the engineering assessment, not a market forecast.

## 1. Executive assessment

**Assessment: sound direction, not ready to implement unchanged.** The modular-monolith boundary, deterministic calculations, replaceable adapters, on-demand flow, no-order boundary, and explicit WAIT/NO_TRADE outcome are good V1 constraints. The EDD also correctly recognizes that a hash alone cannot reproduce a report and that provider terms must be checked.

There are four unresolved gates that materially change product behavior and data design:

1. **Product/regulatory boundary:** LONG/SHORT plus entry, stop, and targets is actionable securities analysis. Calling the product a decision-support tool does not itself settle applicable Indian regulatory obligations, particularly if it is offered to others or monetized.
2. **Data rights and reproducibility:** API availability and price do not establish rights to retain, display, or redistribute historical candles. A hash is not a replayable input.
3. **Market-data semantics:** Provider timestamps, candle boundaries, adjusted prices, partial bars, calendars, and identity need a normative contract before technical outputs can be trusted.
4. **Score and trade-risk meaning:** A user threshold such as 70 is not meaningful absent a defined validated scoring method. Risk/reward alone is not risk sizing or a complete risk check.

**Recommendation:** resolve these product and data decisions before Phase 1 locks schemas or Phase 2 selects the provider. Once resolved, proceed with a small synchronous modular monolith and a plain typed workflow; defer an agent framework, score, chat persistence, and most of the indicator catalog.

## 2. Critical blockers

### 2.1 Establish the product and compliance boundary before exposing trade-like verdicts

- **EDD:** §§1, 2.1, 3, 4.5–4.6, 10, 13, 14, 19.
- **Severity:** MUST FIX.
- **Issue:** The product says it is not investment advice, yet accepts a stock, direction, and risk preferences and can return LONG/SHORT with entry, stop, targets, and a thesis. These are the same outputs a user may act on. “No execution” reduces operational risk but does not answer whether the product's distribution, audience, personalization, or monetization falls within applicable regulatory requirements.
- **Why it matters:** A disclaimer or “analysis” label cannot be treated as a technical control that defines legal status. SEBI's current IA regulations define investment advice relating to investing in/purchasing/selling securities and address AI disclosure for an IA; SEBI RA rules address research reports/recommendations. Applicability depends on the product and its distribution model and needs qualified Indian regulatory review, not an engineering inference. [SEBI IA Regulations](https://www.sebi.gov.in/legal/regulations/feb-2025/securities-and-exchange-board-of-india-investment-advisers-regulations-2013-last-amended-on-february-10-2025-_92319.html), [SEBI RA Regulations](https://www.sebi.gov.in/sebi_data/attachdocs/feb-2025/1740726945457.pdf).
- **Recommended action:** Before implementation of user-facing verdicts, define whether V1 is strictly private/local research tooling or will be distributed/paid; who the users are; whether outputs are personalized; what the application calls a report; and whether LONG/SHORT or price levels will be shown. Obtain India-specific legal/compliance review and record the resulting constraints as product requirements. If scope cannot be cleared, limit the initial output to descriptive evidence and scenarios without imperative verdicts or trade plans while review is pending.
- **Consequence if not adopted:** The team may build report schemas, UI, logging, and monetization around a product promise it later cannot lawfully or safely deliver; retrofitting disclosures, suitability, recordkeeping, eligibility, or output restrictions can be expensive.
- **Confidence:** High that the product boundary is unresolved; legal applicability is intentionally not concluded here.
- **Sources:** Official SEBI regulations linked above; their existence and wording are evidence, while application to this specific product requires counsel.

### 2.2 Select a provider only after confirming usable entitlement and retention/display rights

- **EDD:** §§2.1–2.3, 7.1–7.2, 7.6, 11.2–11.3, 18 Phase 0.
- **Severity:** MUST FIX before provider-backed implementation or persisted market-data output.
- **Issue:** “Free/low-cost provider” and “provider independence” risk conflating API access with data rights. The EDD correctly lists terms verification as open, but V1 persistence and UI requirements assume data may be stored and rendered.
- **Why it matters:** NSE's published Data Sharing & Usage Policy says data use/sharing/distribution is governed by relevant agreements, that agreements specify intended use and handling, and redistribution is not permitted except as agreed. That policy does not automatically establish the terms applicable to a broker API user's data; it demonstrates why the actual provider agreement matters. [NSE Data Sharing & Usage Policy](https://www.nseindia.com/static/market-data/nse-data-policy).
- **Recommended action:** Add a provider acceptance checklist and a signed-off record for the selected account/API covering allowed purpose, personal vs commercial use, display to self/others, derived outputs, retention, deletion, caching, backups, audit, and whether exact normalized inputs may be retained. Confirm with the provider or its binding agreement; do not infer permission from endpoint availability, an API page, or an API being free. Keep license/entitlement/version identifiers in provenance. If rights do not allow candle retention, make auditability the stated goal and retain derived evidence and precise input metadata only; do not promise exact reruns.
- **Consequence if not adopted:** Reports, history, backups, or future sharing can violate data terms; alternatively the application may be unable to preserve enough evidence to explain a historical result.
- **Confidence:** High.
- **Sources:** NSE policy above. **Unverified:** Upstox and Angel One terms permitting the intended retention, display, and analysis use; no assumption is made about those permissions.

### 2.3 Specify the canonical candle contract and price adjustment policy

- **EDD:** §§4.2, 4.6, 7.3–7.6, 8.1, 8.3, 11.1–11.3, 12.1.
- **Severity:** MUST FIX.
- **Issue:** The sample candle has a timestamp and `is_complete`, but does not say whether timestamp means bar start or end, what timezone is required, what “complete” means, whether a daily candle includes auction activity, how bars are anchored, or whether prices are adjusted for corporate actions. A generic `NSE:RELIANCE` ID and `source_provider` field do not identify a listing/version of a security or a coherent retrieval batch.
- **Why it matters:** Two valid providers may label the same bar differently. A split/dividend adjustment can cause false gaps or make historical price-level comparisons invalid. Aggregating a nominal 4-hour bar over a 09:15–15:30 session yields a final partial interval; if silently treated as a normal bar, indicators and levels differ. A provider's latest revised history can also diverge from the report's input. The EDD's proposed timeframes include 4h although the cited provider candidates have different interval support.
- **Recommended action:** Approve a contract before implementing any indicator: (a) candle start instant in UTC plus exchange-local session date/timezone; (b) exchange and provider interval convention; (c) explicit half-open interval `[start,end)` and closed/partial status with determination source; (d) session-calendar ID/version and regular/pre/post/auction policy; (e) adjustment mode and adjustment-event/version; (f) canonical listing ID, ISIN where available, exchange, effective-dated provider instrument key and symbol aliases; (g) batch-level provider/request/retrieved-at metadata and per-row source identity; (h) explicit missing-vs-zero volume semantics. Define an aggregation convention, including incomplete terminal bars, or remove unsupported intervals from V1.
- **Consequence if not adopted:** A technically valid report can be computed from misaligned, mixed-adjustment, or wrongly identified data and still pass all generic OHLC checks.
- **Confidence:** High.
- **Sources:** Provider facts below establish that supported interval sets and response semantics differ; the canonical-contract recommendation is engineering judgment.

### 2.4 Remove or defer setup-quality thresholds until the scoring method is defensible

- **EDD:** §§4.4–4.5, 6.1, 8.2, 8.3, 9.3, 9.4, 12.1, 18 Phase 3, 19 criteria 5–8.
- **Severity:** MUST FIX for a user-facing score/threshold; the rest of the indicator workflow can proceed without it.
- **Issue:** The EDD disclaims calibrated probabilities appropriately, but still proposes a setup-quality score and numeric user threshold (`70`) without defining what it measures, scale, direction, weights, missing evidence policy, correlation treatment, or validation. Calling an arbitrary heuristic a “quality” score and letting it gate LONG/SHORT can recreate a misleading probability in practice.
- **Why it matters:** Indicator counts or weighted votes can double-count correlated signals and reward overfitting. A threshold can look precise without being empirically linked to any outcome.
- **Recommended action:** Remove `minimum_setup_quality` and “setup quality score” from V1 acceptance and API unless there is a documented, frozen definition, rationale for each component, fixture behavior, and evidence that the UI label is not outcome likelihood. V1 can show evidence, rule findings, data completeness, and conflicts directly. If later scoring is retained, treat it as an internal diagnostic until evaluated on a time-ordered, leakage-controlled dataset; never label it confidence or probability.
- **Consequence if not adopted:** Users may interpret a number such as 70/100 as calibrated chance or dependable setup strength, and a weakly grounded score can drive deterministic verdicts.
- **Confidence:** High.

## 3. High-priority improvements

### 3.1 Use a plain typed Python workflow initially

- **EDD:** §§2.1–2.2, 6.2–6.3, 9.5, 16–17.
- **Severity:** SHOULD FIX.
- **Issue:** The request is a mostly linear deterministic pipeline plus one bounded LLM call. There is no long-running approval loop, tool-using autonomous agent, resumable interaction, or human checkpoint that currently justifies graph runtime state.
- **Why it matters:** The primary source of correctness is explicit calculations and validation, so a workflow framework can add state/version/persistence abstractions without removing meaningful complexity. LangGraph's own docs position it as a low-level orchestration/runtime for long-running, stateful agents, with durability, streaming, and human-in-the-loop features. ADK documents sequential/parallel/loop workflows and multiple model integrations; it is a valid option if agent runtime features are required, not a reason by itself to adopt an agent architecture. [LangGraph overview](https://docs.langchain.com/oss/python/langgraph/overview), [ADK workflow agents](https://google.github.io/adk-docs/agents/workflow-agents/), [ADK model integrations](https://google.github.io/adk-docs/agents/models/).
- **Recommended action:** Implement/use-case design should begin as an ordinary application service calling typed functions in order: resolve → fetch → validate → calculate → synthesize → LLM → validate → persist. Preserve dependency interfaces and narrow typed request/result objects. Evaluate LangGraph only if a demonstrated requirement needs resumable state, conditional recovery, interactive approvals, or workflow streaming. ADK is not needed for V1 either. If one must be selected later, benchmark the actual use case for provider compatibility, state persistence, testing, observability, deployment, upgrade burden, and lock-in rather than comparing feature lists.
- **Consequence if not adopted:** More framework state and lifecycle concepts are introduced before there is agent behavior to justify them. This increases operational and migration work without improving quantitative correctness.
- **Confidence:** High. Framework capabilities are sourced above; the choice is engineering judgment.

### 3.2 Narrow V1 market-data and indicator scope

- **EDD:** §§4.2–4.3, 7.1–7.5, 8.2–8.4, 18 Phases 2–3, 19 criteria 1–6.
- **Severity:** SHOULD FIX.
- **Issue:** The candidate interval set (including 3m/10m/4h/weekly), long indicator list, charting, structure detection, and user-configurable profiles collectively imply many definitions and provider edge cases before one end-to-end path has been validated.
- **Why it matters:** Every interval and indicator adds contracts, history/warm-up requirements, numerical semantics, QA fixtures, and UI combinations. “Supported” cannot mean merely that a provider accepts a parameter.
- **Recommended action:** Make V1 a narrow vertical slice: one provider; one daily and a small number of intraday intervals actually supported; a limited, explicitly specified set such as SMA/EMA, RSI, ATR, and deterministic OHLC evidence; no broad candle-pattern catalog or volume profile. Expand from observed quality and user value. Do not claim a feature is supported until coverage, freshness, completeness, adjustment behavior, and indicator fixtures meet stated criteria.
- **Consequence if not adopted:** Scope expands combinatorially and implementation will likely substitute package defaults or provider quirks for documented, testable behavior.
- **Confidence:** High.

### 3.3 Define report provenance and choose auditability versus exact replay

- **EDD:** §§7.6, 8.1, 9.2, 11.1–11.3.
- **Severity:** SHOULD FIX.
- **Issue:** Report provenance fields do not yet capture enough to distinguish source data and reproduce *derived* values, and the EDD leaves the central retention choice open.
- **Why it matters:** A hash can verify a later matching input but cannot recreate it. Provider history may be corrected or corporate actions applied differently. Prompt/model identifiers alone also do not ensure deterministic model replay.
- **Recommended action:** Select auditability as V1's explicit target unless licensing permits more. Persist: canonical instrument/listing and effective provider key; request start/end and interval; retrieval time; provider API/version and account entitlement label; actual timestamps/counts; quality findings; adjustment/session policy versions; input hash over a canonical serialization; indicator definitions/implementation version; synthesis version; config snapshot; prompt/template version and exact model ID/parameters; validator version/findings; output schema version. Retain compact normalized candles only if the provider terms expressly permit it and a retention/deletion period is defined.
- **Consequence if not adopted:** A saved report may be explainable only from prose and not from structured evidence, while the team may accidentally claim reproducibility it cannot deliver.
- **Confidence:** High.

### 3.4 Make short-side assumptions explicit and distinguish geometry from executable risk

- **EDD:** §§4.4, 4.6, 10, 12.1.
- **Severity:** SHOULD FIX.
- **Issue:** `SHORT` is a general verdict despite cash-equity short sale and overnight constraints; the validator checks geometry and R:R but cannot establish borrowability, permitted holding period, fill feasibility, gap risk, liquidity, costs, or position size.
- **Why it matters:** A valid geometric target/stop may be unavailable or misleading for a cash equity position. A stop is not a guaranteed exit price; a multi-price entry zone makes simple R:R ambiguous. A minimum 2R is not equivalent to a maximum loss budget.
- **Recommended action:** In V1 either restrict trade-plan SHORT to clearly defined intraday hypothetical scenarios or return a directional bearish scenario without implying an executable short. Define long/short instrument and horizon capabilities as explicit policy. Label R:R as theoretical per-unit price geometry before fees/slippage, calculate it deterministically with documented zone conventions, and make position sizing out of scope unless the user supplies portfolio capital, loss budget, quantity/lot policy, and assumptions. Return warnings or WAIT where gaps/liquidity/data prevent meaningful geometry.
- **Consequence if not adopted:** A syntactically valid report can present an unavailable or materially understated-risk plan as actionable.
- **Confidence:** High.
- **Sources:** EDD itself flags differing Indian short-sale rules; the product-specific treatment should be confirmed against current applicable regulations and broker constraints before any functionality relies on it.

### 3.5 Decide synchronous lifecycle and idempotency before API shape is finalized

- **EDD:** §§5.3, 11.1, 12.
- **Severity:** SHOULD FIX.
- **Issue:** API text offers both POST “start” and GET status/result while suggesting synchronous request/response. It does not define duplicate submissions, client disconnect behavior, deadlines, partial timeframe failure, persistence timing, or cancellation.
- **Why it matters:** Browser retries or timeouts may create duplicate provider/LLM calls and duplicate paid model usage. Persisting a report after the client disconnects can be useful, but the response contract must explain that. Holding a database transaction open while calling external APIs is also undesirable.
- **Recommended action:** For local/single-user V1 choose synchronous end-to-end unless observed latency requires otherwise; persist an analysis run with state transitions, never hold a DB transaction across provider/model calls, attach an idempotency key to the request, use explicit overall and per-provider/model deadlines, and define whether partial data produces a failed run or a degraded report. Add a job/status API only when real measurements require it.
- **Consequence if not adopted:** Duplicate costs, ambiguous reports, abandoned in-progress rows, or a premature worker/queue design.
- **Confidence:** High.

## 4. Deferred improvements

### 4.1 Second provider, live fallback, cache, queue, streaming, and scheduled analysis

- **EDD:** §§2.3, 5.3, 7.6, 12, 16, 18.
- **Severity:** DEFER.
- **Issue:** These add failure modes, consistency problems, and rights questions; V1 explicitly excludes scheduling and distributed infrastructure.
- **Recommended action:** Keep one provider and no cache/queue until measurements or continuity requirements demonstrate need. If adding a second source later, do not silently splice its candles into the first provider's series; record source boundaries and validate equivalence first.
- **Consequence if not adopted:** Unnecessary operational complexity and hidden source discontinuities.
- **Confidence:** High.

### 4.2 Persistent chat history and multi-agent/model routing

- **EDD:** §§2.3, 3.3, 9.5, 11.1, 13.
- **Severity:** DEFER.
- **Issue:** Chat is an additional product surface with privacy, context, and support needs; model routing and multiple agents have no demonstrated V1 quality benefit.
- **Recommended action:** Start with report-scoped follow-up questions, bounded to one saved report and its structured evidence. If session continuity is not a launch requirement, do not persist arbitrary chat history. Add multi-agent or routing only after comparative evaluation improves measured grounding or quality enough to justify cost and complexity.
- **Consequence if not adopted:** More state and personal data retention without a clear product requirement.
- **Confidence:** High.

### 4.3 Backtesting and calibrated outcome probabilities

- **EDD:** §§2.3, 4.5, 8.4, 9.6, 15.4.
- **Severity:** DEFER for V1; mandatory before probability claims.
- **Issue:** Correctly excluded from V1, but later calibration cannot be done from polished LLM narratives or random train/test splits.
- **Recommended action:** Preserve the exclusion. If later pursued, preregister outcome labels/horizon and use point-in-time instrument universes, chronological splits, adjustment-aware inputs, transaction costs/slippage, survivorship/leakage controls, and a separate evaluation report. Only then consider probability calibration.
- **Consequence if not adopted:** In-sample results or selected examples may be misrepresented as out-of-sample predictive reliability.
- **Confidence:** High.

## 5. Disagreements and alternatives

### 5.1 “Provider-independent” should mean domain contracts, not an abstraction that erases provider behavior

- **EDD:** §§2.1, 6, 7.1–7.3.
- **Severity:** SHOULD FIX.
- **Issue:** A lowest-common-denominator `get_candles` can hide provider-specific limits, candle boundaries, entitlements, timestamp quality, volume semantics, adjustments, and history depth.
- **Recommended action:** Keep a narrow adapter interface, but make `ProviderCapabilities` and provenance first-class, and fail explicitly when requested interval/range/feature cannot be met. Do not promise every provider implements every capability. Provider adapters must expose unsupported/limited capability distinctly and canonicalization must preserve known source semantics.
- **Consequence if not adopted:** Provider switching can silently alter report evidence while API/domain types appear unchanged.
- **Confidence:** High.

### 5.2 Current candidate-provider fit is uneven; choose against a concrete V1 request matrix

- **EDD:** §§2.2, 4.2, 7.1–7.2, 12.1, Open Question 15.
- **Severity:** SHOULD FIX.
- **Issue and verified facts:** Upstox's official V3 documentation currently lists minute intervals 1–300, hour intervals 1–5, and daily/weekly/monthly data, with intraday history from January 2022 and daily/weekly/monthly from January 2000; it also gives retrieval-window limits. Its API rate-limits page lists standard APIs including historical candles at 50 requests/sec, 500/min, 2000/30 min. Upstox documents a free, one-year, read-only Analytics Token that includes historical data access. [Historical Candle V3](https://upstox.com/developer/api-documentation/v3/get-historical-candle-data/), [rate limits](https://upstox.com/developer/api-documentation/rate-limiting/), [Analytics Token](https://upstox.com/developer/api-documentation/analytics-token/).

  Angel One SmartAPI's official historical docs list 1m, 3m, 5m, 10m, 15m, 30m, 1h, and 1d intervals and per-request maximum days, but no 4h or weekly interval in that table. The official rate-limit page lists a client-code candle endpoint limit; the page currently appears to contain inconsistent duplicate figures for the same endpoint in its rendered table, so the precise limit should be confirmed with Angel One before use. [SmartAPI Historical and Rate Limit documentation](https://smartapi.angelone.in/docs).
- **Recommended action:** Use a request matrix for the actual desired V1 intervals/lookbacks/instruments, then verify current API version, account eligibility/auth flow, data availability, missing/zero volume, corporate-action treatment, rate limits, quality, and contractual retention/display. Upstox appears to match the illustrative 4h and weekly interval needs at API-shape level; this is not a provider recommendation or a claim about data quality or use rights. TejHQ suitability/capabilities remain unverified from official material in this review.
- **Consequen…66 tokens truncated…wn on provider comparative quality/contractual rights.

### 5.3 Do not use `Decimal` for every numerical kernel by default

- **EDD:** §7.3.
- **Severity:** OPTIONAL.
- **Issue:** Decimal is attractive for serialized price precision but many indicator libraries and vectorized calculations operate in IEEE floating point. Using Decimal end-to-end may add conversion cost and incompatibility; float alone can obscure exchange tick precision.
- **Recommended action:** Preserve raw provider decimal text or scaled integer/tick representation for price identity and serialization, then convert to a documented numerical type for calculations with explicit tolerances. Round only at display/order-like level conventions; V1 does not execute orders. Store instrument tick size and price scale. Volume should be integer/count where provider semantics support it, not generic Decimal by default.
- **Consequence if not adopted:** Either inaccurate-looking serialization or avoidable calculation complexity; this is not a blocker if a consistent representation is selected.
- **Confidence:** Medium-high; engineering judgment.

### 5.4 PostgreSQL and the modular monolith are appropriate; separate modules can be fewer

- **EDD:** §§2.1–2.2, 6, 11, 16–17.
- **Severity:** OPTIONAL.
- **Issue:** The proposed architecture is directionally sound, but separate “orchestration,” “AI reasoning,” “risk,” “quantitative,” “market-data domain,” and application module folders can become ceremonial boundaries for a small codebase.
- **Recommended action:** Keep deployment as one process and start with four cohesive areas: API, application workflow, domain calculations/validation, adapters+persistence. Split internal packages when change ownership or complexity warrants it. PostgreSQL is a reasonable default for reports/configuration/provenance; no time-series database is justified without retained candle volume/query workload.
- **Consequence if not adopted:** More navigation and indirection, but no major correctness issue.
- **Confidence:** High.

## 6. Missing requirements and open questions

### 6.1 Define the market session source, versioning, and refresh behavior

- **EDD:** §§7.4–7.5, 20 questions 4–6.
- **Severity:** MUST FIX before intraday calculation.
- **Issue:** “Maintained calendar/source” is not a source of truth or update contract. NSE publishes segment-specific timings and holiday calendars; the current equities page lists regular trading 09:15–15:30 and includes a special Muhurat session that falls on Sunday in 2026. A weekday/time predicate is therefore inadequate. [NSE Market Timings & Holidays](https://www.nseindia.com/resources/exchange-communication-holidays?apiversion=v2).
- **Recommended action:** Select the official exchange source for each supported venue, store calendar snapshots/version/effective date, and define fallback behavior when the source is unavailable or a special session is announced late. Treat NSE and BSE calendars independently. Clearly state whether pre-open, auction, block-deal, special pre-open, and Muhurat events enter candle calculations.
- **Consequence if not adopted:** Session bars can be misbucketed or false gaps/partials raised on valid special sessions.
- **Confidence:** High.

### 6.2 Specify “stale” and data sufficiency as policies, not warnings alone

- **EDD:** §§3.2, 4.2, 5.1, 7.4, 10, 19 criterion 4.
- **Severity:** SHOULD FIX.
- **Issue:** Staleness appears repeatedly, but there is no freshness threshold by timeframe, market-open/closed state, provider delay, or user-visible result. Nor is there a minimum bar count / warm-up sufficiency contract.
- **Recommended action:** Define freshness relative to expected latest completed candle, exchange session, provider retrieval time, and timeframe. Define hard-fail vs degraded outcomes and minimum history per indicator. The model must receive explicit typed data-quality status and be prevented from issuing a trade plan where required evidence is missing.
- **Consequence if not adopted:** One vague “stale” flag can be inconsistently applied and the LLM may narrate from inadequate history.
- **Confidence:** High.

### 6.3 Clarify instrument lifecycle and stable identity

- **EDD:** §§4.1, 7.1, 7.3, 11.1.
- **Severity:** SHOULD FIX.
- **Issue:** A symbol is not a stable security/listing identity. NSE and BSE can have distinct listings and provider keys for the same issuer; symbols can change, delist, or be reused.
- **Recommended action:** Model security identity separately from exchange listing and provider instrument identifier. Use ISIN where present as one attribute, not the only key; version symbol/name/key mappings with valid-from/to timestamps and retain the exact mapping used on each report. Do not automatically stitch data across a symbol change until identity and corporate-action continuity are verified.
- **Consequence if not adopted:** Historical reports may point to a newly reused symbol or inadvertently mix separate instruments.
- **Confidence:** High.

### 6.4 Explain verdict semantics and application of constraints

- **EDD:** §§4.4–4.6, 9.3, 10, 12.1.
- **Severity:** SHOULD FIX.
- **Issue:** LONG/SHORT/WAIT/NO_TRADE combines a directional view, a quality decision, data validity, user preference, and ability to formulate levels. “Validator may reject, downgrade or constrain” is too open-ended, and a deterministic validator cannot prove the model's thesis is sound.
- **Recommended action:** Define verdict as a schema with separate fields: directional scenario (bullish/bearish/neutral), plan availability, data eligibility, deterministic rule outcomes, and final presentation status. Specify precedence: invalid data → no plan; contradictory/insufficient evidence → neutral/WAIT; valid evidence but plan geometry fails → no plan; constraints must not be changed silently. Keep natural-language verdict rationale traceable to evidence IDs.
- **Consequence if not adopted:** Similar analyses may produce inconsistent labels and users may interpret validator acceptance as endorsement of expected return.
- **Confidence:** High.

### 6.5 Decide hosted versus local-first security before frontend/settings design

- **EDD:** §§3.1, 6.1, 13.1, 14, 16.
- **Severity:** SHOULD FIX.
- **Issue:** Authentication and deployment are deferred, while the UI includes provider and LLM credentials. Browser-to-localhost, hosted multi-user, and single-user local deployment have materially different threat models and secret ownership.
- **Recommended action:** Declare the V1 trust boundary. For local-only, restrict bind address by default, protect local credentials at rest, avoid exposing settings endpoints to arbitrary origins, and document local access assumptions. For hosted/multi-user, require identity/authorization, tenant scoping on every report/chat/profile query, encrypted secret storage, per-user cost/rate controls, audit/deletion, and CSRF/CORS/session policy before launch.
- **Consequence if not adopted:** A local prototype can accidentally be exposed with no authentication or a multi-user product can leak one user's reports/provider credentials to another.
- **Confidence:** High.

## 7. Financial and market-data correctness risks

### 7.1 Candle alignment, partial bars, aggregation, and session boundaries

- **EDD:** §§4.2, 7.3–7.5, 8.3.
- **Severity:** MUST FIX.
- **Failure scenario:** A provider labels candles by start time while another labels by close time; the pipeline merges them as equivalent. A 4h bar crosses the cash-session close and a final 2h15 segment is treated as a 4h observation. A current candle is mistaken for closed because wall-clock time passed the nominal boundary even though the market calendar says special session or provider is delayed.
- **Mitigation:** Normalize source convention before comparing; retain original timestamp and mapped start/end; use exchange-local calendar/session boundaries and provider completion evidence; model partial bars explicitly and don't feed them to closed-candle indicators by default. Test open, close, holiday, special-session, missing interval, and request-end boundaries.
- **Confidence:** High.

### 7.2 Corporate actions, symbol changes, and adjustment consistency

- **EDD:** §§4.1, 7.3–7.4, 8.1, 11.3.
- **Severity:** MUST FIX for historical price/indicator comparisons.
- **Failure scenario:** A split makes the chart show a discontinuity, ATR and moving averages spike, and model proposes a stop/target in pre-split units; alternatively adjusted history is combined with unadjusted recent candles.
- **Mitigation:** Choose adjusted or unadjusted series per report; capture adjustment mode and as-of version; identify corporate actions and provider adjustment semantics; never combine modes. If no trustworthy adjustment source exists, flag affected windows and suppress affected indicators/price levels. Preserve raw price scale for user-facing actionable levels only when semantics are known.
- **Confidence:** High.

### 7.3 Indicator lookahead and definition drift

- **EDD:** §§4.3, 8.1–8.4, 15.1, 15.3.
- **Severity:** MUST FIX.
- **Failure scenario:** A pivot/swing detector labels a high only after later candles confirm it but attaches the label to the earlier high, giving the current report knowledge it did not have; a library update changes EMA seeding or RSI edge handling without an implementation version change.
- **Mitigation:** Specify point-in-time availability of every pattern, warm-up and NaN behavior, formula/reference, version and output timestamp; fixtures should include warm-up, missing observations, flat series, gaps and equal highs/lows. Pattern outputs should include `observed_at`/confirmation timestamp distinct from event timestamp. Pin numerical dependencies and review upgrades against golden fixtures.
- **Consequence:** False historical confidence and live reports that cannot be compared consistently.
- **Confidence:** High.

### 7.4 Evidence leakage through prompt and report context

- **EDD:** §§3.3, 9.1–9.6, 13.2, 14.
- **Severity:** SHOULD FIX.
- **Failure scenario:** A chat answer about an old report accidentally mixes current market facts with stale report evidence, or the LLM introduces a price level not contained in evidence and the validator only checks its geometry.
- **Mitigation:** Bind every answer to an immutable report ID and analysis timestamp; distinguish report evidence from current data; if “new analysis” occurs, create a new run and link it explicitly. Let the model cite allowed evidence IDs and validate references, instrument, units and price source. Deterministic validation can reject invalid levels but cannot prove a plausible-looking level is supported; prefer model-proposed levels only when tied to allowed source values/rules, otherwise return scenarios without levels.
- **Consequence:** Plausible but unsupported or stale trade language can be presented as current evidence.
- **Confidence:** High.

### 7.5 Confidence, score, and R:R are not outcome guarantees

- **EDD:** §§4.4–4.5, 9.4, 10, 12.1.
- **Severity:** MUST FIX for score gating; SHOULD FIX for labels.
- **Failure scenario:** Users tune a 90% threshold or accept a 2:1 theoretical R:R as if it meant high win probability or favorable realized return.
- **Mitigation:** Do not expose calibrated probability until validated. Remove numeric setup threshold in V1 or label a transparent non-predictive diagnostic with no implication of outcome likelihood. Label R:R as hypothetical, price-only, and before transaction costs/slippage; state that stop execution can gap through levels. Keep qualitative model language separate from computed values.
- **Consequence:** A heuristic or geometric ratio is mistaken for statistically supported expected performance.
- **Confidence:** High.

## 8. Security and operational risks

### 8.1 Data/model outputs remain untrusted and need provenance validation

- **EDD:** §§5.4, 9.1, 9.3, 14.
- **Severity:** SHOULD FIX.
- **Issue:** The prompt injection control is directionally right but not operationalized. Numeric market payloads can be malformed; provider textual instrument metadata and model output can contain hostile or irrelevant content. Structured output does not ensure truth.
- **Recommended action:** Bound and normalize provider fields; never interpolate provider text as instructions; use strict schema validation, allow-listed evidence references, output size/time limits, and deterministic checks. Keep prompt/template versions. Do not add news/text retrieval to V1 unless a separate source/provenance and injection policy is designed.
- **Consequence if not adopted:** Untrusted text can manipulate interpretation or malformed values can leak into calculations.
- **Confidence:** High.

### 8.2 Secrets, tenant isolation, and model-data retention

- **EDD:** §§5.4, 9.2, 11.2, 14.
- **Severity:** SHOULD FIX before hosted use.
- **Issue:** “Backend only” prevents browser exposure but does not cover encryption, rotation, least privilege, user/tenant ownership, outbound model retention, deletion, or logs containing prompts/reports.
- **Recommended action:** Define provider/model data handling and secret lifecycle by deployment mode. Treat reports and prompts as potentially sensitive financial-interest data; redact structured logs, restrict access, define retention/deletion, and ensure saved report queries are tenant-scoped if multi-user. Confirm each LLM provider's current retention/training terms before sending user-specific context.
- **Consequence if not adopted:** Credential compromise, unintended disclosure, or data retention beyond the user's expectation.
- **Confidence:** High.
- **Sources:** Provider-specific LLM retention terms are not specified in the EDD and were not verified here.

### 8.3 Retries and provider limits

- **EDD:** §§5.3, 7.1–7.2, 12.
- **Severity:** SHOULD FIX.
- **Issue:** “Bounded retries/backoff” is too broad: authentication, invalid requests, no data, throttling, and outages need different treatment. Provider limits may be per user/account and can change.
- **Recommended action:** Define typed errors and retry only transient idempotent reads; respect `Retry-After` where supplied; use a shared per-credential limiter even in a single process; do not retry auth/validation failures; expose a degraded/failed status. Revalidate configured quotas at provider selection and after major API changes.
- **Consequence if not adopted:** Retry storms, credential throttling, misleading empty results, and duplicated spend on model calls.
- **Confidence:** High.
- **Sources:** Current Upstox and SmartAPI limits are cited in §5.2; they are mutable provider facts, not durable architecture constants.

## 9. Simplification opportunities

### 9.1 V1 should not need an orchestration product, multiple agents, or persisted arbitrary chat

- **EDD:** §§6, 9, 11, 13, 17.
- **Severity:** SHOULD FIX.
- **Opportunity:** One application service, one LLM invocation, structured evidence, one validator, and one report are sufficient to test product value.
- **Recommended action:** Remove LangGraph/ADK from initial dependencies/architecture decisions; keep a plain workflow seam. Start chat as a report-question endpoint without free-running tools or session memory; only add new analysis when explicitly requested and create a new report run.
- **Benefit/consequence:** Fewer moving parts, smaller prompt/context exposure, easier deterministic testing. The trade-off is that a future resumable agent workflow would need a deliberate later integration.
- **Confidence:** High.

### 9.2 Reduce configuration before adding catalog breadth

- **EDD:** §§4.3–4.5, 12.1, 13.
- **Severity:** SHOULD FIX.
- **Opportunity:** User-selected models, dozens of indicators, arbitrary custom instructions, score thresholds, and multiple depth modes multiply untested combinations.
- **Recommended action:** Launch with one validated analysis profile and minimal safe preferences. Keep advanced parameters server-side until each is defined and evaluated. Custom instructions should affect explanation style only, never calculations or risk constraints.
- **Benefit/consequence:** Better repeatability and less UI/backend validation surface; less user flexibility initially.
- **Confidence:** High.

## 10. Proposed revised architecture (only if warranted)

The deployment shape need not change. Replace the provisional graph with a typed application workflow and make data policy/quality explicit:

```text
API request + idempotency key
  -> resolve effective-dated listing
  -> fetch one provider batch (capability + entitlement checked)
  -> normalize to versioned candle contract
  -> validate session, adjustment, completeness, freshness, and sufficiency
  -> calculate a small versioned deterministic evidence set
  -> persist input provenance/evidence snapshot
  -> one LLM interpretation call over evidence IDs
  -> schema + evidence-reference validation
  -> deterministic plan-geometry check (or no plan)
  -> persist immutable report + validation findings
  -> return report/degraded status
```

- **EDD:** §§6–11.
- **Severity:** SHOULD FIX.
- **Failure mode addressed:** Current boundaries are mostly listed as components, but quality gates, data rights, and immutable run provenance are not ordered as a hard gate before the model call.
- **Recommended action:** Implement the above as a plain service with no transaction held across network calls. A market-data quality failure should stop before the LLM; a valid analysis with no supported plan should still produce a WAIT/NO_TRADE report.
- **Consequence if not adopted:** The LLM can turn invalid/insufficient evidence into a polished report and persisted output before the system's eligibility policy is clear.
- **Confidence:** High.

## 11. Suggested schema/API changes

### 11.1 Separate security, listing, instrument mapping, and candle batch provenance

- **EDD:** §§4.1, 7.3, 11.1.
- **Severity:** SHOULD FIX.
- **Suggested shape:**

```text
Security(id, isin?, legal_name)
Listing(id, security_id, exchange, symbol, valid_from, valid_to, tick_size, currency)
ProviderInstrument(listing_id, provider, provider_key, valid_from, valid_to)
DataBatch(id, provider, api_version, entitlement_ref, request_start/end,
          interval, retrieved_at, calendar_version, adjustment_mode,
          count, first/last_candle_at, quality_summary, input_hash)
Candle(batch_id, listing_id, start_utc, end_utc, open, high, low, close,
       volume?, volume_status, is_complete, source_timestamp)
```

- **Why:** Stable identity and source semantics need different lifecycles. Batch-level provenance avoids repeating provider metadata on each candle and makes a hash meaningful.
- **Consequence if not adopted:** Symbol mapping and source updates are hard to audit; risks in §§6.2–6.3 remain.
- **Confidence:** High; exact physical schema remains implementation choice.

### 11.2 Version immutable analysis inputs and report lifecycle

- **EDD:** §§11.1–11.3, 12.
- **Severity:** SHOULD FIX.
- **Suggested additions:** `run_id`, `idempotency_key`, `status`, `failure/degraded_reason`, `request_schema_version`, `evidence_schema_version`, `indicator_engine_version`, `calendar_version`, `adjustment_policy_version`, `validator_version`, `prompt_version`, `model_id`, `provider_api_version`, and explicit `final_verdict` distinct from `directional_bias` and `plan_status`.
- **Why:** Report text is not a complete audit record; model result and data validity are different dimensions.
- **Consequence if not adopted:** A past response may be impossible to interpret after code/config changes, and repeated POSTs may create duplicate runs.
- **Confidence:** High.

### 11.3 Simplify and clarify initial API behavior

- **EDD:** §12.
- **Severity:** SHOULD FIX.
- **Recommended action:** Specify whether `POST /analyses` returns a completed report synchronously (`200/201`) or a persisted run reference (`202`); do not describe both. Include a client idempotency key. Define per-timeframe result status and no-data/degraded behavior. Do not allow arbitrary provider selection from the request unless the user's entitlement/configuration supports it. Keep profile writes and chat history out of the initial API if not required.
- **Consequence if not adopted:** Client semantics and duplicate-request behavior remain ambiguous.
- **Confidence:** High.

## 12. Prioritized action list

Effort is relative: **S** small, **M** moderate, **L** substantial. Impact describes the consequence addressed, not a forecast metric.

| Priority | EDD | Severity | Action | Effort / impact | Decision needed |
|---|---|---|---|---|---|
| 1 | §§1, 4.6, 10, 14 | MUST FIX | Define launch audience/distribution and obtain India-specific review of verdicts and price levels; adjust product boundary accordingly. | M / Very high | Local-only vs shared/paid; permitted output surface |
| 2 | §§7.1–7.6, 11 | MUST FIX | Verify provider agreement, account entitlement, data use/display/retention/deletion rights. | M / Very high | Provider and exact data rights |
| 3 | §§4.2, 7.3–7.5, 8 | MUST FIX | Freeze canonical candle, session, completeness, adjustment, and identity contracts. | M / Very high | Timestamp boundary; calendar source; adjustment policy |
| 4 | §§4.5, 8.2, 9.4, 18 | MUST FIX | Remove unvalidated setup score/threshold from V1 acceptance/API. | S / High | Whether score is deferred entirely |
| 5 | §§2, 6, 9 | SHOULD FIX | Use plain typed workflow; revisit LangGraph/ADK only for a measured runtime need. | S / Medium | None for initial implementation |
| 6 | §§4.2–4.3, 7–8 | SHOULD FIX | Select a narrow, provider-supported V1 interval/indicator set and test actual sample data. | M / High | Vertical-slice scope |
| 7 | §§10, 12 | SHOULD FIX | Define short-side semantics, plan/no-plan rules, and theoretical R:R limitations. | M / High | Whether short plans are in V1 |
| 8 | §§11–12 | SHOULD FIX | Choose auditability vs exact replay; add immutable run/version/idempotency metadata. | M / High | Retention target subject to rights |
| 9 | §§3, 12 | SHOULD FIX | Decide synchronous lifecycle and duplicate/cancellation/partial-failure semantics. | S / Medium | Sync response acceptable for V1? |
| 10 | §§13–14 | SHOULD FIX | Declare local-first vs hosted trust model and corresponding secret/auth/data controls. | M / High | Deployment model |
| 11 | §§4.1, 7.3, 11 | SHOULD FIX | Model security/listing/provider-key identity with effective dating. | M / High | ISIN and source mapping policy |
| 12 | §§9, 11, 13 | DEFER | Keep chat scoped to reports; defer persistent memory, multiple agents, model routing. | S / Medium | Defer feature set |

## Five decisions required before implementation

1. **What is the V1 distribution/commercial model, and what output language is allowed after India-specific regulatory review?**
2. **Which market-data provider/account will be used, and what exact personal/commercial display, retention, and deletion rights apply?**
3. **What is the canonical candle contract:** timestamp/boundary, session and special-session treatment, incomplete bar policy, corporate-action adjustment, and stable instrument/listing identity?
4. **Is V1 auditability-only or exact computational replay, and what may be retained under the provider agreement?**
5. **Will V1 omit setup-quality scoring and use a plain synchronous workflow with one LLM call, and which small interval/indicator slice is in scope?**

## Verdict

The design is **not ready to proceed unchanged**. Resolve decisions 1–4 and remove or substantiate score gating before implementation begins. After those decisions are documented, the remaining architecture is a reasonable modular-monolith V1; provider integration should proceed only against verified entitlements and a tested data contract.

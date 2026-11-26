# LLM-assisted buy signal design

Proposed design for the private Indian cash-equity research app. See the [architecture baseline](EDD-v0.3.md), [implementation plan](IMPLEMENTATION_PLAN.md), and [evidence-source research](LLM-EVIDENCE-RESEARCH.md).

## Product contract

The user requests a signal for one NSE or BSE listing and one horizon. The dashboard shows **Buy setup** or **No buy for now**. A buy setup includes a conditional entry, one profit-target exit, a stop-loss trigger, an expiry, and the reason for the signal. It can expire without triggering. The exit target and stop describe the proposed setup and carry no execution or fill guarantee.

Keep the first strategy long-only and validate the intraday version first. Use 15-minute setup candles and hourly trend context. The first swing candidate would use daily setup candles and hourly context with a separately calibrated policy and a maximum of ten trading sessions, approximately two weeks. The app remains a research workflow with no broker order calls. The signal states apply to new entries. A no-buy outcome gives no instruction about an existing position.

## Alternatives and recommendation

| Approach | How it works | Benefits and trade-offs | Decision |
| --- | --- | --- | --- |
| Rules with LLM explanation | Python selects the setup and all levels. The LLM explains the supporting and conflicting evidence. | Repeatable signal, clear audit trail, and simple baseline. Qualitative interpretation cannot change the decision. | Build first and keep as the comparison baseline. |
| **Rules plus bounded model decision** | Python proposes a validated candidate. The LLM reads the evidence and chooses `BUY_CANDIDATE` or `ABSTAIN`. Python validates the response and owns the outcome and prices. | The model can withhold a technically valid setup when the evidence conflicts. The same snapshot can produce different recommendations, so measure stability, missed opportunities, latency, and cost. | **Recommended target.** Test in shadow mode against rules-only. Enable model-assisted buy signals after the pilot criteria are met. |
| Model proposes verdict and prices | The LLM returns buy or no-buy and invents price levels from the input. Python checks schema and arithmetic. | Fast to prototype. Plausible numbers can pass arithmetic checks while lacking a reproducible rationale. Prompt or model changes can shift the strategy and its risk. | Omit from the initial design. |
| Second LLM as reviewer | A separate model reviews evidence references and the first model’s interpretation. | May catch claims that exceed the evidence. Errors can be correlated, coverage remains unchanged, and calls add cost and latency. | Evaluate as an offline reviewer. Add a runtime reviewer only if it materially improves measured claim accuracy. |

Start with one candidate per request. That makes the experiment about the model’s judgment and avoids hiding a second strategy in candidate selection. Add multiple candidate IDs only after the baseline can identify and justify more than one setup.

## Architecture

~~~mermaid
flowchart LR
    UI["Dashboard: Generate signal"] --> API["POST /api/v1/analyses"]
    API --> ORCH["Analysis service"]
    ORCH --> KITE["Kite adapters and completed bars"]
    ORCH --> CTX["Market context and independent event providers"]
    KITE --> TECH["Deterministic indicators and data checks"]
    TECH --> SNAP["Versioned evidence snapshot"]
    CTX --> SNAP
    SNAP --> RULES["Python evaluation: gates, candidate and levels"]
    RULES --> MODEL["Optional LLM decision and explanation"]
    RULES --> FINAL["Python finalizer"]
    MODEL --> FINAL
    FINAL --> UI
~~~

Keep modules inside the existing FastAPI application. The analysis service calls Python modules directly. It reuses provider and indicator logic from technical evidence, market context and company news and assembles a single snapshot. The dashboard sends the instrument and horizon. The backend determines timestamps, evidence and price levels.

- **Analysis service:** Freeze the cutoff, identify the listing and session, attach approved evidence with typed values, units, source IDs and publication/observation timestamps. Record missing, stale, partial and permission-restricted coverage. Capture the most recent reference price separately from the completed bars.
- **Evaluation module:** Calculate candidates, apply mandatory gates, and return ordered reasons, candidate prices, time conditions and thresholds with policy versions. It is callable without an LLM.
- **LLM module:** Expose a provider-neutral `SignalModel.assess(input) -> ModelAssessment`. Use one configured structured-output adapter and a fixture adapter for tests. It receives one bounded projection and returns a decision, evidence references and a short explanation. External news text is data. The first model has no tools.
- **Finalizer:** Validate references, evidence types, decision, and candidate state. Translate the outcome to public `BUY` or `NO_BUY` and copy numeric values from the rules result.
- **Ownership and permissions:** Before sending data to an external model, approve the destination and permitted fields by source, including market-derived metrics and news excerpts. Check source entitlements and model retention settings. Keep credentials and account data outside the projection. [Zerodha terms](https://zerodha.com/terms-and-conditions) · [NSE data policy](https://betanseapi.nseindia.com/static/market-data/nse-data-policy) · [OpenAI data controls](https://developers.openai.com/api/docs/guides/your-data)

### Input coverage

| Evidence | Signal behavior |
| --- | --- |
| Stock candles and indicators | Mandatory. Completed, correctly ordered, aligned and warm enough for both intervals. Use a verified exchange calendar and reject stale or incomplete required windows. |
| Benchmark and sector | Benchmark freshness and aligned returns are mandatory for the initial strategy. A missing sector mapping is reported as a coverage gap. Apply a sector veto only when the required sector data exists under the active policy. |
| Reference price and liquidity | Mandatory for a buy. Require a timestamp appropriate to the session, positive prices and a liquidity check. Historical candles alone cannot verify that an entry is still reachable. |
| Official company events | A clearance gate when the selected policy requires event coverage. A configured, fresh source must cover the relevant trading window before the gate can pass. Confirmed restricted events block the setup. |
| Company news and fundamentals | Optional context. Include deduplicated headlines already published and observed by the relevant cutoff and only fields approved for model use. A partial news feed makes no assertion about the absence of events. Fundamentals matter when materially tied to the setup or event, especially for swing. |

The dashboard currently has Kite indicators, benchmark context and bounded company news. Official event feeds and production-grade session/freshness checks still need work. If the policy requires those checks, missing coverage yields `NO_BUY` with a reason. Shadow candidates can still be recorded for evaluation.

## Candidate, levels, and final signal

Start with one proposed **long breakout** strategy. A completed setup bar confirms a break of a prior range calculated without that bar. A higher-timeframe trend check and minimum liquidity gate determine eligibility. A later move can trigger entry only within the precomputed price band. Thresholds, bar counts, liquidity, cost estimates and maximum chasing distance belong to a versioned policy and are calibrated before enabling signals.

1. **Entry:** Use the confirmed setup-bar high as a reference for the later trigger, with tick-aware rounding. Define a maximum acceptable entry above the trigger and a validity window. If the current price is already outside the allowed band, return no buy with an expired or missed-entry reason.
2. **Stop-loss:** Derive the trigger from a documented invalidation level such as the setup swing low, with a configured volatility buffer. Reject a stop distance that falls outside allowed ATR-relative or policy bounds. A gap can pass through the trigger.
3. **Profit exit:** Use a reproducible target such as a policy-defined multiple of the initial risk. Reject the setup if a verified resistance level caps usable reward or if reward after estimated fees, spread and slippage falls below the strategy’s threshold. Calculate the check from the least favorable allowed entry. Keep these calculations in `Decimal`; validate tick size and ordering after rounding.
4. **Expiry:** End intraday setups by the configured session cutoff. Swing setups use trading sessions and have a separate risk policy. For open simulated positions, define a time exit as well as profit and stop exits. A new report recomputes from current evidence.

~~~mermaid
flowchart TD
    INPUT["Point-in-time evidence"] --> GATES{"All mandatory gates pass?"}
    GATES -->|No or unknown| NOBUY["NO_BUY with reason codes"]
    GATES -->|Yes| PLAN{"Candidate and rounded levels valid?"}
    PLAN -->|No| NOBUY
    PLAN -->|Yes| RIGHTS{"Model input permitted?"}
    RIGHTS -->|No| NOBUY
    RIGHTS -->|Yes| LLM["Model chooses BUY_CANDIDATE or ABSTAIN"]
    LLM --> CHECK{"Valid output and supported evidence?"}
    CHECK -->|No or unavailable| NOBUY
    CHECK -->|Yes| DECIDE{"Approved candidate and still valid?"}
    DECIDE -->|No or abstain| NOBUY
    DECIDE -->|Yes| BUY["BUY with Python-owned levels and expiry"]
~~~

This diagram describes model-assisted mode. In shadow mode the request records both decisions for comparison. Public responses for shadow runs use a research-only status and no live buy setup. In model-assisted mode, refusal, timeout, invalid references, expired evidence, and prohibited data use produce no buy. Report these as distinct reasons so users can distinguish an unfavorable setup from an unavailable analysis.

## API and validation

Proposed entry point is `POST /api/v1/analyses` with exchange, symbol and horizon. Select intervals and policy server-side. Return a report ID, as-of and expiry times, evidence coverage, gate outcomes and versions, and either a populated setup or `setup: null`. For an accepted buy, the setup includes currency, entry trigger and ceiling, target, stop trigger, and risk/reward under stated cost assumptions. Link displayed evidence IDs to the underlying source and timestamp. Invalid requests get HTTP 4xx. A valid analysis that concludes no buy returns the typed outcome even when the evaluation cannot clear a gate. Transport failures return an explicit service error when no report can be constructed.

The model response schema includes only the decision, supplied candidate ID when applicable, a bounded list of reason codes and evidence IDs, and a short explanation. Use a strict schema and handle refusal and incomplete results explicitly. Verify every referenced ID and allowed reason/evidence combination in Python. Render prices and links from server data. Where possible, use typed claims for facts and render their numbers from evidence. Review free-text semantic support in the evaluation suite since valid references alone do not guarantee the explanation follows. [Structured Outputs](https://developers.openai.com/api/docs/guides/structured-outputs)

Set one model deadline, input and output token limits, and a concurrency cap. Use one inference per eligible request and deduplicate equivalent in-flight requests by evidence hash, owner and policy/model versions. Avoid automatically retrying paid inference after ambiguous timeouts. Store the decision, reason codes, source snapshot or allowed references, model and prompt versions, and outcome-validation status. Keep raw prompt text out of application logs.

## Evaluation and rollout

| Stage | What to verify |
| --- | --- |
| Contract and failure tests | Missing, stale, or lookahead inputs fail required gates. Invalid or invented IDs, contradictory reason codes, altered levels, expired entries, refusals, timeouts, and instructions embedded in headlines never produce an invalid buy. |
| Historical replay | Compare rules-only and model-assisted outcomes on identical snapshots. Freeze policy before the held-out window. Use point-in-time events and listings, corporate-action-aware candles, cost and gap models, and fills at a later eligible bar. When stop and target both fall inside an OHLC bar and sequence is unknown, use finer data or score conservatively. |
| Shadow run | Compare accepted signal rate, repeated-run disagreement, unsupported claims, after-cost expectancy, drawdown, latency and cost. Report sample size and results by horizon, event status and liquidity. Avoid checking performance by selecting thresholds on the same evaluated window. |
| Release | Require zero mandatory-gate bypasses, fabricated evidence references and off-policy levels in accepted test output. Agree on out-of-sample performance and operational thresholds before publishing buy setups. Roll out intraday first. Keep swing in shadow until its separate policy qualifies. |

Replay measures strategy behavior, while claim checks measure the quality of explanation. A well-grounded explanation can still describe a losing setup. Historical fitting and selection can also overstate an apparent edge. [Bailey et al., The Probability of Backtest Overfitting](https://escholarship.org/uc/item/4w1110bb)

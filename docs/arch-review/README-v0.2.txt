Trading Assistant EDD v0.2

Primary document: EDD-v0.2.md

This revision incorporates the owner's five decisions:
1. Hosted deployment.
2. Low-cost market-data provider target; no provider selected before a verification spike.
3. Both bullish/LONG and bearish/SHORT analysis, with actionable SHORT constrained by a versioned segment x horizon policy.
4. Synchronous request/response API for V1.
5. Per-analysis normalized candle snapshots for charts/replay, subject to explicit provider storage/display/retention/deletion rights.

It also incorporates the convergent Claude and Codex review recommendations:
- Plain typed Python pipeline; no LangGraph or Google ADK in V1.
- Hosted authentication, authorization, secret management, privacy, observability and cost controls.
- Separate directional bias, actionability and final verdict.
- Remove unvalidated scalar setup-quality score and numeric confidence thresholds; use named deterministic gates.
- Canonical candle boundaries, session/calendar, completeness, volume and corporate-action adjustment semantics.
- Separate security/listing/provider instrument identities.
- Persist exact evidence/provenance and permitted candle snapshots; hashes alone are insufficient for replay.
- LLM selects among evidence-backed candidate price levels; deterministic validation remains authoritative.

Important unresolved gates before implementation:
- Choose and verify a low-cost provider, including current API capabilities, price, account eligibility and contractual data rights.
- Confirm exact cloud vendor/region and private single-owner access model.
- Define the direction x segment x horizon eligibility matrix, especially cash-equity intraday SHORT.
- Finalize snapshot TTL, object storage, backups and deletion based on provider terms.
- Obtain qualified India-specific legal/regulatory advice before any wider distribution or marketing.

The EDD does not assert that any provider permits candle retention. If a candidate provider prohibits the selected snapshot use, it does not satisfy the chosen product requirement unless an approved alternative retention arrangement exists.

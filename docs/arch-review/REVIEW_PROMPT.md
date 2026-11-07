# Independent Architecture Review Assignment

You are reviewing a draft Engineering Design Document for an AI-assisted Indian equity market analysis platform.

## Your role

Act as a skeptical senior/principal engineer. Evaluate the design on its merits. Do not assume that the current proposal is correct simply because it is detailed.

## Instructions

1. Read `EDD.md` completely.
2. Review the architecture independently. Do not inspect another agent's review or coordinate with another reviewer.
3. Do not modify `EDD.md`.
4. Do not write application code, scaffold a project, install packages or start implementation.
5. Create exactly one review report in `reviews/`:
   - Codex: `reviews/codex-review.md`
   - Claude: `reviews/claude-review.md`
6. Follow the required report structure and classification rules in EDD section 21.
7. Challenge the design where justified, but do not add complexity merely because it is technically possible.
8. Preserve the explicitly agreed V1 boundaries: Indian equities first, on-demand analysis, no order execution, no scheduled jobs, no permanent raw-candle warehouse, modular monolith, deterministic quantitative calculations, LLM interpretation, provider abstraction and report provenance.
9. Specifically evaluate LangGraph versus Google ADK versus a plain Python workflow. Explain whether an agent framework is needed at all for V1.
10. Evaluate the market-data design carefully. Verify current provider capabilities, access requirements, rate limits, pricing/free-tier claims and data-use/retention terms from official sources before making factual claims. If you cannot verify something, label it unverified.
11. Treat financial correctness as a first-class engineering concern: candle boundaries, session calendars, incomplete candles, corporate actions, lookahead, data leakage, indicator definitions, risk geometry and confidence calibration.
12. Distinguish critical blockers from improvements that can safely be deferred.
13. Do not treat LLM-generated confidence as a probability. Challenge any scoring design that lacks a defensible methodology.
14. Give concrete recommendations with consequences and trade-offs, not generic advice.

## Required report

Use these headings:
1. Executive assessment
2. Critical blockers
3. High-priority improvements
4. Deferred improvements
5. Disagreements and alternatives
6. Missing requirements and open questions
7. Financial and market-data correctness risks
8. Security and operational risks
9. Simplification opportunities
10. Proposed revised architecture (only if warranted)
11. Suggested schema/API changes
12. Prioritized action list

For every finding include:
- EDD section reference
- Severity: MUST FIX / SHOULD FIX / DEFER / OPTIONAL
- Concrete issue or opportunity
- Why it matters / failure mode
- Recommended action
- Consequence of not adopting it
- Confidence level
- Sources for claims that depend on current external facts

Finish with:
- The five most important decisions the project owner must make before implementation.
- A concise verdict on whether the design is ready to proceed after those decisions.

This is a review-only task. Do not implement anything.

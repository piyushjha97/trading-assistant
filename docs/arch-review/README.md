# Trading Assistant — Architecture Review Package

This package is for **independent architecture review only**. It is not an implementation prompt.

## Files

- `EDD.md` — draft Engineering Design Document and current requirements/decisions.
- `REVIEW_PROMPT.md` — instructions to give to each agent.

## How to use with Codex CLI and Claude Code

1. Extract this package into a local project/docs folder, for example `trading-assistant/docs/architecture-review/`.
2. Give the same `EDD.md` and `REVIEW_PROMPT.md` to both agents.
3. Run the review in separate sessions. Do not share one agent's findings with the other until both reviews are complete.
4. Ask Codex to save its report as `reviews/codex-review.md`.
5. Ask Claude to save its report as `reviews/claude-review.md`.
6. Do not ask either agent to modify the EDD or write application code yet.
7. Bring both reports back for reconciliation and a decision log.

## Suggested command/session prompt

> Read `EDD.md` and `REVIEW_PROMPT.md`. Perform the independent review exactly as instructed. Create only your review report in the `reviews/` directory using the required filename. Do not modify the EDD, create application code, scaffold the repository, or install dependencies.

## Important

The EDD marks decisions as agreed, provisional or deferred. Reviewers must not silently convert open questions into settled decisions. In particular, final market-data provider, exact reproducibility/retention strategy, scoring methodology, hosting, and backtesting versus paper trading remain open.

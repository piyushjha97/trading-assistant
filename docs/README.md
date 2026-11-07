# Trading Assistant Documentation

## Current design baseline

- [Engineering Design Document v0.2](EDD-v0.2.md) is the current architecture and requirements baseline. It records owner-confirmed decisions, provisional choices, unresolved questions, release gates and V1 acceptance criteria.
- [Implementation plan](IMPLEMENTATION_PLAN.md) breaks the EDD roadmap into gated phases, tasks, deliverables and acceptance tests. It is planning only; it does not authorize application implementation.

Do not treat the EDD as authorization to bypass its provider, licensing, security or legal gates. Changes to confirmed design decisions require an explicit owner decision and an updated design record.

## Architecture review materials

The original independent-review package and its source materials are preserved under [arch-review](arch-review/). The v0.1 EDD and review prompt are historical review inputs; use `EDD-v0.2.md` at this directory level as the current design baseline. Review reports are retained in the review package for traceability.

The review package also contains a ZIP archive used to exchange the original review materials. It is a generated distribution artifact and is excluded from Git; the source Markdown files are the review record.

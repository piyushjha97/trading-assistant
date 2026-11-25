# Trading Assistant Documentation

## Current design

- [Engineering Design Document v0.3](EDD-v0.3.md) is the current architecture baseline.
- [Implementation plan](IMPLEMENTATION_PLAN.md) records the work sequence and acceptance checks.
- [LLM-assisted buy signal design](LLM-SIGNAL-DESIGN.md) defines the candidate, model decision, risk checks and rollout.
- [LLM evidence research](LLM-EVIDENCE-RESEARCH.md) compares source options and defines the proposed report input and validation flow.
- [EDD v0.2](EDD-v0.2.md) and [architecture review materials](arch-review/) are retained as historical references.

The EDD describes the agreed Python modular monolith: the Analysis API coordinates market-data, analytics, and evaluation modules; AI research, report explanation, and report-scoped chat use those shared services. The flow diagram is in section 3 of EDD v0.3.

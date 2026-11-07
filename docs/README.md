# Trading Assistant Documentation

## Current design

- [Engineering Design Document v0.3](EDD-v0.3.md) is the current architecture baseline.
- [Implementation plan](IMPLEMENTATION_PLAN.md) records the work sequence and acceptance checks.
- [EDD v0.2](EDD-v0.2.md) and [architecture review materials](arch-review/) are retained as historical references.

The EDD describes the agreed Python modular monolith: the Analysis API coordinates market-data, analytics, and evaluation modules; AI research, report explanation, and report-scoped chat use those shared services. The flow diagram is in section 3 of EDD v0.3.

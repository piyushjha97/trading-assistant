# Intraday signal evaluation and paper trades

The dashboard's **Evaluate & track** button evaluates the selected listing with the 15-minute strategy. `BUY` opens a simulated long when the entry triggers. `SELL` opens a simulated short when the entry triggers. `WAIT` records no paper position. This is a single-share simulation with a 15-basis-point round-trip cost assumption. The app sends no broker orders.

## Evaluation

The evaluator checks the latest completed stock bar, indicator warm-up, ATR, relative volume, the prior 20-bar range, the 20-period EMA and the current session's aligned Nifty 50 return. A mapped sector return can veto the signal when it disagrees. The initial strategy requires a breakout in the same direction as the benchmark. A missing sector mapping allows a benchmark-only decision. Official events, fundamentals, news and portfolio state are outside the baseline inputs.

Python calculates tick-aligned entry, entry limit, target and stop. The rule requires at least 1.5 units of estimated net reward per unit of estimated net risk at the least favorable entry in the band. A setup expires on a 15-minute boundary, at most 60 minutes after the setup bar started and by 15:15 IST. The strategy uses regular-session timing and received candle timestamps. A verified exchange calendar and special-session coverage remain future work.

The `SignalModel` interface receives candidate identity, direction and named numeric evidence after deterministic gates pass. The configured `NoOpSignalModel` defers to the baseline. A future adapter can approve or abstain with references to the supplied evidence. A missing, invalid or abstaining assessment from a configured model yields `WAIT`. An accepted model response cannot set price levels.

## Simulation

Open **Paper trades** and select **Check outcome** to replay eligible candles through the latest completed bar. Later refreshes catch up from the saved cursor. The tracker uses only candles that start after the signal. It skips entries that gap beyond the allowed price band and uses conservative fills when price order within the candle is ambiguous. An opening gap through a stop may fill worse than the stop. A completed position is booked at a target, stop or time exit without needing the model.

The journal records entry and exit bar timestamps, simulated prices, exit reason, gross and net P&L, and `WIN`, `LOSS` or `FLAT` based on net P&L. Unfilled or unresolved positions are recorded separately. Missing intraday bars can make an outcome unresolved. This implementation simulates each signal independently, so its history is not a portfolio or a return estimate. Outcome checks run on request and can be repeated without replaying already processed bars.

## Storage

The local POSIX store writes `.cache/paper-trades.json` with advisory locking and atomic replacement. The journal is ignored by Git. Each schema-versioned record pairs one immutable signal plan with the latest execution state. Decimal values serialize as strings and timestamps include offsets.

For a shared or hosted journal, use **MongoDB** with one document per signal. Use `plan.signal_id` as the unique document ID, BSON UTC dates and Decimal128 for numeric values. Index active status and expiry for refresh jobs and index exchange, symbol and signal time for history. Compare and update using a revision to keep concurrent refreshes from overwriting newer state. The adapter would implement the existing `PaperTradeStore` protocol. SQLite is the simpler migration if the app remains local and SQL analytics becomes the priority. [MongoDB data modeling](https://www.mongodb.com/docs/manual/data-modeling/) · [SQLite usage](https://www.sqlite.org/whentouse.html)

## Local endpoints

- `POST /api/v1/analyses` evaluates one exchange and symbol and registers an eligible setup once for its completed bar and policy.
- `GET /api/v1/paper-trades` returns the stored journal.
- `POST /api/v1/paper-trades/{signal_id}/refresh` checks an existing setup against completed Kite candles.

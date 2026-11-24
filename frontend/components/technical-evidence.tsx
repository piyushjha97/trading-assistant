import { BarChart3 } from "lucide-react";
import { intervals, marketDate, marketTime, price, type Interval } from "../lib/market";
import type { EvidenceState } from "../lib/technical-evidence";

const studies = [
  { label: "SMA / EMA", description: "Trend direction", keys: ["sma", "ema"] },
  { label: "Wilder RSI", description: "Momentum", keys: ["rsi"] },
  { label: "Wilder ATR", description: "Volatility", keys: ["atr"] },
  { label: "Wilder ADX", description: "Trend strength", keys: ["adx"] },
  { label: "Relative volume", description: "Trading participation", keys: ["relative_volume"] },
  { label: "Prior high / low", description: "Breakout context", keys: ["prior_range_high", "prior_range_low"] },
] as const;

export function TechnicalEvidencePanel({ state, interval }: { state: EvidenceState; interval: Interval }) {
  const evidence = state.status === "loaded" ? state.evidence : null;
  const snapshot = evidence?.snapshot;
  const lastBar = snapshot?.last_candle_at;
  const intervalLabel = intervals[interval].label;
  let summary = "Load market data to calculate indicators for this interval.";
  if (state.status === "loading") summary = "Calculating indicators from Kite candles.";
  if (state.status === "error") summary = state.message;
  if (snapshot) {
    summary = lastBar ? `${snapshot.candle_count} completed bars · Last bar started ${marketDate(lastBar)}${interval === "day" ? "" : `, ${marketTime(lastBar)} IST`}` :
      "Kite returned no eligible completed bars for this interval.";
  }

  return (
    <section className="panel technical-panel" id="technicals" aria-busy={state.status === "loading"}>
      <div className="section-title">
        <BarChart3 size={20} />
        <div><h2>Technical evidence</h2><p role="status">{summary}</p></div>
        <span className="pending-badge">{intervalLabel}</span>
      </div>
      <div className="technical-grid">
        {studies.map(({ label, description, keys }) => {
          const values = keys.map((key) => snapshot?.[key]);
          const available = values.some((value) => value != null);
          return (
            <div key={label} className="study">
              <span>{description}</span><strong>{label}</strong>
              <span className="study-value">
                {available ? values.map((value) => price(value)).join(" / ") + (keys[0] === "relative_volume" ? "×" : "") :
                  evidence ? (evidence.status === "insufficient_history" ? "Insufficient history" : "Unavailable") : "—"}
              </span>
            </div>
          );
        })}
      </div>
      {!!evidence?.notes.length && (
        <details className="evidence-notes">
          <summary>Data coverage and timing</summary>
          <ul>{evidence.notes.map((note) => <li key={note}>{note}</li>)}</ul>
        </details>
      )}
    </section>
  );
}

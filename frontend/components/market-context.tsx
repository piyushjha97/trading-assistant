import { BellRing, ClipboardList, Globe2, Layers3 } from "lucide-react";
import { marketDate, marketTime, price } from "../lib/market";
import type { MarketContextState } from "../lib/market-context";

const labels = {
  benchmark_return: "Benchmark return",
  stock_vs_benchmark: "Stock vs benchmark",
  sector_return: "Sector return",
  stock_vs_sector: "Stock vs sector",
  vix_level: "India VIX",
  vix_change: "India VIX change",
};

const gapLabels: Record<string, string> = {
  stock_bars_unavailable: "Stock comparison bars unavailable.",
  benchmark_bars_unavailable: "Matching benchmark bars unavailable.",
  sector_mapping_unavailable: "No sector index configured for this listing.",
  sector_bars_unavailable: "Matching sector bars unavailable.",
  volatility_bars_unavailable: "Matching India VIX bars unavailable.",
};

const units = { percent: "%", percentage_points: " pp", index_points: " pts" };

export function MarketContextPanel({ state }: { state: MarketContextState }) {
  const snapshot = state.status === "loaded" ? state.snapshot : null;
  const metrics = snapshot?.market.metrics ?? [];
  let message = "Load market data to compare the stock with its benchmark and sector.";
  if (state.status === "loading") message = "Loading benchmark, sector and volatility data from Kite.";
  if (state.status === "error") message = state.message;
  if (snapshot) {
    const { interval, start_bar, end_bar } = snapshot.request;
    const start = interval === "day" ? marketDate(start_bar) : marketTime(start_bar);
    const end = interval === "day" ? marketDate(end_bar) : marketTime(end_bar);
    message = metrics.length
      ? interval === "day" ? `Kite · Daily closes from ${start} to ${end}`
        : `Kite · ${marketDate(end_bar)} · Bar starts ${start} to ${end} IST`
      : "Kite returned no benchmark, sector or volatility bars for this comparison window.";
  }

  return (
    <section id="context" className="context-section">
      <div className="section-title context-title"><ClipboardList size={20} /><div><h2>Market context</h2></div></div>
      <div className="context-grid">
        <article className="panel context-panel" aria-busy={state.status === "loading"}>
          <div className="context-panel-top"><Globe2 size={20} /></div>
          <h3>Market &amp; sector</h3>
          <p role="status">{message}</p>
          {metrics.length > 0 && <ul>
            {metrics.map(({ kind, instrument, value, unit }) => (
              <li key={kind}>{labels[kind]}{kind.startsWith("vix_") ? "" : ` · ${instrument.split(":")[1]}`}
                <span>{price(value)}{units[unit]}</span>
              </li>
            ))}
          </ul>}
          {snapshot?.market.gaps.map((gap) => <p key={gap}>{gapLabels[gap] ?? gap}</p>)}
        </article>
        <article className="panel context-panel">
          <div className="context-panel-top"><BellRing size={20} /><span>No feed connected</span></div>
          <h3>Catalysts &amp; news</h3>
          <p>Company filings, earnings dates, and industry or macro news are currently unavailable.</p>
        </article>
        <article className="panel context-panel">
          <div className="context-panel-top"><Layers3 size={20} /><span>No feed connected</span></div>
          <h3>Fundamentals</h3>
          <p>Company results and balance sheet data are currently unavailable.</p>
        </article>
      </div>
    </section>
  );
}

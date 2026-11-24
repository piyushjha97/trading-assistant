"use client";

import {
  Activity, BarChart3, BellRing, CandlestickChart, ChartNoAxesCombined, CircleHelp,
  ClipboardList, Database, Globe2, Layers3, LoaderCircle, RefreshCw, Search, ShieldCheck, Sparkles,
} from "lucide-react";
import { useRef, useState, type FormEvent } from "react";
import {
  horizonIntervals, intervals, marketDate, marketTime, price, quantity,
  stockPresets, symbolPattern, type Exchange, type Horizon, type Interval,
  type MarketQuery, type MarketResult,
} from "../lib/market";
import { PriceChart } from "./price-chart";

const studies = [
  ["SMA + EMA", "Trend direction"],
  ["Wilder RSI", "Momentum"],
  ["Wilder ATR", "Volatility"],
  ["Wilder ADX", "Trend strength"],
  ["Relative volume", "Trading participation"],
  ["Prior high / low", "Breakout context"],
];

const contextPanels = [
  {
    title: "Market & sector",
    icon: Globe2,
    text: "Compare the stock with its benchmark and sector at the same market cutoff.",
    items: ["Benchmark return", "Sector relative strength", "Market volatility"],
  },
  {
    title: "Catalysts",
    icon: BellRing,
    text: "A timeline for company filings, upcoming events, and relevant industry news.",
    items: ["Company filings", "Earnings calendar", "Industry & macro news"],
  },
  {
    title: "Fundamentals",
    icon: Layers3,
    text: "Company context for swing research and exposure around scheduled results.",
    items: ["Latest results", "Recent corporate actions", "Balance sheet context"],
  },
];

const blankResult: MarketResult = { quote: null, candles: null, issues: {} };
const initialQuery: MarketQuery = { exchange: "NSE", symbol: "INFY", interval: "15minute" };

export default function Dashboard() {
  const [query, setQuery] = useState(initialQuery);
  const [input, setInput] = useState(initialQuery.symbol);
  const [horizon, setHorizon] = useState<Horizon>("Intraday");
  const [result, setResult] = useState<MarketResult>(blankResult);
  const [loading, setLoading] = useState(false);
  const [formError, setFormError] = useState("");
  const [navigation, setNavigation] = useState("overview");
  const currentRequest = useRef<AbortController | null>(null);

  const preset = stockPresets.find((stock) => stock.symbol === query.symbol);
  const title = preset?.name ?? query.symbol;
  const { quote, candles: batch, issues } = result;
  const candles = batch?.candles ?? [];
  const rawQuoteTime = quote?.provider_timestamp ?? quote?.last_trade_time;
  // Kite equity quote times can be supplied without a UTC offset. Interpret those as IST.
  const quoteTime = rawQuoteTime && !/(?:Z|[+-]\d{2}:?\d{2})$/i.test(rawQuoteTime) ? rawQuoteTime + "+05:30" : rawQuoteTime;
  const previousClose = Number(quote?.previous_close ?? 0);
  const change = quote && previousClose > 0 ? Number(quote.last_price) - previousClose : null;
  const hasMarketData = !!(quote || candles.length);
  const failures = Object.values(issues).filter(Boolean);
  const feedLabel = loading ? "Loading Kite" : hasMarketData ? "Kite snapshot" : failures.length ? "Feed unavailable" : "Local workspace";

  async function loadMarket(nextQuery: MarketQuery) {
    currentRequest.current?.abort();
    const controller = new AbortController();
    currentRequest.current = controller;
    setLoading(true);
    setResult(blankResult);
    setFormError("");
    setQuery(nextQuery);
    setInput(nextQuery.symbol);
    try {
      const url = new URLSearchParams({ ...nextQuery });
      const response = await fetch("/api/market?" + url, { signal: controller.signal, cache: "no-store" });
      if (!response.ok) throw new Error("Market data could not be loaded. Check the symbol and try again.");
      const data = await response.json() as MarketResult;
      if (!controller.signal.aborted) setResult(data);
    } catch (error) {
      if (controller.signal.aborted) return;
      const message = error instanceof Error ? error.message : "Market data is unavailable.";
      setResult({ ...blankResult, issues: { candles: message, quote: message } });
    } finally {
      if (!controller.signal.aborted) setLoading(false);
    }
  }

  function onLoad(event: FormEvent<HTMLFormElement>) {
    event.preventDefault();
    const symbol = input.trim().toUpperCase();
    if (!symbolPattern.test(symbol)) {
      setFormError("Enter a trading symbol such as INFY or M&M.");
      return;
    }
    void loadMarket({ ...query, symbol });
  }

  function onExchange(exchange: Exchange) {
    currentRequest.current?.abort();
    setLoading(false);
    setResult(blankResult);
    setQuery({ ...query, exchange });
  }

  function selectHorizon(value: Horizon) {
    setHorizon(value);
    const next = { ...query, interval: horizonIntervals[value] };
    if (next.interval !== query.interval) {
      void loadMarket(next);
    }
  }

  return (
    <div className="workspace">
      <a className="skip-link" href="#overview">Skip to research workspace</a>
      <header className="topbar">
        <a className="brand" href="#overview" onClick={() => setNavigation("overview")}>
          <span className="brand-mark"><ChartNoAxesCombined size={21} strokeWidth={2.3} /></span>
          <span>Trading Assistant</span>
        </a>
        <nav aria-label="Workspace" className="top-nav">
          {[["overview", "Overview"], ["technicals", "Technicals"], ["context", "Market context"]].map(([id, label]) => (
            <a key={id} href={"#" + id} className={navigation === id ? "nav-active" : undefined} onClick={() => setNavigation(id)}>
              {label}
            </a>
          ))}
        </nav>
        <span className={"feed-badge" + (hasMarketData ? " available" : "")}>
          <i />{feedLabel}
        </span>
      </header>

      <div className="workspace-layout">
        <aside className="watchlist" aria-label="Stock shortcuts">
          <div className="watchlist-heading"><span>Watchlist</span><span className="exchange-label">NSE</span></div>
          <div className="watch-items">
            {stockPresets.map((stock) => (
              <button
                key={stock.symbol}
                className={"watch-stock" + (query.symbol === stock.symbol && query.exchange === "NSE" ? " watch-active" : "")}
                aria-pressed={query.symbol === stock.symbol && query.exchange === "NSE"}
                onClick={() => void loadMarket({ ...query, exchange: "NSE", symbol: stock.symbol })}
              >
                <span className={"stock-mark " + stock.color}>{stock.symbol.slice(0, 1)}</span>
                <span className="watch-name"><b>{stock.symbol}</b><span>{stock.name}</span></span>
              </button>
            ))}
          </div>
          <div className="watch-foot">
            <ShieldCheck size={18} />
            <div><strong>Private workspace</strong><span>Research and analysis</span></div>
          </div>
        </aside>

        <main id="overview" className="workspace-main">
          <div className="workspace-intro">
            <div><h1>Research workspace</h1><p>Analyze Indian equities across intraday and swing horizons.</p></div>
            <span className="clock-label">Market time · IST</span>
          </div>

          <form className="controls" onSubmit={onLoad}>
            <div className="control instrument-control">
              <label htmlFor="stock-symbol">Instrument</label>
              <div className="symbol-entry">
                <Search size={18} />
                <input
                  id="stock-symbol" autoComplete="off" spellCheck={false} maxLength={32}
                  value={input} onChange={(event) => { setInput(event.target.value.toUpperCase()); setFormError(""); }}
                  aria-invalid={!!formError} aria-describedby={formError ? "symbol-error" : undefined}
                />
              </div>
            </div>
            <div className="control exchange-control">
              <label htmlFor="stock-exchange">Exchange</label>
              <select id="stock-exchange" value={query.exchange} onChange={(event) => onExchange(event.target.value as Exchange)}>
                <option value="NSE">NSE</option><option value="BSE">BSE</option>
              </select>
            </div>
            <div className="control horizon-control">
              <span>Horizon</span>
              <div className="segmented" role="group" aria-label="Research horizon">
                {(["Intraday", "Swing"] as const).map((item) => (
                  <button key={item} type="button" aria-pressed={horizon === item} onClick={() => selectHorizon(item)}>{item}</button>
                ))}
              </div>
            </div>
            <button type="submit" className="load-button" disabled={loading}>
              {loading ? <LoaderCircle className="spin" size={17} /> : <RefreshCw size={17} />}
              <span>{loading ? "Loading data" : "Load market data"}</span>
            </button>
            {formError && <p id="symbol-error" className="form-error" role="alert">{formError}</p>}
          </form>

          <div className="research-grid">
            <section className="panel chart-panel" aria-label="Price and volume chart">
              <div className="instrument-header">
                <div className="instrument-summary">
                  <span className={"instrument-mark stock-mark " + (preset?.color ?? "mint")}>{query.symbol[0]}</span>
                  <div><div className="instrument-code">{query.exchange}:{query.symbol}</div><h2>{title}</h2></div>
                </div>
                <div className="quote">
                  <strong>{quote ? "₹" + price(quote.last_price) : "—"}</strong>
                  {change !== null ? (
                    <span className={change < 0 ? "negative" : "positive"}>
                      {change >= 0 ? "+" : "−"}{price(Math.abs(change))} ({price(Math.abs(change) * 100 / previousClose)}%)
                    </span>
                  ) : <span>{issues.quote ? "Quote unavailable" : "Last price"}</span>}
                </div>
              </div>

              <div className="chart-toolbar">
                <div className="chart-title"><CandlestickChart size={18} /><strong>Price &amp; volume</strong></div>
                <div className="segmented timeframe" role="group" aria-label="Chart interval">
                  {(Object.keys(intervals) as Interval[]).map((interval) => (
                    <button key={interval} type="button" aria-pressed={interval === query.interval}
                      onClick={() => { if (interval !== query.interval) void loadMarket({ ...query, interval }); }}>
                      {intervals[interval].label}
                    </button>
                  ))}
                </div>
              </div>
              <PriceChart key={query.exchange + ":" + query.symbol + ":" + query.interval} candles={candles} interval={query.interval} loading={loading} error={issues.candles} />
              <dl className="quote-stats">
                <div><dt>Day open</dt><dd>{price(quote?.open)}</dd></div>
                <div><dt>Day high</dt><dd>{price(quote?.high)}</dd></div>
                <div><dt>Day low</dt><dd>{price(quote?.low)}</dd></div>
                <div><dt>Day volume</dt><dd>{quantity(quote?.volume)}</dd></div>
              </dl>
              <div className="chart-footer">
                <span>{batch ? "Source: Zerodha Kite" : "Zerodha Kite · Market data"}</span>
                <span>{candles.length ? candles.length + " bars · Latest bar may be forming" : "Chart times in IST"}</span>
              </div>
            </section>

            <aside className="analysis-rail" aria-label="Readiness and explanation">
              <section className="panel rail-panel" aria-live="polite">
                <div className="panel-title"><Database size={18} /><h2>Data readiness</h2></div>
                <ul className="readiness-list">
                  <li><span className={quote ? "state-dot good" : issues.quote ? "state-dot failed" : "state-dot"} /><div><strong>Kite quote</strong><span>{quoteTime ? "As of " + marketDate(quoteTime) + ", " + marketTime(quoteTime) + " IST" : quote ? "Received · source time unavailable" : issues.quote ? "Unavailable" : loading ? "Fetching snapshot" : "Awaiting snapshot"}</span></div></li>
                  <li><span className={candles.length ? "state-dot good" : issues.candles ? "state-dot failed" : "state-dot"} /><div><strong>{intervals[query.interval].label} candles</strong><span>{batch?.candles.length ? "Fetched " + marketDate(batch.received_at) + ", " + marketTime(batch.received_at) + " IST" : issues.candles ? "Unavailable" : loading ? "Fetching candles" : "Awaiting candles"}</span></div></li>
                  <li><span className="state-dot" /><div><strong>Evidence validation</strong><span>Awaiting analysis service</span></div></li>
                </ul>
                {issues.quote && issues.quote !== issues.candles && <p className="connection-note" role="status">{issues.quote}</p>}
              </section>
              <section className="panel rail-panel brief-panel">
                <div className="brief-icon"><Sparkles size={19} /></div>
                <h2>AI research brief</h2>
                <p>Review the setup, conflicting signals, and reasons to wait once the analysis service is connected.</p>
                <div className="brief-state"><CircleHelp size={15} /> Awaiting validated evidence</div>
              </section>
            </aside>
          </div>

          <section className="panel technical-panel" id="technicals">
            <div className="section-title"><BarChart3 size={20} /><div><h2>Technical evidence</h2><p>Read each indicator alongside its timeframe and input data.</p></div><span className="pending-badge">Analysis service pending</span></div>
            <div className="technical-grid">
              {studies.map(([name, description]) => (
                <div key={name} className="study">
                  <span>{description}</span><strong>{name}</strong><span className="study-value" aria-label="Unavailable">—</span>
                </div>
              ))}
            </div>
          </section>

          <section id="context" className="context-section">
            <div className="section-title context-title"><ClipboardList size={20} /><div><h2>Market context</h2><p>Review what could reinforce or invalidate the setup.</p></div></div>
            <div className="context-grid">
              {contextPanels.map(({ title, icon: Icon, text, items }) => (
                <article className="panel context-panel" key={title}>
                  <div className="context-panel-top"><Icon size={20} /><span>Source pending</span></div>
                  <h3>{title}</h3><p>{text}</p>
                  <ul>{items.map((item) => <li key={item}>{item}<span>—</span></li>)}</ul>
                </article>
              ))}
            </div>
          </section>
          <div className="workspace-footer"><Activity size={15} /> Trading Assistant · Local research</div>
        </main>
      </div>
    </div>
  );
}

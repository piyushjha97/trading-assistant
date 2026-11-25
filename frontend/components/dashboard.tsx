"use client";

import {
  Activity, CandlestickChart, ChartNoAxesCombined, CircleHelp,
  Database, LoaderCircle, RefreshCw, Search, Sparkles,
} from "lucide-react";
import { useCallback, useEffect, useRef, useState, type FormEvent } from "react";
import {
  horizonIntervals, intervals, marketDate, marketTime, price, quantity,
  symbolPattern, type Exchange, type Horizon, type Interval,
  type MarketQuery, type MarketResult,
} from "../lib/market";
import { loadCompanyNews, loadMarketContext, type CompanyNewsState, type MarketContextState } from "../lib/market-context";
import { MarketContextPanel } from "./market-context";
import { PriceChart } from "./price-chart";
import { TechnicalEvidencePanel } from "./technical-evidence";
import type { EvidenceState, TechnicalEvidence } from "../lib/technical-evidence";
import { Watchlist, type InstrumentResult } from "./watchlist";

async function loadEvidence(params: URLSearchParams, signal: AbortSignal): Promise<EvidenceState> {
  try {
    const response = await fetch("/api/technical-evidence?" + params, { signal, cache: "no-store" });
    if (response.ok) return { status: "loaded", evidence: await response.json() as TechnicalEvidence };
    const { error } = await response.json();
    return { status: "error", message: error, loginRequired: response.status === 401 };
  } catch {
    return { status: "error", message: "Technical evidence is temporarily unavailable.", loginRequired: false };
  }
}

const blankResult: MarketResult = { quote: null, candles: null, issues: {} };
const initialQuery: MarketQuery = { exchange: "NSE", symbol: "INFY", interval: "15minute" };
const navigationSections = [
  ["overview", "Overview"],
  ["technicals", "Technicals"],
  ["context", "Market context"],
] as const;

type NavigationSection = (typeof navigationSections)[number][0];
const kiteMessages: Record<string, string> = {
  setup: "Add KITE_API_SECRET to the backend’s .env, set the Kite callback URL, and restart the backend.",
  retry: "Kite sign-in did not complete. Select Connect Kite and try again.",
  unavailable: "Kite sign-in is unavailable. Check that the local backend is running and try again.",
};

export default function Dashboard() {
  const [query, setQuery] = useState(initialQuery);
  const [input, setInput] = useState(initialQuery.symbol);
  const [horizon, setHorizon] = useState<Horizon>("Intraday");
  const [result, setResult] = useState<MarketResult>(blankResult);
  const [news, setNews] = useState<CompanyNewsState>({ status: "idle" });
  const [context, setContext] = useState<MarketContextState>({ status: "idle" });
  const [technical, setTechnical] = useState<EvidenceState>({ status: "idle" });
  const [selectedInstrument, setSelectedInstrument] = useState<InstrumentResult | null>(null);
  const [loading, setLoading] = useState(false);
  const [formError, setFormError] = useState("");
  const [connectionMessage, setConnectionMessage] = useState("");
  const [navigation, setNavigation] = useState<NavigationSection>("overview");
  const workspace = useRef<HTMLDivElement>(null);
  const topbar = useRef<HTMLElement>(null);
  const currentRequest = useRef<AbortController | null>(null);

  useEffect(() => {
    const header = topbar.current;
    const layout = workspace.current;
    const technicals = document.getElementById("technicals");
    const context = document.getElementById("context");
    if (!header || !layout || !technicals || !context) return;

    let technicalsStart = 0;
    let contextStart = 0;

    function updateActiveTab() {
      // Allow for fractional anchor positions rounded by the browser.
      const position = window.scrollY + 2;
      setNavigation(position >= contextStart ? "context" :
        position >= technicalsStart ? "technicals" : "overview");
    }

    const measureSections = () => {
      const clearance = header.offsetHeight + 16;
      const technicalsTop = technicals.getBoundingClientRect().top + window.scrollY;
      const contextTop = context.getBoundingClientRect().top + window.scrollY;
      const maxScroll = document.documentElement.scrollHeight - window.innerHeight;
      const naturalContextStart = Math.max(0, contextTop - clearance);
      // Keep both lower anchors reachable when the page is shorter than their offsets.
      const scale = maxScroll > 0 && naturalContextStart > maxScroll
        ? maxScroll / naturalContextStart : 1;
      technicalsStart = Math.max(0, technicalsTop - clearance) * scale;
      contextStart = naturalContextStart * scale;
      technicals.style.scrollMarginTop = `${technicalsTop - technicalsStart}px`;
      context.style.scrollMarginTop = `${contextTop - contextStart}px`;
      layout.style.setProperty("--section-scroll-clearance", `${clearance}px`);
      updateActiveTab();
    };

    measureSections();
    const initialSection = window.location.hash;
    if (initialSection === "#technicals" || initialSection === "#context") {
      (initialSection === "#technicals" ? technicals : context).scrollIntoView({ behavior: "instant" });
      updateActiveTab();
    }
    const resizeObserver = new ResizeObserver(measureSections);
    resizeObserver.observe(layout);
    resizeObserver.observe(header);
    window.addEventListener("resize", measureSections);
    window.addEventListener("scroll", updateActiveTab, { passive: true });
    return () => {
      resizeObserver.disconnect();
      window.removeEventListener("resize", measureSections);
      window.removeEventListener("scroll", updateActiveTab);
    };
  }, []);

  const title = selectedInstrument?.symbol === query.symbol && selectedInstrument.exchange === query.exchange
    ? selectedInstrument.name || query.symbol : query.symbol;
  const { quote, candles: batch, issues } = result;
  const candles = batch?.candles ?? [];
  const lastChartBar = candles.at(-1);
  const rawQuoteTime = quote?.last_trade_time ?? quote?.provider_timestamp;
  // Kite equity quote times can be supplied without a UTC offset. Interpret those as IST.
  const quoteTime = rawQuoteTime && !/(?:Z|[+-]\d{2}:?\d{2})$/i.test(rawQuoteTime) ? rawQuoteTime + "+05:30" : rawQuoteTime;
  const previousClose = Number(quote?.previous_close ?? 0);
  const change = quote && previousClose > 0 ? Number(quote.last_price) - previousClose : null;
  const hasMarketData = !!(quote || candles.length);
  const failures = Object.values(issues).filter(Boolean);
  const feedLabel = loading ? "Loading Kite" : hasMarketData ? "Kite snapshot" : failures.length ? "Feed unavailable" : "Local workspace";

  const loadMarket = useCallback(async (nextQuery: MarketQuery) => {
    currentRequest.current?.abort();
    const controller = new AbortController();
    currentRequest.current = controller;
    setLoading(true);
    setResult(blankResult);
    setTechnical({ status: "loading" });
    setContext({ status: "loading" });
    setNews({ status: "loading" });
    setFormError("");
    setConnectionMessage("");
    setQuery(nextQuery);
    setInput(nextQuery.symbol);
    const params = new URLSearchParams({ ...nextQuery });
    void loadCompanyNews(nextQuery.exchange, nextQuery.symbol, controller.signal).then((nextNews) => {
      if (!controller.signal.aborted) setNews(nextNews);
    });
    const technicalRequest = loadEvidence(params, controller.signal).then((evidence) => {
      if (!controller.signal.aborted) setTechnical(evidence);
    });
    try {
      const response = await fetch("/api/market?" + params, { signal: controller.signal, cache: "no-store" });
      const data = await response.json() as MarketResult | { error: string };
      if ("error" in data) throw new Error(data.error);
      if (!controller.signal.aborted) setResult(data);
    } catch (error) {
      if (controller.signal.aborted) return;
      const message = error instanceof Error ? error.message : "Market data is unavailable.";
      setResult({ ...blankResult, issues: { candles: message, quote: message } });
    } finally {
      if (!controller.signal.aborted) setLoading(false);
    }

    // Let the foreground candle requests finish before querying other Kite instruments.
    await technicalRequest;
    if (controller.signal.aborted) return;
    const nextContext = await loadMarketContext(params, controller.signal);
    if (!controller.signal.aborted) setContext(nextContext);
  }, []);

  useEffect(() => {
    const url = new URL(window.location.href);
    const connection = url.searchParams.get("kite");
    if (!connection) return;
    url.searchParams.delete("kite");
    window.history.replaceState(window.history.state, "", url);
    const pending = window.sessionStorage.getItem("kite-market-query");
    window.sessionStorage.removeItem("kite-market-query");
    if (connection !== "connected") {
      setConnectionMessage(Object.hasOwn(kiteMessages, connection) ? kiteMessages[connection] : kiteMessages.retry);
      return;
    }
    const params = new URLSearchParams(pending ?? "");
    const exchange = params.get("exchange");
    const symbol = params.get("symbol") ?? "";
    const interval = params.get("interval") ?? "";
    if (params.get("horizon") === "Swing") setHorizon("Swing");
    const validQuery = (exchange === "NSE" || exchange === "BSE") &&
      symbolPattern.test(symbol) && Object.hasOwn(intervals, interval);
    void loadMarket(validQuery ? { exchange, symbol, interval: interval as Interval } : initialQuery);
  }, [loadMarket]);

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
    setTechnical({ status: "idle" });
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
    <div className="workspace" ref={workspace}>
      <a className="skip-link" href="#overview">Skip to research workspace</a>
      <header className="topbar" ref={topbar}>
        <a className="brand" href="#overview" onClick={() => setNavigation("overview")}>
          <span className="brand-mark"><ChartNoAxesCombined size={21} strokeWidth={2.3} /></span>
          <span>Trading Assistant</span>
        </a>
        <nav aria-label="Workspace" className="top-nav">
          {navigationSections.map(([id, label]) => (
            <a key={id} href={"#" + id} className={navigation === id ? "nav-active" : undefined}
              aria-current={navigation === id ? "location" : undefined} onClick={() => setNavigation(id)}>
              {label}
            </a>
          ))}
        </nav>
        <span className={"feed-badge" + (hasMarketData ? " available" : "")}>
          <i />{feedLabel}
        </span>
      </header>

      <div className="workspace-layout">
        <Watchlist selected={query} onSelect={(instrument) => {
          setSelectedInstrument(instrument);
          void loadMarket({ ...query, exchange: instrument.exchange, symbol: instrument.symbol });
        }} />

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
                  <span className="instrument-mark stock-mark mint">{query.symbol[0]}</span>
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
                <div className="chart-title"><CandlestickChart size={18} /><strong>Price &amp; volume snapshot</strong></div>
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
                <span>{lastChartBar ? `Last bar started ${marketDate(lastChartBar.timestamp)}${query.interval === "day" ? "" : `, ${marketTime(lastChartBar.timestamp)} IST`} · May be forming` : "Chart times in IST"}</span>
              </div>
            </section>

            <aside className="analysis-rail" aria-label="Readiness and explanation">
              <section className="panel rail-panel" aria-live="polite">
                <div className="panel-title"><Database size={18} /><h2>Data readiness</h2></div>
                <ul className="readiness-list">
                  <li><span className={quote ? "state-dot good" : issues.quote ? "state-dot failed" : "state-dot"} /><div><strong>Kite quote</strong><span>{quoteTime ? `${quote?.last_trade_time ? "Last traded" : "Quote timestamp"} ${marketDate(quoteTime)}, ${marketTime(quoteTime)} IST` : quote ? "Received · source time unavailable" : issues.quote ? "Unavailable" : loading ? "Fetching snapshot" : "Awaiting snapshot"}</span></div></li>
                  <li><span className={candles.length ? "state-dot good" : issues.candles ? "state-dot failed" : "state-dot"} /><div><strong>{intervals[query.interval].label} candles</strong><span>{batch?.candles.length ? "Fetched " + marketDate(batch.received_at) + ", " + marketTime(batch.received_at) + " IST" : issues.candles ? "Unavailable" : loading ? "Fetching candles" : "Awaiting candles"}</span></div></li>
                  <li><span className={technical.status === "loaded" && technical.evidence.status === "ready" ? "state-dot good" : technical.status === "error" ? "state-dot failed" : "state-dot"} /><div><strong>Technical evidence</strong><span>{technical.status === "loaded" ? `${technical.evidence.snapshot.candle_count} eligible bars` : technical.status === "loading" ? "Calculating indicators" : technical.status === "error" ? "Unavailable" : "Awaiting data"}</span></div></li>
                </ul>
                {issues.quote && issues.quote !== issues.candles && <p className="connection-note" role="status">{issues.quote}</p>}
                {connectionMessage && <p className="connection-note" role="status">{connectionMessage}</p>}
                {!loading && (result.kiteLoginRequired || (technical.status === "error" && technical.loginRequired) || (context.status === "error" && context.loginRequired) || (news.status === "error" && news.loginRequired) || !hasMarketData) && (
                  <a className="kite-connect" href="/api/kite/login" onClick={() => {
                    const symbol = input.trim().toUpperCase();
                    window.sessionStorage.setItem("kite-market-query", new URLSearchParams({
                      ...query, symbol: symbolPattern.test(symbol) ? symbol : query.symbol, horizon,
                    }).toString());
                  }}>Connect Kite</a>
                )}
              </section>
              <section className="panel rail-panel brief-panel">
                <div className="brief-icon"><Sparkles size={19} /></div>
                <h2>AI research brief</h2>
                <p>Review the setup, conflicting signals, and reasons to wait once the analysis service is connected.</p>
                <div className="brief-state"><CircleHelp size={15} /> Awaiting validated evidence</div>
              </section>
            </aside>
          </div>

          <TechnicalEvidencePanel state={technical} interval={query.interval} />

          <MarketContextPanel state={context} news={news} />
          <div className="workspace-footer"><Activity size={15} /> Trading Assistant · Local research</div>
        </main>
      </div>
    </div>
  );
}

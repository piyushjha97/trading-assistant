"use client";

import { useEffect, useState } from "react";
import { Activity, ClipboardList } from "lucide-react";
import { marketDate, marketTime, price, type Exchange } from "../lib/market";

interface Setup {
  signal_id: string;
  entry_trigger: string;
  entry_limit: string;
  target: string;
  stop: string;
  signal_at: string;
  expires_at: string;
}

interface Signal {
  verdict: "BUY" | "SELL" | "WAIT";
  reasons: string[];
  setup: Setup | null;
  model_status: string;
}

interface PaperTrade {
  plan: Setup & { exchange: Exchange; symbol: string; side: "BUY" | "SELL"; round_trip_cost_bps: string };
  status: "PENDING" | "OPEN" | "CLOSED" | "EXPIRED" | "UNRESOLVED";
  entry_fill_price: string | null;
  exit_fill_price: string | null;
  entry_bar_at: string | null;
  exit_bar_at: string | null;
  exit_reason: "TARGET" | "STOP" | "TIME" | null;
  gross_pnl_per_share: string | null;
  net_pnl_per_share: string | null;
  outcome: "WIN" | "LOSS" | "FLAT" | null;
}

const reasons: Record<string, string> = {
  outside_session: "The intraday paper strategy runs during regular market hours.",
  recent_completed_bar_required: "Kite hasn’t supplied the latest completed 15-minute candle.",
  insufficient_time_to_track: "There’s too little time left in the session to simulate the setup.",
  insufficient_technical_history: "More completed candles are needed to evaluate the setup.",
  weak_volume_or_volatility: "The candle didn’t meet the volume or volatility requirement.",
  no_supported_breakout: "The latest completed candle didn’t confirm a breakout.",
  aligned_benchmark_unavailable: "A matching benchmark candle is unavailable.",
  market_or_sector_disagrees: "The benchmark or available sector data conflicts with the breakout.",
  instrument_tick_size_unavailable: "An equity tick size is unavailable for this listing.",
  levels_or_estimated_cost_invalid: "The setup didn’t clear the level and estimated cost checks.",
  model_response_invalid: "The model assessment couldn’t be validated.",
  model_evidence_invalid: "The model cited evidence outside the supplied snapshot.",
  model_abstained: "The model abstained on this candidate.",
  breakout_confirmed: "The latest completed candle confirmed a breakout.",
  benchmark_aligned: "The benchmark moved in the same direction.",
};
const statusLabels = {
  PENDING: "Awaiting entry", OPEN: "Open", CLOSED: "Closed", EXPIRED: "Expired unfilled", UNRESOLVED: "Unresolved",
};
const exitLabels = { TARGET: "Target hit", STOP: "Stop hit", TIME: "Time exit" };

function at(iso: string) {
  return `${marketDate(iso)}, ${marketTime(iso)} IST`;
}

async function paperRequest<T>(uri: string, init?: RequestInit): Promise<T> {
  const response = await fetch(uri, { ...init, cache: "no-store" });
  const data = await response.json();
  if (!response.ok) throw new Error(data.error ?? "Couldn’t complete the paper-trading request.");
  return data as T;
}

function SetupDetails({ setup }: { setup: Setup }) {
  return (
    <dl className="paper-details">
      <div><dt>Entry trigger</dt><dd>₹{price(setup.entry_trigger)}</dd></div>
      <div><dt>Entry limit</dt><dd>₹{price(setup.entry_limit)}</dd></div>
      <div><dt>Target</dt><dd>₹{price(setup.target)}</dd></div>
      <div><dt>Stop-loss</dt><dd>₹{price(setup.stop)}</dd></div>
    </dl>
  );
}

export function SignalPanel({ exchange, symbol, onRegistered }: {
  exchange: Exchange;
  symbol: string;
  onRegistered: () => void;
}) {
  const [signal, setSignal] = useState<Signal | null>(null);
  const [loading, setLoading] = useState(false);
  const [error, setError] = useState("");

  async function generate() {
    setLoading(true);
    setError("");
    setSignal(null);
    try {
      const data = await paperRequest<Signal>("/api/analyses", {
        method: "POST", headers: { "Content-Type": "application/json" }, body: JSON.stringify({ exchange, symbol }),
      });
      setSignal(data);
      if (data.setup) onRegistered();
    } catch (cause) {
      setError(cause instanceof Error ? cause.message : "Couldn’t evaluate the signal.");
    } finally {
      setLoading(false);
    }
  }

  return (
    <section className="panel rail-panel brief-panel" aria-busy={loading}>
      <div className="brief-icon"><Activity size={19} /></div>
      <h2>Intraday paper signal</h2>
      <p>{exchange}:{symbol} · 15-minute candles · Rules only</p>
      <button type="button" className="kite-connect paper-button" onClick={generate} disabled={loading}>
        {loading ? "Evaluating…" : "Evaluate & track"}
      </button>
      {error && <p role="alert">{error}</p>}
      {signal && <div className="paper-signal-result" role="status">
        <strong>{signal.verdict === "BUY" ? "BUY · Simulated long" :
          signal.verdict === "SELL" ? "SELL · Simulated short" : "WAIT · No setup"}</strong>
        {signal.reasons.map((reason) => <p key={reason}>{reasons[reason] ?? reason}</p>)}
        {signal.setup && <>
          <SetupDetails setup={signal.setup} />
          <p>Expires {at(signal.setup.expires_at)}</p>
        </>}
      </div>}
    </section>
  );
}

export function PaperTradeHistory({ revision }: { revision: number }) {
  const [trades, setTrades] = useState<PaperTrade[] | null>(null);
  const [busy, setBusy] = useState<string | null>(null);
  const [error, setError] = useState("");

  useEffect(() => {
    const controller = new AbortController();
    void paperRequest<PaperTrade[]>("/api/paper-trades", { signal: controller.signal }).then(
      (data) => { if (!controller.signal.aborted) setTrades(data); },
      (cause) => { if (!controller.signal.aborted) setError(cause instanceof Error ? cause.message : "Couldn’t load paper trades."); },
    );
    return () => controller.abort();
  }, [revision]);

  async function refresh(id: string) {
    setBusy(id);
    setError("");
    try {
      const record = await paperRequest<PaperTrade>(`/api/paper-trades?id=${encodeURIComponent(id)}`, { method: "POST" });
      setTrades((current) => current?.map((trade) => trade.plan.signal_id === id ? record : trade) ?? [record]);
    } catch (cause) {
      setError(cause instanceof Error ? cause.message : "Couldn’t refresh the paper trade.");
    } finally {
      setBusy(null);
    }
  }

  return (
    <section className="panel technical-panel" aria-label="Paper trades">
      <div className="section-title"><ClipboardList size={20} /><div><h2>Paper trades</h2>
        <p>Check outcomes using completed Kite candles.</p>
      </div></div>
      {error && <p role="alert">{error}</p>}
      {!trades?.length && !error && <p>{trades ? "No paper trades recorded yet." : "Loading paper trades…"}</p>}
      {!!trades?.length && <ul className="paper-history">
        {trades.map((trade) => {
          const { plan, status } = trade;
          return (
            <li key={plan.signal_id}>
              <div className="paper-trade-heading">
                <strong>{plan.exchange}:{plan.symbol} · {plan.side} · {trade.outcome ?? statusLabels[status]}</strong>
                {(status === "PENDING" || status === "OPEN") && (
                  <button type="button" className="kite-connect" disabled={busy !== null} onClick={() => refresh(plan.signal_id)}>
                    {busy === plan.signal_id ? "Checking…" : "Check outcome"}
                  </button>
                )}
              </div>
              <p>Signal {at(plan.signal_at)} · Expires {at(plan.expires_at)}</p>
              <SetupDetails setup={plan} />
              {trade.entry_fill_price && <p>Filled at ₹{price(trade.entry_fill_price)}{trade.entry_bar_at ? ` · Bar ${at(trade.entry_bar_at)}` : ""}</p>}
              {trade.exit_fill_price && <p>{trade.exit_reason ? exitLabels[trade.exit_reason] : "Closed"} at ₹{price(trade.exit_fill_price)}{trade.exit_bar_at ? ` · Bar ${at(trade.exit_bar_at)}` : ""}</p>}
              {trade.net_pnl_per_share !== null && (
                <p>Gross P&amp;L ₹{price(trade.gross_pnl_per_share)} · Net P&amp;L ₹{price(trade.net_pnl_per_share)}
                  {" "}per share · {plan.round_trip_cost_bps} bps cost assumption</p>
              )}
            </li>
          );
        })}
      </ul>}
    </section>
  );
}

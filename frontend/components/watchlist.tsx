"use client";

import { Plus, Search, X } from "lucide-react";
import { useEffect, useState } from "react";
import { symbolPattern, type Exchange } from "../lib/market";
import styles from "./watchlist.module.css";

export interface InstrumentResult {
  exchange: Exchange;
  symbol: string;
  name: string;
}

type SearchResult = { query: string } & (
  { instruments: InstrumentResult[] } | { error: string }
);

const storageKey = "trading-assistant-watchlist";

function sameListing(left: Pick<InstrumentResult, "exchange" | "symbol">, right: InstrumentResult) {
  return left.exchange === right.exchange && left.symbol === right.symbol;
}

function isInstrument(value: unknown): value is InstrumentResult {
  if (!value || typeof value !== "object") return false;
  const listing = value as Partial<InstrumentResult>;
  return (listing.exchange === "NSE" || listing.exchange === "BSE") &&
    typeof listing.symbol === "string" && symbolPattern.test(listing.symbol) &&
    typeof listing.name === "string";
}

function savedWatchlist(): InstrumentResult[] {
  try {
    const data: unknown = JSON.parse(window.localStorage.getItem(storageKey) ?? "[]");
    return Array.isArray(data) ? data.filter(isInstrument) : [];
  } catch {
    return [];
  }
}

export function Watchlist({ selected, onSelect }: {
  selected: Pick<InstrumentResult, "exchange" | "symbol">;
  onSelect: (instrument: InstrumentResult) => void;
}) {
  const [input, setInput] = useState("");
  const [saved, setSaved] = useState<InstrumentResult[] | null>(null);
  const [result, setResult] = useState<SearchResult | null>(null);
  const query = input.trim();
  const searching = query.length >= 2;
  const shown = result?.query === query ? result : null;

  useEffect(() => setSaved(savedWatchlist()), []);

  useEffect(() => {
    if (!saved) return;
    try {
      window.localStorage.setItem(storageKey, JSON.stringify(saved));
    } catch {
      // The list remains usable for this visit when browser storage is unavailable.
    }
  }, [saved]);

  useEffect(() => {
    if (!searching) return;
    const controller = new AbortController();
    const timeout = window.setTimeout(async () => {
      try {
        const response = await fetch(`/api/instruments?${new URLSearchParams({ q: query })}`, {
          cache: "no-store", signal: controller.signal,
        });
        const data = await response.json();
        if (controller.signal.aborted) return;
        if (!response.ok) {
          setResult({ query, error: data.error ?? "Search is unavailable." });
          return;
        }
        if (!Array.isArray(data.instruments)) throw new Error("Unexpected search response");
        setResult({ query, instruments: data.instruments.filter(isInstrument) });
      } catch {
        if (!controller.signal.aborted) setResult({ query, error: "Search is unavailable. Try again shortly." });
      }
    }, 250);
    return () => {
      window.clearTimeout(timeout);
      controller.abort();
    };
  }, [query, searching]);

  function add(instrument: InstrumentResult) {
    setSaved((previous) => {
      const list = previous ?? [];
      return list.some((item) => sameListing(item, instrument)) ? list : [...list, instrument];
    });
  }

  function select(instrument: InstrumentResult) {
    setInput("");
    onSelect(instrument);
  }

  function renderInstrument(instrument: InstrumentResult, search: boolean) {
    const alreadySaved = saved?.some((item) => sameListing(item, instrument));
    const isSelected = sameListing(selected, instrument);
    const listing = `${instrument.exchange}:${instrument.symbol}`;
    return (
      <li key={listing} className={styles.row}>
        <button type="button" className={`watch-stock${isSelected ? " watch-active" : ""}`}
          aria-pressed={isSelected} onClick={() => select(instrument)}>
          <span className="watch-name">
            <b>{instrument.symbol} <small className={styles.exchange}>{instrument.exchange}</small></b>
            <span title={instrument.name}>{instrument.name}</span>
          </span>
        </button>
        {search ? (
          <button type="button" className={styles.action} disabled={alreadySaved}
            aria-label={alreadySaved ? `${listing} is in watchlist` : `Add ${listing} to watchlist`}
            onClick={() => add(instrument)}><Plus size={16} /></button>
        ) : (
          <button type="button" className={styles.action} aria-label={`Remove ${listing} from watchlist`}
            onClick={() => setSaved((items) => items?.filter((item) => !sameListing(item, instrument)) ?? [])}><X size={16} /></button>
        )}
      </li>
    );
  }

  const status = !searching ? input.length > 0 ? "Enter at least two characters." : "" :
    !shown ? "Searching Kite…" : "error" in shown ? shown.error :
    shown.instruments.length === 0 ? "No matching instruments." : "";

  return (
    <aside className="watchlist" aria-label="Watchlist">
      <h2 className={styles.heading}>Watchlist</h2>
      <label htmlFor="watchlist-search" className={styles.label}>Search NSE and BSE</label>
      <div className={`symbol-entry ${styles.input}`}>
        <Search size={16} aria-hidden="true" />
        <input id="watchlist-search" type="search" value={input} placeholder="Company or symbol"
          autoComplete="off" maxLength={80} onChange={(event) => setInput(event.target.value)} />
      </div>
      <div aria-live="polite">{status && <p className={styles.status}>{status}</p>}</div>
      {shown && "instruments" in shown && shown.instruments.length > 0 && (
        <ul className={styles.results} aria-label="Instrument search results">
          {shown.instruments.map((item) => renderInstrument(item, true))}
        </ul>
      )}
      {saved?.length ? (
        <ul className="watch-items" aria-label="Saved instruments">
          {saved.map((item) => renderInstrument(item, false))}
        </ul>
      ) : !searching && <p className={styles.status}>Use + to save a search result.</p>}
    </aside>
  );
}

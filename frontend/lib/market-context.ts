import type { Interval } from "./market";

type MetricKind =
  | "benchmark_return" | "stock_vs_benchmark"
  | "sector_return" | "stock_vs_sector" | "vix_level" | "vix_change";

interface MarketContextSnapshot {
  request: { interval: Interval; start_bar: string; end_bar: string };
  market: {
    status: "available" | "partial" | "unavailable" | "not_configured";
    metrics: {
      kind: MetricKind;
      instrument: string;
      value: string;
      unit: "percent" | "percentage_points" | "index_points";
    }[];
    gaps: string[];
  };
}

export type MarketContextState =
  | { status: "idle" | "loading" }
  | { status: "loaded"; snapshot: MarketContextSnapshot }
  | { status: "error"; message: string; loginRequired: boolean };

export async function loadMarketContext(params: URLSearchParams, signal: AbortSignal): Promise<MarketContextState> {
  try {
    const response = await fetch("/api/market-context?" + params, { signal, cache: "no-store" });
    if (response.ok) return { status: "loaded", snapshot: await response.json() as MarketContextSnapshot };
    const { error } = await response.json();
    return { status: "error", message: error, loginRequired: response.status === 401 };
  } catch {
    return { status: "error", message: "Market context is temporarily unavailable.", loginRequired: false };
  }
}

import type { Interval } from "./market";

export interface TechnicalEvidence {
  interval: Interval;
  status: "ready" | "insufficient_history";
  snapshot: {
    candle_count: number;
    last_candle_at: string | null;
    sma: string | null;
    ema: string | null;
    rsi: string | null;
    atr: string | null;
    adx: string | null;
    relative_volume: string | null;
    prior_range_high: string | null;
    prior_range_low: string | null;
  };
  notes: string[];
}

export type EvidenceState =
  | { status: "idle" | "loading" }
  | { status: "loaded"; evidence: TechnicalEvidence }
  | { status: "error"; message: string; loginRequired: boolean };

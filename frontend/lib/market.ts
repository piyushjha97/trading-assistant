export const intervals = {
  "15minute": { label: "15 min", days: 5 },
  "60minute": { label: "1 hour", days: 30 },
  day: { label: "1 day", days: 90 },
} as const;

export type Interval = keyof typeof intervals;
export type Exchange = "NSE" | "BSE";
export type Horizon = "Intraday" | "Swing";

export const horizonIntervals: Record<Horizon, Interval> = {
  Intraday: "15minute",
  Swing: "day",
};

export interface MarketQuery {
  exchange: Exchange;
  symbol: string;
  interval: Interval;
}

export interface Candle {
  timestamp: string;
  open: string;
  high: string;
  low: string;
  close: string;
  volume: number;
}

export interface CandleBatch {
  provider: string;
  exchange: Exchange;
  symbol: string;
  interval: Interval;
  received_at: string;
  candles: Candle[];
}

export interface Quote {
  last_price: string;
  previous_close?: string | null;
  open?: string | null;
  high?: string | null;
  low?: string | null;
  volume?: number | null;
  provider_timestamp?: string | null;
  last_trade_time?: string | null;
  received_at: string;
}

export interface MarketResult {
  kiteLoginRequired?: boolean;
  quote: Quote | null;
  candles: CandleBatch | null;
  issues: {
    quote?: string;
    candles?: string;
  };
}

export const symbolPattern = /^[A-Z0-9&_-]{1,32}$/;

const priceFormatter = new Intl.NumberFormat("en-IN", {
  minimumFractionDigits: 2,
  maximumFractionDigits: 2,
});
const volumeFormatter = new Intl.NumberFormat("en-IN", {
  notation: "compact",
  maximumFractionDigits: 2,
});
const dateFormatter = new Intl.DateTimeFormat("en-IN", {
  timeZone: "Asia/Kolkata",
  day: "numeric",
  month: "short",
});
const timeFormatter = new Intl.DateTimeFormat("en-IN", {
  timeZone: "Asia/Kolkata",
  hour: "2-digit",
  minute: "2-digit",
  hour12: false,
});

export function price(value?: string | number | null) {
  return value == null ? "—" : priceFormatter.format(Number(value));
}

export function quantity(value?: number | null) {
  return value == null ? "—" : volumeFormatter.format(value);
}

export function marketDate(value: string) {
  return dateFormatter.format(new Date(value));
}

export function marketTime(value: string) {
  return timeFormatter.format(new Date(value));
}

import {
  intervals,
  symbolPattern,
  type CandleBatch,
  type Interval,
  type Quote,
} from "../../../lib/market";
import { localBackendUrl } from "../../../lib/backend";

class MarketRequestError extends Error {
  constructor(public readonly status: number, message: string) {
    super(message);
  }
}

async function getFromBackend<T>(path: string, params: URLSearchParams): Promise<T> {
  const url = localBackendUrl(path);
  url.search = params.toString();

  let response: Response;
  try {
    response = await fetch(url, {
      cache: "no-store",
      redirect: "error",
      signal: AbortSignal.timeout(14_000),
    });
  } catch (error) {
    if (error instanceof Error && error.name === "TimeoutError") {
      throw new MarketRequestError(504, "The market data request timed out. Try reloading.");
    }
    throw new MarketRequestError(503, "Couldn’t reach the local backend. Start it and try again.");
  }

  if (response.status === 401) {
    throw new MarketRequestError(401, "Connect to Kite to load market data.");
  }
  if (response.status === 403) {
    throw new MarketRequestError(403, "Kite denied access. Check your plan and data entitlements.");
  }
  if (response.status === 404) {
    throw new MarketRequestError(404, "Kite couldn’t find this symbol on the selected exchange.");
  }
  if (response.status === 429) {
    throw new MarketRequestError(429, "Kite’s request limit was reached. Try again shortly.");
  }
  if (!response.ok) {
    throw new MarketRequestError(response.status, "The local backend couldn’t complete this market data request.");
  }
  return response.json() as Promise<T>;
}

function issue(reason: unknown) {
  return reason instanceof MarketRequestError ? reason : new MarketRequestError(502, "Market data is temporarily unavailable.");
}

export async function GET(request: Request) {
  const params = new URL(request.url).searchParams;
  const exchange = params.get("exchange");
  const symbol = params.get("symbol") ?? "";
  const interval = params.get("interval") ?? "";
  if (
    (exchange !== "NSE" && exchange !== "BSE") ||
    !symbolPattern.test(symbol) ||
    !Object.hasOwn(intervals, interval)
  ) {
    return Response.json({ error: "Choose a valid exchange, symbol, and interval." }, { status: 400 });
  }

  const end = Date.now();
  const days = intervals[interval as Interval].days;
  const candleParams = new URLSearchParams({
    exchange, symbol, interval,
    from: new Date(end - days * 86_400_000).toISOString(),
    to: new Date(end).toISOString(),
  });

  const [quoteResult, candleResult] = await Promise.allSettled([
    getFromBackend<{ quotes: Quote[] }>(
      "/api/v1/market-data/quotes", new URLSearchParams({ symbols: exchange + ":" + symbol }),
    ),
    getFromBackend<CandleBatch>("/api/v1/market-data/candles", candleParams),
  ]);

  const quote = quoteResult.status === "fulfilled" ? quoteResult.value.quotes[0] ?? null : null;
  const candles = candleResult.status === "fulfilled" ? candleResult.value : null;
  const quoteError = quoteResult.status === "rejected" ? issue(quoteResult.reason) : undefined;
  const candleError = candleResult.status === "rejected" ? issue(candleResult.reason) : undefined;
  const kiteLoginRequired = quoteError?.status === 401 || candleError?.status === 401;
  const status = quote || candles?.candles.length ? 200 :
    kiteLoginRequired ? 401 : candleError?.status ?? quoteError?.status ?? 404;
  return Response.json({
    quote,
    candles,
    kiteLoginRequired,
    issues: {
      quote: quoteError?.message ?? (!quote ? "Kite returned no quote for this symbol." : undefined),
      candles: candleError?.message ?? (candles?.candles.length === 0 ? "Kite returned no candles in this window." : undefined),
    },
  }, { status, headers: { "Cache-Control": "no-store" } });
}

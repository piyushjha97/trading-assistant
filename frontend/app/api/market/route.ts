import {
  intervals,
  symbolPattern,
  type CandleBatch,
  type Interval,
  type Quote,
} from "../../../lib/market";

class MarketRequestError extends Error {}

async function getFromBackend<T>(path: string, params: URLSearchParams): Promise<T> {
  const backend = process.env.TRADING_BACKEND_URL ?? "http://127.0.0.1:8000";
  const origin = new URL(backend);
  if (!["http:", "https:"].includes(origin.protocol) ||
      !["localhost", "127.0.0.1", "[::1]"].includes(origin.hostname)) {
    throw new MarketRequestError("The backend address must point to this machine.");
  }
  const url = new URL(path, origin);
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
      throw new MarketRequestError("The market data request timed out. Try reloading.");
    }
    throw new MarketRequestError("Couldn’t reach the local backend. Start it and try again.");
  }

  if (response.status === 401) {
    throw new MarketRequestError("Kite credentials are missing or expired. Refresh the token and restart the backend.");
  }
  if (response.status === 403) {
    throw new MarketRequestError("Kite denied access. Check your plan and data entitlements.");
  }
  if (response.status === 404) {
    throw new MarketRequestError("Kite couldn’t find this symbol on the selected exchange.");
  }
  if (response.status === 429) {
    throw new MarketRequestError("Kite’s request limit was reached. Try again shortly.");
  }
  if (!response.ok) {
    throw new MarketRequestError("The local backend couldn’t complete this market data request.");
  }
  return response.json() as Promise<T>;
}

function issue(reason: unknown) {
  return reason instanceof MarketRequestError ? reason.message : "Market data is temporarily unavailable.";
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
  return Response.json({
    quote,
    candles,
    issues: {
      quote: quoteResult.status === "rejected" ? issue(quoteResult.reason) :
        !quote ? "Kite returned no quote for this symbol." : undefined,
      candles: candleResult.status === "rejected" ? issue(candleResult.reason) :
        candles?.candles.length === 0 ? "Kite returned no candles in this window." : undefined,
    },
  }, { headers: { "Cache-Control": "no-store" } });
}

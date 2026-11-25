import { localBackendUrl } from "../../../lib/backend";
import { symbolPattern } from "../../../lib/market";

const headers = { "Cache-Control": "no-store" };

export async function GET(request: Request) {
  const params = new URL(request.url).searchParams;
  const exchange = params.get("exchange");
  const symbol = params.get("symbol") ?? "";
  if ((exchange !== "NSE" && exchange !== "BSE") || !symbolPattern.test(symbol)) {
    return Response.json({ error: "Choose a valid stock and exchange." }, { status: 400, headers });
  }

  const timeout = AbortSignal.timeout(18_000);
  try {
    const url = localBackendUrl("/api/v1/company-news");
    url.search = new URLSearchParams({ exchange, symbol }).toString();
    const response = await fetch(url, {
      cache: "no-store", redirect: "error", signal: AbortSignal.any([request.signal, timeout]),
    });
    if (!response.ok) {
      const error = response.status === 401 ? "Connect to Kite to identify the company for news." :
        "The backend couldn’t load company news.";
      return Response.json({ error }, { status: response.status, headers });
    }
    return Response.json(await response.json(), { headers });
  } catch {
    const error = timeout.aborted ? "The company news request timed out." : "Couldn’t reach the company news endpoint.";
    return Response.json({ error }, { status: timeout.aborted ? 504 : 503, headers });
  }
}

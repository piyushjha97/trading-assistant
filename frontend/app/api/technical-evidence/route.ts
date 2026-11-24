import { localBackendUrl } from "../../../lib/backend";
import { intervals, symbolPattern } from "../../../lib/market";

function issue(status: number, error: string) {
  return Response.json({ error }, { status, headers: { "Cache-Control": "no-store" } });
}

export async function GET(request: Request) {
  const params = new URL(request.url).searchParams;
  const exchange = params.get("exchange");
  const symbol = params.get("symbol") ?? "";
  const interval = params.get("interval") ?? "";
  if ((exchange !== "NSE" && exchange !== "BSE") || !symbolPattern.test(symbol) || !Object.hasOwn(intervals, interval)) {
    return issue(400, "Choose a valid exchange, symbol, and interval.");
  }

  const timeout = AbortSignal.timeout(14_000);
  let response: Response;
  try {
    const url = localBackendUrl("/api/v1/technical-evidence");
    url.search = new URLSearchParams({ exchange, symbol, interval }).toString();
    response = await fetch(url, { cache: "no-store", redirect: "error", signal: AbortSignal.any([request.signal, timeout]) });
  } catch {
    return timeout.aborted ? issue(504, "The technical evidence request timed out.") :
      issue(503, "Technical evidence couldn’t reach the local backend.");
  }

  if (response.status === 401) return issue(401, "Connect to Kite to load technical evidence.");
  if (response.status === 403) return issue(403, "Check your Kite historical-data entitlement.");
  if (response.status === 404) return issue(404, "Kite couldn’t find this instrument on the selected exchange.");
  if (response.status === 429) return issue(429, "Kite’s request limit was reached. Try again shortly.");
  if (!response.ok) return issue(response.status, "The backend couldn’t calculate technical evidence.");

  try {
    return Response.json(await response.json(), { headers: { "Cache-Control": "no-store" } });
  } catch {
    return issue(502, "The backend returned unreadable technical evidence.");
  }
}

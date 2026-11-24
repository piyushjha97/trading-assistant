import { localBackendUrl } from "../../../lib/backend";

export async function GET(request: Request) {
  const input = new URL(request.url).searchParams;
  const q = input.get("q")?.trim() ?? "";
  const exchange = input.get("exchange");
  const headers = { "Cache-Control": "no-store" };
  if (q.length < 2 || q.length > 80) {
    return Response.json({ error: "Enter a search term between 2 and 80 characters." }, { status: 400, headers });
  }
  if (exchange !== null && exchange !== "NSE" && exchange !== "BSE") {
    return Response.json({ error: "Choose NSE or BSE." }, { status: 400, headers });
  }

  try {
    const url = localBackendUrl("/api/v1/instruments");
    url.searchParams.set("q", q);
    if (exchange) url.searchParams.set("exchange", exchange);
    const response = await fetch(url, {
      cache: "no-store", redirect: "error",
      signal: AbortSignal.any([request.signal, AbortSignal.timeout(24_000)]),
    });
    if (response.status === 401) {
      return Response.json({ error: "Connect to Kite to search instruments." }, { status: 401, headers });
    }
    if (!response.ok) {
      return Response.json({ error: "Kite instrument search is unavailable. Try again shortly." }, { status: response.status, headers });
    }
    return Response.json(await response.json(), { headers });
  } catch {
    return Response.json({ error: "Could not reach instrument search. Check the local backend and try again." }, { status: 503, headers });
  }
}

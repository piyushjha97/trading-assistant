import { localBackendUrl } from "./backend";

export async function paperBackend(request: Request, path: string, body?: string) {
  const headers = { "Cache-Control": "no-store" };
  const timeout = AbortSignal.timeout(45_000);
  try {
    const response = await fetch(localBackendUrl(path), {
      method: request.method,
      body,
      headers: body ? { "Content-Type": "application/json" } : undefined,
      cache: "no-store",
      redirect: "error",
      signal: AbortSignal.any([request.signal, timeout]),
    });
    const data = await response.json();
    if (response.ok) return Response.json(data, { headers });
    const error = response.status === 401 ? "Connect to Kite to use current market data."
      : typeof data.detail === "string" ? data.detail
      : data.detail?.message ?? "The backend couldn’t complete the paper-trading request.";
    return Response.json({ error }, { status: response.status, headers });
  } catch {
    return Response.json({
      error: timeout.aborted ? "The paper-trading request timed out." : "Couldn’t reach the paper-trading backend.",
    }, { status: timeout.aborted ? 504 : 503, headers });
  }
}

import { symbolPattern } from "../../../lib/market";
import { paperBackend } from "../../../lib/paper-backend";

export async function POST(request: Request) {
  const body = await request.json().catch(() => null);
  if ((body?.exchange !== "NSE" && body?.exchange !== "BSE") ||
      typeof body.symbol !== "string" || !symbolPattern.test(body.symbol)) {
    return Response.json({ error: "Choose a valid stock and exchange." }, { status: 400 });
  }
  return paperBackend(request, "/api/v1/analyses", JSON.stringify({
    exchange: body.exchange, symbol: body.symbol,
  }));
}

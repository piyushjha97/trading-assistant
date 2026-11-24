import { NextResponse, type NextRequest } from "next/server";
import { localBackendUrl } from "../../../../lib/backend";

export async function GET(request: NextRequest) {
  const params = request.nextUrl.searchParams;
  const requestToken = params.get("request_token");
  const expectedState = request.cookies.get("kite_login_state")?.value;
  let result = "retry";
  if (expectedState && params.get("state") === expectedState && params.get("status") === "success" &&
      requestToken && /^[A-Za-z0-9_-]{1,256}$/.test(requestToken)) {
    try {
      const response = await fetch(localBackendUrl("/api/v1/kite/session"), {
        method: "POST",
        headers: { "Content-Type": "application/json" },
        body: JSON.stringify({ request_token: requestToken }),
        cache: "no-store",
        redirect: "error",
        signal: AbortSignal.timeout(14_000),
      });
      if (response.ok) result = "connected";
    } catch {
      result = "unavailable";
    }
  }
  const response = new NextResponse(null, { status: 303, headers: {
    Location: `/?kite=${result}`,
    "Cache-Control": "no-store",
    "Referrer-Policy": "no-referrer",
  } });
  response.cookies.set("kite_login_state", "", { httpOnly: true, sameSite: "lax", path: "/api/kite", maxAge: 0 });
  return response;
}

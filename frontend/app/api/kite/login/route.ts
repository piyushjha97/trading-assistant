import { randomBytes } from "node:crypto";
import { NextResponse } from "next/server";
import { localBackendUrl } from "../../../../lib/backend";

export async function GET() {
  const state = randomBytes(32).toString("hex");
  try {
    const url = localBackendUrl("/api/v1/kite/login-url");
    url.searchParams.set("state", state);
    const response = await fetch(url, { cache: "no-store", redirect: "error", signal: AbortSignal.timeout(3000) });
    if (response.status === 503) return new Response(null, { status: 303, headers: { Location: "/?kite=setup" } });
    if (!response.ok) throw new Error("Login unavailable");
    const { url: loginUrl } = await response.json();
    const target = new URL(loginUrl);
    if (target.origin !== "https://kite.zerodha.com" || target.pathname !== "/connect/login") {
      throw new Error("Unexpected Kite login URL");
    }
    const redirect = NextResponse.redirect(target, 303);
    redirect.cookies.set("kite_login_state", state, { httpOnly: true, sameSite: "lax", path: "/api/kite", maxAge: 600 });
    redirect.headers.set("Cache-Control", "no-store");
    return redirect;
  } catch {
    return new Response(null, { status: 303, headers: { Location: "/?kite=unavailable" } });
  }
}

export function localBackendUrl(path: string) {
  const origin = new URL(process.env.TRADING_BACKEND_URL ?? "http://127.0.0.1:8000");
  if (!["http:", "https:"].includes(origin.protocol) ||
      !["localhost", "127.0.0.1", "[::1]"].includes(origin.hostname)) {
    throw new Error("The backend address must point to this machine.");
  }
  return new URL(path, origin);
}

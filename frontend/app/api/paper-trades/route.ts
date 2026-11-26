import { paperBackend } from "../../../lib/paper-backend";

export function GET(request: Request) {
  return paperBackend(request, "/api/v1/paper-trades");
}

export async function POST(request: Request) {
  const id = new URL(request.url).searchParams.get("id");
  if (!id || !/^[a-f0-9]{32}$/.test(id)) {
    return Response.json({ error: "Choose a valid paper trade." }, { status: 400 });
  }
  return paperBackend(request, `/api/v1/paper-trades/${id}/refresh`);
}

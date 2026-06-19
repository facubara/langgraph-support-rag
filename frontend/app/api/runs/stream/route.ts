import { backendFetch, UnauthorizedError } from "@/lib/backend";

// POST /api/runs/stream — proxy the backend SSE stream straight through to the browser.
export async function POST(request: Request) {
  const body = await request.text();
  try {
    const res = await backendFetch("/runs/stream", {
      method: "POST",
      body,
      headers: { "content-type": "application/json" },
    });
    if (!res.ok || !res.body) {
      const detail = await res.text();
      return new Response(detail || JSON.stringify({ detail: "stream failed" }), {
        status: res.status || 502,
        headers: { "content-type": res.headers.get("content-type") ?? "application/json" },
      });
    }
    // Pipe the upstream event-stream body directly to the client.
    return new Response(res.body, {
      status: 200,
      headers: {
        "content-type": "text/event-stream",
        "cache-control": "no-cache, no-transform",
        connection: "keep-alive",
        "x-accel-buffering": "no",
      },
    });
  } catch (err) {
    if (err instanceof UnauthorizedError) return Response.json({ detail: "unauthorized" }, { status: 401 });
    return Response.json({ detail: "backend unreachable" }, { status: 502 });
  }
}

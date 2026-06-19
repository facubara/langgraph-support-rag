import { forwardPost, proxyJson } from "@/lib/backend";

// GET /api/conversations — list recent threads.  POST — pre-create a thread.
export async function GET() {
  return proxyJson("/conversations");
}

export async function POST(request: Request) {
  return forwardPost(request, "/conversations");
}

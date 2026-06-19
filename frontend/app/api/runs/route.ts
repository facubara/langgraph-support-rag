import { forwardPost, proxyJson } from "@/lib/backend";

// GET /api/runs — list recent runs.  POST /api/runs — run one conversation turn.
export async function GET() {
  return proxyJson("/runs");
}

export async function POST(request: Request) {
  return forwardPost(request, "/runs");
}

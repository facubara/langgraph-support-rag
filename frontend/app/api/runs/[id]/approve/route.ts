import { proxyJson } from "@/lib/backend";

// POST /api/runs/[id]/approve — HITL: execute the risky action the run is awaiting.
export async function POST(_req: Request, ctx: { params: Promise<{ id: string }> }) {
  const { id } = await ctx.params;
  return proxyJson(`/runs/${encodeURIComponent(id)}/approve`, { method: "POST" });
}

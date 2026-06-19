import { proxyJson } from "@/lib/backend";

// POST /api/runs/[id]/reject — HITL: reject the proposed risky action.
export async function POST(_req: Request, ctx: { params: Promise<{ id: string }> }) {
  const { id } = await ctx.params;
  return proxyJson(`/runs/${encodeURIComponent(id)}/reject`, { method: "POST" });
}

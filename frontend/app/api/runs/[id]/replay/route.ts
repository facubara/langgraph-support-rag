import { proxyJson } from "@/lib/backend";

// POST /api/runs/[id]/replay — deterministically replay a run and diff vs. the original.
export async function POST(_req: Request, ctx: { params: Promise<{ id: string }> }) {
  const { id } = await ctx.params;
  return proxyJson(`/runs/${encodeURIComponent(id)}/replay`, { method: "POST" });
}

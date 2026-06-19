import { proxyJson } from "@/lib/backend";

// GET /api/conversations/[id] — a thread and its ordered turns.
export async function GET(_req: Request, ctx: { params: Promise<{ id: string }> }) {
  const { id } = await ctx.params;
  return proxyJson(`/conversations/${encodeURIComponent(id)}`);
}

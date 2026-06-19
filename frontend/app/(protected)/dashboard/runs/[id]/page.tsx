import Link from "next/link";
import { notFound } from "next/navigation";
import { ArrowLeft } from "lucide-react";
import { getJson } from "@/lib/backend";
import { StatusBadge } from "@/components/dashboard/status-badge";
import { TraceTimeline, type Step } from "@/components/dashboard/trace-timeline";
import { ReplayWidget } from "@/components/dashboard/replay-widget";

type RunDetail = {
  run: {
    id: string;
    created_at: number;
    user_message: string;
    intent: string | null;
    final_response: string | null;
    status: string | null;
    conversation_id: string | null;
    replay_of: string | null;
  };
  steps: Step[];
};

export default async function RunDetailPage(props: { params: Promise<{ id: string }> }) {
  const { id } = await props.params;

  let data: RunDetail;
  try {
    data = await getJson<RunDetail>(`/runs/${id}`);
  } catch (err) {
    if ((err as { status?: number }).status === 404) notFound();
    throw err;
  }
  const { run, steps } = data;

  return (
    <div>
      <Link href="/dashboard" className="inline-flex items-center gap-1.5 text-sm text-muted-foreground hover:text-foreground">
        <ArrowLeft className="size-4" /> Back to runs
      </Link>

      <div className="mt-4 flex flex-wrap items-center gap-3">
        <h1 className="text-xl font-semibold tracking-tight">Run</h1>
        <code className="rounded bg-muted px-1.5 py-0.5 text-sm">{run.id}</code>
        <StatusBadge status={run.status} />
        {run.replay_of && (
          <Link href={`/dashboard/runs/${run.replay_of}`} className="text-xs text-muted-foreground hover:underline">
            ↩ replay of {run.replay_of}
          </Link>
        )}
      </div>

      <div className="mt-5 grid gap-5 lg:grid-cols-[1fr_300px]">
        <div className="space-y-5">
          <section className="rounded-[var(--radius-lg)] border bg-card p-4">
            <h2 className="text-xs font-semibold uppercase tracking-wide text-muted-foreground">Conversation</h2>
            <p className="mt-2 text-sm"><span className="text-muted-foreground">User:</span> {run.user_message}</p>
            <p className="mt-2 whitespace-pre-wrap text-sm">
              <span className="text-muted-foreground">Assistant:</span> {run.final_response ?? "—"}
            </p>
            <p className="mt-2 text-xs text-muted-foreground">Intent: {run.intent ?? "—"}</p>
          </section>

          <section>
            <h2 className="mb-2 text-xs font-semibold uppercase tracking-wide text-muted-foreground">Step trace</h2>
            <TraceTimeline steps={steps} />
          </section>
        </div>

        <div className="lg:sticky lg:top-20 lg:self-start">
          <ReplayWidget runId={run.id} />
        </div>
      </div>
    </div>
  );
}

import { cn } from "@/lib/utils";

export type Step = {
  step_index: number;
  step_type: string;
  name: string | null;
  input: unknown;
  output: unknown;
  latency_ms: number | null;
  cost_usd: number | null;
  error: string | null;
};

const TYPE_COLOR: Record<string, string> = {
  router: "bg-accent",
  agent: "bg-purple-500",
  tool: "bg-success",
  llm: "bg-warning",
  approval: "bg-danger",
};

function fmtJson(v: unknown) {
  if (v == null) return "—";
  return JSON.stringify(v, null, 2);
}

export function TraceTimeline({ steps }: { steps: Step[] }) {
  const totalLatency = steps.reduce((a, s) => a + (s.latency_ms ?? 0), 0);
  const totalCost = steps.reduce((a, s) => a + (s.cost_usd ?? 0), 0);

  return (
    <div>
      <div className="mb-3 flex gap-4 text-xs text-muted-foreground">
        <span>{steps.length} steps</span>
        <span>{totalLatency.toFixed(0)} ms total</span>
        <span>${totalCost.toFixed(4)}</span>
      </div>
      <ol className="space-y-2">
        {steps.map((s) => (
          <li key={s.step_index} className="relative rounded-[var(--radius-md)] border bg-card p-3">
            <div className="flex items-center gap-2">
              <span className={cn("size-2 rounded-full", TYPE_COLOR[s.step_type] ?? "bg-muted-foreground")} />
              <span className="text-xs font-medium uppercase tracking-wide text-muted-foreground">{s.step_type}</span>
              <span className="font-mono text-sm">{s.name}</span>
              <span className="ml-auto text-xs text-muted-foreground">
                {s.latency_ms != null ? `${s.latency_ms.toFixed(0)} ms` : ""}
                {s.cost_usd ? ` · $${s.cost_usd.toFixed(4)}` : ""}
              </span>
            </div>
            {s.error && <p className="mt-2 text-sm text-danger">{s.error}</p>}
            {(s.input != null || s.output != null) && (
              <div className="mt-2 grid gap-2 md:grid-cols-2">
                {s.input != null && (
                  <details className="rounded-[var(--radius-sm)] border bg-background/60">
                    <summary className="cursor-pointer px-2.5 py-1.5 text-xs font-medium text-muted-foreground">input</summary>
                    <pre className="overflow-x-auto px-2.5 pb-2.5 text-xs">{fmtJson(s.input)}</pre>
                  </details>
                )}
                {s.output != null && (
                  <details className="rounded-[var(--radius-sm)] border bg-background/60">
                    <summary className="cursor-pointer px-2.5 py-1.5 text-xs font-medium text-muted-foreground">output</summary>
                    <pre className="overflow-x-auto px-2.5 pb-2.5 text-xs">{fmtJson(s.output)}</pre>
                  </details>
                )}
              </div>
            )}
          </li>
        ))}
      </ol>
    </div>
  );
}

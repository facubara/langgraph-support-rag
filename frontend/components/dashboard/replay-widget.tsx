"use client";

import { useState } from "react";
import { CheckCircle2, History, Loader2, XCircle } from "lucide-react";

type Comparison = { match: boolean; diffs: { field: string; original: unknown; replay: unknown }[] };

export function ReplayWidget({ runId }: { runId: string }) {
  const [state, setState] = useState<"idle" | "running" | "done" | "error">("idle");
  const [result, setResult] = useState<Comparison | null>(null);

  async function replay() {
    setState("running");
    try {
      const res = await fetch(`/api/runs/${runId}/replay`, { method: "POST" });
      const data = await res.json();
      setResult(data.comparison ?? null);
      setState("done");
    } catch {
      setState("error");
    }
  }

  return (
    <div className="rounded-[var(--radius-lg)] border bg-card p-4">
      <h3 className="text-sm font-semibold">Deterministic replay</h3>
      <p className="mt-1 text-xs text-muted-foreground">
        Re-runs the graph with this run&apos;s recorded model outputs and diffs the result.
      </p>
      <button
        onClick={replay}
        disabled={state === "running"}
        className="mt-3 inline-flex items-center gap-2 rounded-[var(--radius-md)] bg-primary px-3 py-1.5 text-sm font-medium text-primary-foreground transition hover:opacity-90 disabled:opacity-60"
      >
        {state === "running" ? <Loader2 className="size-4 animate-spin" /> : <History className="size-4" />}
        Replay this run
      </button>

      {state === "done" && result && (
        <div className="mt-3">
          {result.match ? (
            <p className="inline-flex items-center gap-1.5 text-sm font-medium text-success">
              <CheckCircle2 className="size-4" /> Match — reproduced exactly
            </p>
          ) : (
            <div className="text-sm">
              <p className="inline-flex items-center gap-1.5 font-medium text-warning">
                <XCircle className="size-4" /> Diverged on {result.diffs.length} field(s)
              </p>
              <pre className="mt-2 overflow-x-auto rounded-[var(--radius-sm)] border bg-background/60 p-2.5 text-xs">
                {JSON.stringify(result.diffs, null, 2)}
              </pre>
            </div>
          )}
        </div>
      )}
      {state === "error" && <p className="mt-3 text-sm text-danger">Replay failed.</p>}
    </div>
  );
}

"use client";

import { useMemo, useState } from "react";
import Link from "next/link";
import { Search } from "lucide-react";
import { StatusBadge } from "./status-badge";
import { cn } from "@/lib/utils";

export type RunRow = {
  id: string;
  created_at: number;
  user_message: string;
  intent: string | null;
  status: string | null;
  replay_of: string | null;
  conversation_id: string | null;
};

const STATUSES = ["all", "completed", "awaiting_approval", "rejected", "error"] as const;

function fmtTime(epoch: number) {
  return new Date(epoch * 1000).toLocaleString(undefined, { dateStyle: "medium", timeStyle: "short" });
}

export function RunsTable({ runs }: { runs: RunRow[] }) {
  const [q, setQ] = useState("");
  const [status, setStatus] = useState<(typeof STATUSES)[number]>("all");

  const filtered = useMemo(() => {
    const needle = q.trim().toLowerCase();
    return runs.filter(
      (r) =>
        (status === "all" || r.status === status) &&
        (!needle ||
          r.user_message.toLowerCase().includes(needle) ||
          (r.intent ?? "").toLowerCase().includes(needle) ||
          r.id.includes(needle)),
    );
  }, [runs, q, status]);

  return (
    <div>
      <div className="flex flex-col gap-3 sm:flex-row sm:items-center sm:justify-between">
        <div className="relative max-w-sm flex-1">
          <Search className="pointer-events-none absolute left-3 top-1/2 size-4 -translate-y-1/2 text-muted-foreground" />
          <input
            value={q}
            onChange={(e) => setQ(e.target.value)}
            placeholder="Search message, intent, or id…"
            className="w-full rounded-[var(--radius-md)] border bg-card py-2 pl-9 pr-3 text-sm outline-none focus-visible:ring-2 focus-visible:ring-ring"
          />
        </div>
        <div className="flex flex-wrap gap-1.5">
          {STATUSES.map((s) => (
            <button
              key={s}
              onClick={() => setStatus(s)}
              className={cn(
                "rounded-full border px-3 py-1 text-xs capitalize transition",
                s === status ? "border-accent/60 bg-accent/5 font-medium text-foreground" : "text-muted-foreground hover:text-foreground",
              )}
            >
              {s.replace(/_/g, " ")}
            </button>
          ))}
        </div>
      </div>

      <div className="mt-4 overflow-hidden rounded-[var(--radius-lg)] border">
        <table className="w-full text-sm">
          <thead className="bg-muted/50 text-left text-xs uppercase tracking-wide text-muted-foreground">
            <tr>
              <th className="px-4 py-2.5 font-medium">Time</th>
              <th className="px-4 py-2.5 font-medium">Message</th>
              <th className="px-4 py-2.5 font-medium">Intent</th>
              <th className="px-4 py-2.5 font-medium">Status</th>
            </tr>
          </thead>
          <tbody>
            {filtered.length === 0 ? (
              <tr>
                <td colSpan={4} className="px-4 py-10 text-center text-muted-foreground">
                  No runs match.
                </td>
              </tr>
            ) : (
              filtered.map((r) => (
                <tr key={r.id} className="border-t transition hover:bg-muted/40">
                  <td className="whitespace-nowrap px-4 py-2.5 text-muted-foreground">{fmtTime(r.created_at)}</td>
                  <td className="px-4 py-2.5">
                    <Link href={`/dashboard/runs/${r.id}`} className="font-medium hover:underline">
                      {r.user_message.length > 64 ? r.user_message.slice(0, 64) + "…" : r.user_message}
                    </Link>
                    {r.replay_of && <span className="ml-2 text-xs text-muted-foreground">↩ replay</span>}
                  </td>
                  <td className="px-4 py-2.5 text-muted-foreground">{r.intent ?? "—"}</td>
                  <td className="px-4 py-2.5">
                    <StatusBadge status={r.status} />
                  </td>
                </tr>
              ))
            )}
          </tbody>
        </table>
      </div>
      <p className="mt-2 text-xs text-muted-foreground">
        {filtered.length} of {runs.length} runs
      </p>
    </div>
  );
}

import Link from "next/link";
import { Users } from "lucide-react";
import { getJson } from "@/lib/backend";
import { RunsTable, type RunRow } from "@/components/dashboard/runs-table";

export default async function DashboardPage() {
  let runs: RunRow[] = [];
  let error = false;
  try {
    runs = await getJson<RunRow[]>("/runs");
  } catch {
    error = true;
  }

  return (
    <div>
      <div className="flex items-center justify-between">
        <div>
          <h1 className="text-2xl font-semibold tracking-tight">Observability</h1>
          <p className="mt-1 text-sm text-muted-foreground">
            Every run is traced end to end. Open one to inspect its steps and replay it.
          </p>
        </div>
        <Link
          href="/dashboard/admin"
          className="inline-flex items-center gap-1.5 rounded-[var(--radius-md)] border bg-card px-3 py-2 text-sm transition hover:shadow-sm"
        >
          <Users className="size-4" /> Sign-ins
        </Link>
      </div>

      <div className="mt-6">
        {error ? (
          <p className="rounded-[var(--radius-lg)] border bg-card p-6 text-sm text-muted-foreground">
            Could not reach the backend. Is it running?
          </p>
        ) : (
          <RunsTable runs={runs} />
        )}
      </div>
    </div>
  );
}

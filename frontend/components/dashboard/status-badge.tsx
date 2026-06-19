import { cn } from "@/lib/utils";

const STYLES: Record<string, string> = {
  completed: "bg-success/15 text-success",
  awaiting_approval: "bg-warning/15 text-warning",
  rejected: "bg-danger/15 text-danger",
  error: "bg-danger/15 text-danger",
  created: "bg-muted text-muted-foreground",
};

export function StatusBadge({ status }: { status?: string | null }) {
  const s = status ?? "created";
  return (
    <span
      className={cn(
        "inline-flex items-center rounded-full px-2 py-0.5 text-xs font-medium capitalize",
        STYLES[s] ?? "bg-muted text-muted-foreground",
      )}
    >
      {s.replace(/_/g, " ")}
    </span>
  );
}

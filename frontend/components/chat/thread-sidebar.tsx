"use client";

import { MessageSquarePlus, MessagesSquare } from "lucide-react";
import type { ThreadSummary } from "@/hooks/use-chat";
import { cn } from "@/lib/utils";

export function ThreadSidebar({
  threads,
  activeId,
  onNew,
  onSelect,
}: {
  threads: ThreadSummary[];
  activeId: string | null;
  onNew: () => void;
  onSelect: (id: string) => void;
}) {
  return (
    <div className="flex h-full flex-col gap-3">
      <button
        onClick={onNew}
        className="inline-flex items-center justify-center gap-2 rounded-[var(--radius-md)] border bg-card px-3 py-2 text-sm font-medium transition hover:shadow-sm"
      >
        <MessageSquarePlus className="size-4" /> New chat
      </button>

      <div className="min-h-0 flex-1 overflow-y-auto">
        <p className="px-1 pb-1 text-xs font-semibold uppercase tracking-wide text-muted-foreground">
          Conversations
        </p>
        {threads.length === 0 ? (
          <p className="px-1 py-2 text-xs text-muted-foreground">No conversations yet.</p>
        ) : (
          <ul className="space-y-0.5">
            {threads.map((t) => (
              <li key={t.id}>
                <button
                  onClick={() => onSelect(t.id)}
                  className={cn(
                    "flex w-full items-center gap-2 rounded-[var(--radius-md)] px-2.5 py-2 text-left text-sm transition",
                    t.id === activeId ? "bg-muted font-medium" : "text-muted-foreground hover:bg-muted/60",
                  )}
                >
                  <MessagesSquare className="size-4 shrink-0" />
                  <span className="truncate">{t.title || `Conversation ${t.id.slice(0, 6)}`}</span>
                </button>
              </li>
            ))}
          </ul>
        )}
      </div>
    </div>
  );
}

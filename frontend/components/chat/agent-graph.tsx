"use client";

import { motion } from "framer-motion";
import { Check, Compass, Library, MessageSquare, ShieldCheck, type LucideIcon } from "lucide-react";
import type { GraphState, NodeKey, NodeStatus } from "@/lib/types";
import { cn } from "@/lib/utils";

const NODES: { key: NodeKey; label: string; desc: string; icon: LucideIcon }[] = [
  { key: "router", label: "Router", desc: "Classifies intent", icon: Compass },
  { key: "retrieval", label: "Retrieval & Tools", desc: "RAG + business tools", icon: Library },
  { key: "policy", label: "Policy & Safety", desc: "Eligibility + HITL gate", icon: ShieldCheck },
  { key: "response", label: "Response", desc: "Grounded reply", icon: MessageSquare },
];

const IDLE: GraphState = { router: "idle", retrieval: "idle", policy: "idle", response: "idle" };

function StatusDot({ status }: { status: NodeStatus }) {
  if (status === "done")
    return (
      <span className="grid size-5 place-items-center rounded-full bg-success/15 text-success">
        <Check className="size-3.5" />
      </span>
    );
  if (status === "active")
    return (
      <motion.span
        className="size-2.5 rounded-full bg-accent"
        animate={{ scale: [1, 1.5, 1], opacity: [1, 0.5, 1] }}
        transition={{ duration: 1, repeat: Infinity }}
      />
    );
  if (status === "skipped")
    return <span className="text-[10px] font-medium uppercase tracking-wide text-muted-foreground">skipped</span>;
  return <span className="size-2.5 rounded-full border" />;
}

export function AgentGraph({ graph }: { graph?: GraphState }) {
  const g = graph ?? IDLE;

  return (
    <div className="rounded-[var(--radius-lg)] border bg-card p-4">
      <h3 className="text-xs font-semibold uppercase tracking-wide text-muted-foreground">Agent graph</h3>
      <ol className="mt-3 space-y-1">
        {NODES.map(({ key, label, desc, icon: Icon }, i) => {
          const status = g[key];
          const active = status === "active";
          const done = status === "done";
          const dim = status === "idle" || status === "skipped";
          return (
            <li key={key}>
              <div
                className={cn(
                  "flex items-center gap-3 rounded-[var(--radius-md)] border px-3 py-2.5 transition",
                  active && "border-accent/60 bg-accent/5 shadow-sm",
                  done && "border-success/30",
                  dim && "opacity-55",
                )}
              >
                <span
                  className={cn(
                    "grid size-8 shrink-0 place-items-center rounded-[var(--radius-md)] bg-muted",
                    active && "text-accent",
                    done && "text-success",
                  )}
                >
                  <Icon className="size-4" />
                </span>
                <div className="min-w-0 flex-1">
                  <p className="truncate text-sm font-medium">{label}</p>
                  <p className="truncate text-xs text-muted-foreground">{desc}</p>
                </div>
                <StatusDot status={status} />
              </div>
              {i < NODES.length - 1 && (
                <div className="ml-7 h-3 w-px bg-border" aria-hidden />
              )}
            </li>
          );
        })}
      </ol>
    </div>
  );
}

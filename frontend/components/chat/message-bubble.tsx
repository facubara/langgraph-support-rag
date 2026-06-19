"use client";

import { useState } from "react";
import { motion } from "framer-motion";
import { AlertTriangle, Check, ChevronDown, FileText, Sparkles, Wrench, X } from "lucide-react";
import type { ChatMessage } from "@/lib/types";
import { cn } from "@/lib/utils";

function prettyTool(name: string) {
  return name.replace(/_/g, " ");
}

function Sources({ message }: { message: ChatMessage }) {
  const [open, setOpen] = useState(false);
  const cites = message.citations ?? [];
  if (!cites.length) return null;
  return (
    <div className="mt-3 rounded-[var(--radius-md)] border bg-background/60">
      <button
        onClick={() => setOpen((o) => !o)}
        className="flex w-full items-center gap-2 px-3 py-2 text-xs font-medium text-muted-foreground hover:text-foreground"
      >
        <FileText className="size-3.5" />
        {cites.length} grounded source{cites.length > 1 ? "s" : ""}
        <ChevronDown className={cn("ml-auto size-3.5 transition", open && "rotate-180")} />
      </button>
      {open && (
        <ul className="space-y-1 border-t px-3 py-2">
          {cites.map((c, i) => (
            <li key={i} className="flex items-center justify-between gap-3 text-xs">
              <span className="truncate capitalize">{c.title}</span>
              <span className="shrink-0 font-mono text-muted-foreground">{c.score.toFixed(3)}</span>
            </li>
          ))}
        </ul>
      )}
    </div>
  );
}

function HitlCard({ message, onDecide }: { message: ChatMessage; onDecide: Decide }) {
  const action = message.pending?.action ?? "this action";
  return (
    <div className="mt-3 rounded-[var(--radius-md)] border border-warning/40 bg-warning/5 p-3">
      <div className="flex items-center gap-2 text-sm font-medium text-warning">
        <AlertTriangle className="size-4" />
        Human approval required
      </div>
      <p className="mt-1 text-sm text-muted-foreground">
        The assistant proposes to run <span className="font-mono">{prettyTool(action)}</span>. Nothing
        happens until you approve.
      </p>
      <div className="mt-3 flex gap-2">
        <button
          onClick={() => message.runId && onDecide(message.runId, "approve")}
          className="inline-flex items-center gap-1.5 rounded-[var(--radius-md)] bg-success px-3 py-1.5 text-sm font-medium text-white transition hover:opacity-90"
        >
          <Check className="size-4" /> Approve
        </button>
        <button
          onClick={() => message.runId && onDecide(message.runId, "reject")}
          className="inline-flex items-center gap-1.5 rounded-[var(--radius-md)] border bg-card px-3 py-1.5 text-sm font-medium transition hover:shadow-sm"
        >
          <X className="size-4" /> Reject
        </button>
      </div>
    </div>
  );
}

type Decide = (runId: string, action: "approve" | "reject") => void;

export function MessageBubble({ message, onDecide }: { message: ChatMessage; onDecide: Decide }) {
  if (message.role === "user") {
    return (
      <div className="flex justify-end">
        <div className="max-w-[80%] rounded-[var(--radius-lg)] rounded-br-sm bg-primary px-4 py-2.5 text-sm text-primary-foreground">
          {message.content}
        </div>
      </div>
    );
  }

  const decided = message.decision;
  return (
    <motion.div initial={{ opacity: 0, y: 6 }} animate={{ opacity: 1, y: 0 }} className="flex gap-3">
      <span className="mt-0.5 grid size-8 shrink-0 place-items-center rounded-full bg-muted text-primary">
        <Sparkles className="size-4" />
      </span>
      <div className="min-w-0 max-w-[85%]">
        <div className="rounded-[var(--radius-lg)] rounded-tl-sm border bg-card px-4 py-3 text-sm leading-relaxed">
          {message.content ? (
            <span className="whitespace-pre-wrap">{message.content}</span>
          ) : (
            <span className="text-muted-foreground">Thinking…</span>
          )}
          {message.streaming && message.content && (
            <motion.span
              className="ml-0.5 inline-block h-4 w-1.5 translate-y-0.5 bg-accent"
              animate={{ opacity: [1, 0] }}
              transition={{ duration: 0.7, repeat: Infinity }}
            />
          )}

          {message.tools && message.tools.length > 0 && (
            <div className="mt-3 flex flex-wrap gap-1.5">
              {message.tools.map((t) => (
                <span
                  key={t}
                  className="inline-flex items-center gap-1 rounded-full border bg-background/60 px-2 py-0.5 text-xs text-muted-foreground"
                >
                  <Wrench className="size-3" /> {prettyTool(t)}
                </span>
              ))}
            </div>
          )}

          <Sources message={message} />

          {message.pending && !decided && <HitlCard message={message} onDecide={onDecide} />}

          {decided && (
            <p
              className={cn(
                "mt-3 inline-flex items-center gap-1.5 rounded-full px-2.5 py-1 text-xs font-medium",
                decided === "approve" ? "bg-success/15 text-success" : "bg-danger/15 text-danger",
              )}
            >
              {decided === "approve" ? <Check className="size-3.5" /> : <X className="size-3.5" />}
              {decided === "approve" ? "Approved & executed" : "Rejected"}
            </p>
          )}

          {message.error && (
            <p className="mt-3 inline-flex items-center gap-1.5 rounded-full bg-danger/15 px-2.5 py-1 text-xs font-medium text-danger">
              <AlertTriangle className="size-3.5" /> {message.error}
            </p>
          )}
        </div>
      </div>
    </motion.div>
  );
}

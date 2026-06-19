"use client";

import { useEffect, useMemo, useRef, useState } from "react";
import { Sparkles, User2 } from "lucide-react";
import { useChat } from "@/hooks/use-chat";
import { PERSONAS, SUGGESTIONS, type ChatMessage } from "@/lib/types";
import { cn } from "@/lib/utils";
import { AgentGraph } from "./agent-graph";
import { Composer } from "./composer";
import { MessageBubble } from "./message-bubble";
import { ThreadSidebar } from "./thread-sidebar";

function lastAssistant(messages: ChatMessage[]): ChatMessage | undefined {
  for (let i = messages.length - 1; i >= 0; i--) if (messages[i].role === "assistant") return messages[i];
  return undefined;
}

function PersonaBar({ persona, setPersona }: { persona: string; setPersona: (id: string) => void }) {
  return (
    <div className="flex items-center gap-2 overflow-x-auto border-b px-4 py-2.5">
      <span className="shrink-0 text-xs font-medium text-muted-foreground">Acting as</span>
      <div className="flex gap-1.5">
        {PERSONAS.map((p) => (
          <button
            key={p.id}
            onClick={() => setPersona(p.id)}
            title={p.blurb}
            className={cn(
              "shrink-0 rounded-full border px-3 py-1 text-xs transition",
              p.id === persona ? "border-primary/60 bg-primary/5 font-medium text-foreground" : "text-muted-foreground hover:text-foreground",
            )}
          >
            {p.name} · {p.plan}
          </button>
        ))}
      </div>
    </div>
  );
}

function RunDetails({ message }: { message?: ChatMessage }) {
  if (!message) return null;
  return (
    <div className="rounded-[var(--radius-lg)] border bg-card p-4 text-sm">
      <h3 className="text-xs font-semibold uppercase tracking-wide text-muted-foreground">Run details</h3>
      <dl className="mt-3 space-y-2">
        <Row label="Intent" value={message.intent ?? "—"} />
        <Row label="Status" value={message.status ?? (message.streaming ? "running…" : "—")} />
        <Row label="Tools" value={message.tools?.length ? String(message.tools.length) : "0"} />
        <Row label="Sources" value={message.citations?.length ? String(message.citations.length) : "0"} />
        {message.runId && <Row label="Run" value={message.runId.slice(0, 10)} mono />}
      </dl>
    </div>
  );
}

function Row({ label, value, mono }: { label: string; value: string; mono?: boolean }) {
  return (
    <div className="flex items-center justify-between gap-3">
      <dt className="text-muted-foreground">{label}</dt>
      <dd className={cn("truncate capitalize", mono && "font-mono normal-case")}>{value}</dd>
    </div>
  );
}

export function ChatApp() {
  const { messages, threads, conversationId, busy, send, decide, newChat, loadThread } = useChat();
  const [persona, setPersona] = useState(PERSONAS[0].id);
  const scrollRef = useRef<HTMLDivElement>(null);

  useEffect(() => {
    scrollRef.current?.scrollTo({ top: scrollRef.current.scrollHeight, behavior: "smooth" });
  }, [messages]);

  const focus = useMemo(() => lastAssistant(messages), [messages]);
  const empty = messages.length === 0;

  return (
    <div className="flex min-h-0 flex-1">
      <aside className="hidden w-64 shrink-0 border-r p-3 lg:flex">
        <ThreadSidebar threads={threads} activeId={conversationId} onNew={newChat} onSelect={loadThread} />
      </aside>

      <section className="flex min-w-0 flex-1 flex-col">
        <PersonaBar persona={persona} setPersona={setPersona} />

        <div ref={scrollRef} className="min-h-0 flex-1 overflow-y-auto">
          <div className="mx-auto max-w-3xl px-4 py-6">
            {empty ? (
              <div className="mx-auto mt-10 max-w-xl text-center">
                <div className="mx-auto grid size-12 place-items-center rounded-[var(--radius-md)] bg-muted text-primary">
                  <Sparkles className="size-6" />
                </div>
                <h2 className="mt-4 text-lg font-semibold">How can I help with your account?</h2>
                <p className="mt-1 text-sm text-muted-foreground">
                  Ask a billing question and watch the multi-agent graph work in real time.
                </p>
                <div className="mt-6 grid gap-2 sm:grid-cols-2">
                  {SUGGESTIONS.map((s) => (
                    <button
                      key={s}
                      onClick={() => send(s, persona)}
                      className="rounded-[var(--radius-md)] border bg-card px-3 py-2.5 text-left text-sm transition hover:-translate-y-0.5 hover:shadow-sm"
                    >
                      {s}
                    </button>
                  ))}
                </div>
              </div>
            ) : (
              <div className="space-y-5">
                {messages.map((m) => (
                  <MessageBubble key={m.id} message={m} onDecide={decide} />
                ))}
              </div>
            )}
          </div>
        </div>

        <div className="border-t bg-background/80 p-4 backdrop-blur">
          <div className="mx-auto max-w-3xl">
            <Composer onSend={(text) => send(text, persona)} busy={busy} />
            <p className="mt-2 text-center text-xs text-muted-foreground">
              Demo on a mock model · acting as {PERSONAS.find((p) => p.id === persona)?.name}
            </p>
          </div>
        </div>
      </section>

      <aside className="hidden w-80 shrink-0 flex-col gap-4 overflow-y-auto border-l p-4 xl:flex">
        <AgentGraph graph={focus?.graph} />
        <RunDetails message={focus} />
        <div className="rounded-[var(--radius-lg)] border bg-card p-4">
          <div className="flex items-center gap-2 text-xs font-semibold uppercase tracking-wide text-muted-foreground">
            <User2 className="size-3.5" /> Personas
          </div>
          <ul className="mt-3 space-y-2 text-sm">
            {PERSONAS.map((p) => (
              <li key={p.id} className={cn(p.id === persona && "font-medium")}>
                <span className="capitalize">{p.name}</span>
                <span className="block text-xs text-muted-foreground">{p.blurb}</span>
              </li>
            ))}
          </ul>
        </div>
      </aside>
    </div>
  );
}

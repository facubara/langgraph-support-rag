"use client";

import { useCallback, useEffect, useRef, useState } from "react";
import { streamSSE } from "@/lib/sse";
import type { ChatMessage, GraphState, NodeStatus } from "@/lib/types";

const FRESH_GRAPH: GraphState = { router: "idle", retrieval: "idle", policy: "idle", response: "idle" };

const uid = () => Math.random().toString(36).slice(2, 10);

function settle(status: NodeStatus): NodeStatus {
  return status === "active" ? "done" : status;
}

export type ThreadSummary = { id: string; title: string | null; updated_at: number };

export function useChat() {
  const [messages, setMessages] = useState<ChatMessage[]>([]);
  const [conversationId, setConversationId] = useState<string | null>(null);
  const [threads, setThreads] = useState<ThreadSummary[]>([]);
  const [busy, setBusy] = useState(false);
  const assistantId = useRef<string | null>(null);

  const refreshThreads = useCallback(async () => {
    try {
      const res = await fetch("/api/conversations");
      if (res.ok) setThreads(await res.json());
    } catch {
      /* best-effort */
    }
  }, []);

  useEffect(() => {
    refreshThreads();
  }, [refreshThreads]);

  const patch = useCallback(
    (fn: (m: ChatMessage) => ChatMessage) => {
      setMessages((prev) => prev.map((m) => (m.id === assistantId.current ? fn(m) : m)));
    },
    [],
  );

  const send = useCallback(
    async (text: string, customerId: string | null) => {
      if (!text.trim() || busy) return;
      setBusy(true);

      const aId = uid();
      assistantId.current = aId;
      setMessages((p) => [
        ...p,
        { id: uid(), role: "user", content: text },
        { id: aId, role: "assistant", content: "", streaming: true, graph: { ...FRESH_GRAPH, router: "active" } },
      ]);

      try {
        const res = await fetch("/api/runs/stream", {
          method: "POST",
          headers: { "content-type": "application/json" },
          body: JSON.stringify({ message: text, customer_id: customerId, conversation_id: conversationId }),
        });
        if (!res.ok || !res.body) throw new Error(`Stream failed (${res.status})`);

        for await (const ev of streamSSE(res)) {
          if (ev.type === "run_started") {
            if (ev.data.conversation_id) setConversationId(ev.data.conversation_id);
            patch((m) => ({ ...m, runId: ev.data.run_id }));
          } else if (ev.type === "router") {
            patch((m) => ({ ...m, intent: ev.data.intent, graph: { ...m.graph!, router: "done", retrieval: "active" } }));
          } else if (ev.type === "rag") {
            patch((m) => ({ ...m, citations: ev.data.included, excluded: ev.data.excluded, tools: ev.data.tools }));
          } else if (ev.type === "tool") {
            patch((m) => ({ ...m, graph: { ...m.graph!, retrieval: "active" } }));
          } else if (ev.type === "policy") {
            patch((m) => ({ ...m, graph: { ...m.graph!, retrieval: "done", policy: "done", response: "active" } }));
          } else if (ev.type === "token") {
            patch((m) => {
              const g = { ...m.graph! };
              if (g.policy !== "done") {
                // refusal / non-billing path skips retrieval + policy
                g.retrieval = g.retrieval === "done" ? "done" : "skipped";
                g.policy = "skipped";
              }
              g.response = "active";
              return { ...m, content: m.content + ev.data.text, graph: g };
            });
          } else if (ev.type === "done") {
            patch((m) => ({
              ...m,
              streaming: false,
              content: ev.data.response ?? m.content,
              status: ev.data.status,
              pending: ev.data.pending_action,
              intent: ev.data.intent,
              tools: ev.data.tools,
              graph: {
                router: settle(m.graph!.router),
                retrieval: settle(m.graph!.retrieval),
                policy: settle(m.graph!.policy),
                response: "done",
              },
            }));
          } else if (ev.type === "error") {
            patch((m) => ({ ...m, streaming: false, error: ev.data.detail }));
          }
        }
      } catch (err) {
        patch((m) => ({ ...m, streaming: false, error: String(err) }));
      } finally {
        setBusy(false);
        assistantId.current = null;
        refreshThreads();
      }
    },
    [busy, conversationId, patch, refreshThreads],
  );

  const decide = useCallback(async (runId: string, action: "approve" | "reject") => {
    setMessages((prev) =>
      prev.map((m) => (m.runId === runId ? { ...m, pending: null, decision: action } : m)),
    );
    try {
      const res = await fetch(`/api/runs/${runId}/${action}`, { method: "POST" });
      const data = await res.json().catch(() => ({}));
      setMessages((prev) =>
        prev.map((m) =>
          m.runId === runId
            ? { ...m, status: data.status ?? (action === "approve" ? "completed" : "rejected") }
            : m,
        ),
      );
    } catch {
      /* keep optimistic state */
    }
  }, []);

  const newChat = useCallback(() => {
    setMessages([]);
    setConversationId(null);
    assistantId.current = null;
  }, []);

  const loadThread = useCallback(async (id: string) => {
    try {
      const res = await fetch(`/api/conversations/${id}`);
      if (!res.ok) return;
      const data = await res.json();
      const msgs: ChatMessage[] = [];
      for (const turn of data.turns ?? []) {
        msgs.push({ id: uid(), role: "user", content: turn.user_message });
        msgs.push({
          id: uid(),
          role: "assistant",
          content: turn.final_response ?? "",
          runId: turn.id,
          intent: turn.intent,
          status: turn.status,
          pending: turn.status === "awaiting_approval" ? turn.pending_action : null,
        });
      }
      setMessages(msgs);
      setConversationId(id);
    } catch {
      /* ignore */
    }
  }, []);

  return { messages, conversationId, threads, busy, send, decide, newChat, loadThread, refreshThreads };
}

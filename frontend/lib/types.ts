// Shared types for the chat experience and the SSE stream the backend emits.

export type Persona = { id: string; name: string; plan: string; blurb: string };

export type Citation = { title: string; score: number };

export type PendingAction = { action: string; [k: string]: unknown };

export type RunResult = {
  run_id: string;
  conversation_id: string | null;
  intent: string | null;
  response: string | null;
  status: string | null;
  pending_action: PendingAction | null;
  grounded: boolean;
  tools: string[];
};

export type SSEEvent =
  | { type: "run_started"; data: { run_id: string; conversation_id: string | null } }
  | { type: "router"; data: { intent: string; customer_id: string | null } }
  | { type: "rag"; data: { included: Citation[]; excluded: Citation[]; tools: string[] } }
  | { type: "tool"; data: { tool: string; result: unknown } }
  | { type: "policy"; data: { intent: string; outcome: string } }
  | { type: "token"; data: { text: string } }
  | { type: "done"; data: RunResult }
  | { type: "error"; data: { detail: string } };

export type NodeKey = "router" | "retrieval" | "policy" | "response";
export type NodeStatus = "idle" | "active" | "done" | "skipped";
export type GraphState = Record<NodeKey, NodeStatus>;

export type ChatMessage = {
  id: string;
  role: "user" | "assistant";
  content: string;
  streaming?: boolean;
  runId?: string;
  intent?: string | null;
  status?: string | null;
  pending?: PendingAction | null;
  decision?: "approve" | "reject";
  citations?: Citation[];
  excluded?: Citation[];
  tools?: string[];
  error?: string;
  graph?: GraphState;
};

export const PERSONAS: Persona[] = [
  { id: "cus_001", name: "Ada Lovelace", plan: "Pro", blurb: "Active · has a duplicate charge" },
  { id: "cus_002", name: "Grace Hopper", plan: "Team", blurb: "Active · clean billing history" },
  { id: "cus_003", name: "Alan Turing", plan: "Enterprise", blurb: "Past due · needs review" },
];

export const SUGGESTIONS = [
  "I was charged twice this month, can I get a refund?",
  "What's my current plan and when does it renew?",
  "I'd like a refund for my last invoice.",
  "I need to speak to a human about my account.",
];

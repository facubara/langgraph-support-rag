# Architecture

> Placeholder — filled in as the system is built. Will include the agent graph diagram,
> state schema, the tool gateway/validation design, the eval scoring rubric, and the
> trace/replay model.

## Agent graph (planned)

- **Router** → classifies intent (billing question | duplicate charge | refund request | escalation).
- **Billing / RAG Agent** → retrieval + tool calls to answer.
- **Policy / Safety Agent** → refund-eligibility check; human-in-the-loop gate on risky tools.
- **Response Agent** → grounded final reply + context/tool report.

## Run state & replay

Each run persists its full state and step trace to SQLite (run id, messages, retrieved context,
tool calls + recorded outputs, model calls, latency, cost, errors).

**Deterministic replay.** Everything in the graph is deterministic *except* the user-facing
phrasing the Response agent gets from the LLM (under a real provider, the same prompt can yield
different text). `POST /runs/{id}/replay` re-runs the graph for a recorded run, but a `ReplayLLM`
serves that run's **recorded** completions in call order instead of calling the provider — wired
in through a context variable that `llm.factory.get_llm` consults, so no node knows whether it is
live or replaying. Tool results come from static fixtures and routing/policy are rule-based, so the
replay reproduces the original outcome and the endpoint returns a diff (intent, status, response,
pending action, tool sequence) against the source run. The replay is stored as its own run linked
via `replay_of`.

## Observability dashboard

A server-rendered HTML dashboard (no template engine or JS build) runs from the same FastAPI
process: `GET /dashboard` lists recent runs; `GET /dashboard/runs/{id}` shows the full step trace
(per-step type, latency, cost, input/output, errors), any linked replays, and a button to replay
the run and view the match/diff inline.

## Mock business tools (planned)

`get_customer_profile` · `get_invoice_history` · `check_refund_policy` ·
`create_refund_ticket` (HITL) · `escalate_to_human` (HITL)

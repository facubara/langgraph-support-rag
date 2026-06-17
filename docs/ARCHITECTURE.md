# Architecture

> Placeholder — filled in as the system is built. Will include the agent graph diagram,
> state schema, the tool gateway/validation design, the eval scoring rubric, and the
> trace/replay model.

## Agent graph (planned)

- **Router** → classifies intent (billing question | duplicate charge | refund request | escalation).
- **Billing / RAG Agent** → retrieval + tool calls to answer.
- **Policy / Safety Agent** → refund-eligibility check; human-in-the-loop gate on risky tools.
- **Response Agent** → grounded final reply + context/tool report.

## Run state & replay (planned)

Each run persists its full state and step trace to SQLite (run id, messages, retrieved context,
tool calls + recorded outputs, model calls, latency, cost, errors). A run is replayed
deterministically from its recorded tool outputs + seed.

## Mock business tools (planned)

`get_customer_profile` · `get_invoice_history` · `check_refund_policy` ·
`create_refund_ticket` (HITL) · `escalate_to_human` (HITL)

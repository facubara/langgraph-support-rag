# langgraph-support-rag

A production-style **multi-agent customer-support / billing assistant** demo built to show
the concepts that separate a real agentic system from a toy chatbot: multi-agent orchestration,
RAG grounding, tool use with human-in-the-loop safety, an evaluation framework, full-trace
observability with deterministic replay, and one-command Docker deployment.

> Status: 🚧 work in progress. Building in the open.

## What it does

Handles realistic SaaS support scenarios — billing questions, duplicate charges, refund-policy
checks, and escalation to human review — using a small multi-agent graph that only answers from
approved tool data and a grounded knowledge base.

## Architecture

Four agents on a [LangGraph](https://langchain-ai.github.io/langgraph/) state graph:

1. **Router** — classifies intent and routes the conversation.
2. **Billing / RAG Agent** — retrieves context and calls business tools to answer.
3. **Policy / Safety Agent** — checks refund eligibility against policy and gates risky actions.
4. **Response Agent** — composes the final grounded reply and reports the context/tools it used.

**Why LangGraph:** the graph and run-state are explicit, which makes orchestration, agent handoffs,
and deterministic replay first-class — exactly what evals and observability need.

```
user → Router → Billing/RAG ⇄ tools ⇄ KB → Policy/Safety (HITL gate) → Response → user
                         │
                  every step traced → SQLite → dashboard + replay
```

## Capabilities (target)

- **Model orchestration** — provider/model via env vars; retry, timeout, and fallback on LLM calls; versioned prompts.
- **Context optimization** — RAG over a policy/FAQ knowledge base; per-run logging of context included vs. excluded; token-budget trimming.
- **Tool use & grounding** — mock business tools (`get_customer_profile`, `get_invoice_history`, `check_refund_policy`, `create_refund_ticket`, `escalate_to_human`); tool-call validation; human-in-the-loop approval before risky actions; refuses to answer when unsupported by context.
- **Evaluation framework** — offline test dataset; scored report for task success, grounding, tool correctness, policy compliance, and escalation correctness; regression diff between prompt/model versions.
- **Observability** — every prompt, model call, tool call, latency, cost, and error traced to SQLite; a dashboard to inspect runs and **replay** a failed conversation deterministically.
- **Deployment** — `docker compose up`, env-based provider configuration, architecture doc.

## Tech stack

Python · LangGraph · FastAPI · SQLite (state + traces) · Chroma/pgvector (KB) · Docker Compose ·
OpenAI / Anthropic (configurable).

## Quick start

```bash
cp .env.example .env   # add your API key
pip install -r requirements.txt
# (run instructions added as the app comes together)
```

## License

MIT — see [LICENSE](LICENSE).

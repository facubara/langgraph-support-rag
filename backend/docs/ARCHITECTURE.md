# Architecture

A multi-agent customer-support / billing assistant. One conversation turn enters the graph,
is routed to specialist agents, gated for safety, and answered only from approved tool data and a
grounded knowledge base — with every step traced for observability and deterministic replay.

## Agent graph

A [LangGraph](https://langchain-ai.github.io/langgraph/) state machine with four nodes and
conditional routing:

```
user → Router ─┬→ Billing/RAG ⇄ tools ⇄ KB ─┐
               └→ RAG-only ──────────────────┤
                                             ▼
                                     Policy/Safety ──(risky?)── HITL gate → approve/reject
                                             │
                                             ▼
                                         Response → user
                                             │
              every node emits a step → SQLite → dashboard + replay
```

- **Router** — classifies intent (billing question | duplicate charge | refund request | escalation)
  and picks the downstream path.
- **Billing / RAG Agent** — retrieves KB context and calls business tools to gather facts.
- **Policy / Safety Agent** — checks refund eligibility against policy and gates risky tools
  (`create_refund_ticket`, `escalate_to_human`) behind a human-in-the-loop approval.
- **Response Agent** — composes the grounded final reply and reports the context/tools it used;
  refuses when nothing in context supports an answer.

**Why LangGraph:** the graph and run-state are explicit, which makes orchestration, agent handoffs,
and deterministic replay first-class — exactly what evals and observability need.

## LLM layer (provider-configurable)

`llm.factory.get_llm` returns a provider chosen by `LLM_PROVIDER`:

- **mock** (default) — deterministic, no API key, zero cost; runs the whole pipeline in tests and demos.
- **gemini** — real calls via `GOOGLE_API_KEY`.

The interface (`llm/base.py`) is small enough that an OpenAI/Anthropic adapter is a single drop-in
file. Every provider is wrapped by a `ResilientLLM` (timeout → retry → optional fallback model), and
the factory consults a context variable so a `ReplayLLM` can transparently serve recorded completions
during replay without any node knowing. The interface also exposes `stream()` (default: one chunk of
the full `complete()` text), which providers override for true token streaming.

## Streaming (SSE)

`POST /runs/stream` runs a turn and emits Server-Sent Events: `run_started → router → rag → tool* →
policy → token* → done` (or `error`). The graph stays **synchronous** — only the Response agent's text
is streamed. The Response node, when `stream_response` is set, builds the prompt via
`build_response_prompt` but defers the LLM call; the streaming layer (`run_conversation_streaming`)
then calls `get_llm().stream(...)`, emits a `token` event per chunk, applies the HITL suffix, persists
the final `llm` step, and emits `done`. Because the persisted trace is identical to the non-streaming
path, a streamed run replays deterministically. Mid-stream provider failures (after the first token)
surface as an `error` event — they can't be retried once tokens are on the wire.

## Multi-turn conversations

A `conversation_id` threads turns together. `conversations` rows hold thread metadata; each `run` links
back via `conversation_id` + `turn_index`. On a new turn the graph loads the last
`CONVERSATION_HISTORY_TURNS` turns into `history` (prepended to the response prompt) and resolves a
**sticky** customer id from the thread when the turn omits one. Omitting `conversation_id` preserves the
original single-turn behavior exactly. Because replay records LLM *output* (not the prompt), a
conversation turn still replays deterministically even though the replay prompt has no history.

## RAG grounding

The KB (`app/kb/*.md`) is chunked by paragraph and embedded with a local deterministic embedder, then
served by a cosine top-k retriever. The caller applies a score threshold (`RAG_MIN_SCORE`) to decide
what is grounded enough to include; chunks below it are logged as *excluded*, and the Response agent
refuses rather than answer ungrounded.

## Run state & replay

Each run persists its full state and step trace to SQLite (run id, message, intent, retrieved context,
tool calls + recorded outputs, model calls, latency, cost, errors, status, pending action).

**Deterministic replay.** Everything in the graph is deterministic *except* the user-facing phrasing
from the LLM. `POST /runs/{id}/replay` re-runs the graph for a recorded run, but `ReplayLLM` serves
that run's **recorded** completions in call order instead of calling the provider — wired in through a
context variable that `llm.factory.get_llm` consults, so no node knows whether it is live or replaying.
Tool results come from static fixtures and routing/policy are rule-based, so the replay reproduces the
original outcome and the endpoint returns a diff (intent, status, response, pending action, tool
sequence) against the source run. The replay is stored as its own run linked via `replay_of`.

## Security & access control

The Next.js app is the only intended caller (a backend-for-frontend). Its server-side route
handlers read the Auth.js session and forward each request with a shared secret
(`X-Internal-Secret`) plus the user's identity (`X-User-Id` / `X-User-Email`). FastAPI trusts those
identity headers only because the secret gates them (`app/auth.py`).

- **`AUTH_REQUIRED`** (default off for the demo/tests) — when on, write endpoints demand a valid
  shared secret + user id (`require_user`); `/health` stays open. Anonymous mode attributes requests
  to the supplied id or the client IP so rate limiting still applies.
- **Rate limiting** (`app/ratelimit.py`) — a per-user sliding window (default 30/60s, in-process)
  on `POST /runs` and `/runs/stream`; over-limit returns `429` with `Retry-After` + `X-RateLimit-*`
  headers. Redis is the documented multi-instance swap.
- **Sign-in tracking** — the frontend's Auth.js `events.signIn` calls `POST /auth/sign-in`
  (shared-secret gated) which upserts a `users` row and logs a `sign_in` event. The owner
  (`OWNER_EMAIL`) can read `GET /admin/users` and `/admin/sign-ins`.

## Observability dashboard

A server-rendered HTML dashboard (no template engine or JS build) runs from the same FastAPI process:
`GET /dashboard` lists recent runs; `GET /dashboard/runs/{id}` shows the full step trace (per-step
type, latency, cost, input/output, errors), any linked replays, and a button to replay the run and
view the match/diff inline.

## Evaluation framework

`evals/runner.py` scores an offline dataset (`evals/dataset.json`) on task success, grounding, tool
correctness, policy compliance, and escalation correctness; `evals/compare.py` diffs two reports to
catch regressions between prompt/model versions (`PROMPT_VERSION`). Reports land in `evals/reports/`.

## Business tools

`get_customer_profile` · `get_invoice_history` · `check_refund_policy` ·
`create_refund_ticket` (HITL) · `escalate_to_human` (HITL). Each has a Pydantic args schema; the tool
gateway validates arguments before invocation and flags which tools require approval.

## Deployment

The service is pure Python and serves the API + dashboard from one ASGI process, so deployment is a
single container.

- **Dockerfile** — `python:3.13-slim`, deps cached in their own layer, runs as an unprivileged user,
  and ships a `/health` healthcheck driven by the interpreter (no curl in the image). Entrypoint:
  `uvicorn app.main:app --host 0.0.0.0 --port 8000`.
- **docker-compose.yml** — `docker compose up --build` brings the stack up on the mock provider with
  no key. `.env` is optional (`required: false`); when present it injects provider config. The SQLite
  run/trace store is persisted on a named `runtime` volume so runs survive restarts.
- **Configuration** — all runtime config is environment-driven via `app/config.py` (`Settings`); every
  key is documented in `.env.example`, and `tests/test_deployment.py` asserts the example, the
  Dockerfile, and the compose file stay coherent with the app.

```bash
docker compose up --build          # API + dashboard on http://localhost:8000
# real provider:
cp .env.example .env               # set LLM_PROVIDER=gemini and GOOGLE_API_KEY=...
docker compose up --build
```

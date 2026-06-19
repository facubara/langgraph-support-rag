# Support Copilot — multi-agent RAG assistant

A production-style **multi-agent customer-support / billing assistant**, built as a full-stack
portfolio piece. It shows the concepts that separate a real agentic system from a toy chatbot:
multi-agent orchestration, RAG grounding, tool use with human-in-the-loop safety, an evaluation
framework, full-trace observability with deterministic replay — now with a polished **Next.js**
frontend, **Google sign-in**, streaming, and per-user rate limiting.

> **Monorepo:** a Python **FastAPI** backend (`backend/`) and a **Next.js** frontend (`frontend/`).
> Frontend deploys to **Vercel**, backend to **Render**; they talk over an authenticated
> backend-for-frontend (BFF) proxy.

```
langgraph-support-rag/
├── backend/      FastAPI · LangGraph · RAG · SQLite · evals   (deploys to Render)
├── frontend/     Next.js 16 · Auth.js (Google) · Tailwind     (deploys to Vercel)
└── docker-compose.yml   one-command local backend
```

## Architecture

```
Browser ──► Next.js (Vercel)                          FastAPI (Render)
            ├─ Auth.js (Google OAuth)                   ├─ /runs, /runs/stream (SSE)
            ├─ chat UI · live agent graph · dashboard   ├─ LangGraph: router → billing/RAG
            └─ /api/* BFF proxy ────────────────────────►   → policy/safety (HITL) → response
                 adds shared secret + user identity      └─ SQLite traces on a persistent disk
```

Four agents on a [LangGraph](https://langchain-ai.github.io/langgraph/) state graph:

1. **Router** — classifies intent and routes the conversation.
2. **Billing / RAG Agent** — retrieves context and calls business tools to answer.
3. **Policy / Safety Agent** — checks refund eligibility and gates risky actions behind human approval.
4. **Response Agent** — composes the grounded reply and reports the context/tools it used.

**Auth model (BFF):** the browser only talks to Next.js. Server-side route handlers read the Auth.js
session and forward requests to FastAPI with a shared secret + identity headers, so the browser never
hits the backend directly and the backend can rate-limit and attribute every request to a user.

## What it demonstrates

- **Multi-agent orchestration** — explicit LangGraph state machine with conditional routing and hand-offs.
- **RAG grounding** — retrieval over a policy/FAQ KB with score thresholds; refuses when unsupported.
- **Tool use & HITL safety** — validated business tools; refunds/escalations pause for human approval.
- **Streaming** — token-by-token SSE responses with a live, lighting-up agent graph.
- **Observability** — every prompt, tool call, latency, and cost traced to SQLite; deterministic replay.
- **Evaluation** — offline scored dataset with regression diffs between prompt/model versions.
- **Auth & abuse control** — Google sign-in, per-user rate limiting, sign-in tracking.

## Quick start

### Backend (FastAPI)

```bash
cd backend
python -m venv .venv && . .venv/Scripts/activate   # Windows; use bin/activate on macOS/Linux
pip install -r requirements.txt
cp .env.example .env                                # defaults to the mock provider — no key needed
uvicorn app.main:app --reload                       # http://localhost:8000  (/docs, /dashboard)
pytest                                              # run the test suite
```

### Frontend (Next.js)

```bash
cd frontend
npm install
cp .env.example .env.local                          # set AUTH_SECRET + AUTH_GOOGLE_* for real sign-in
npm run dev                                          # http://localhost:3000
```

### Backend via Docker (one command)

```bash
docker compose up --build                            # FastAPI on http://localhost:8000
```

Runs on the built-in **mock** provider (no API key, zero cost); the SQLite run/trace store persists on
a named volume. For real Gemini calls, set `LLM_PROVIDER=gemini` + `GOOGLE_API_KEY` in `backend/.env`.

> Tip: locally you can skip Google OAuth — set `ALLOW_DEV_LOGIN=true` in `frontend/.env.local` for a
> one-click "demo user" sign-in. Leave it unset in production.

See [`backend/docs/ARCHITECTURE.md`](backend/docs/ARCHITECTURE.md) and
[`frontend/README.md`](frontend/README.md) for package-level details.

## Deployment

Frontend → **Vercel**, backend → **Render**, talking over the authenticated BFF proxy.

**Backend (Render).** Use the [`render.yaml`](render.yaml) blueprint (Docker, `rootDir: backend`,
`/health` check, SQLite on a 1 GB disk at `/data`). Set these env vars in the Render dashboard:

| Var | Value |
| --- | --- |
| `SERVICE_SHARED_SECRET` | a strong random string — **must match Vercel** |
| `OWNER_EMAIL` | your email (unlocks `/admin`) |
| `CORS_ALLOW_ORIGINS` | `https://<your-app>.vercel.app` |
| `AUTH_REQUIRED` | `true` |

**Frontend (Vercel).** Import the repo with **root directory `frontend`**. Set:

| Var | Value |
| --- | --- |
| `BACKEND_URL` | your Render URL, e.g. `https://support-copilot-api.onrender.com` |
| `SERVICE_SHARED_SECRET` | same value as Render |
| `AUTH_SECRET` | `npx auth secret` |
| `AUTH_GOOGLE_ID` / `AUTH_GOOGLE_SECRET` | Google OAuth client (redirect URI `https://<app>.vercel.app/api/auth/callback/google`) |

Do **not** set `ALLOW_DEV_LOGIN` in production. Note: Render's free tier has no persistent disk
(SQLite resets on redeploy); the blueprint uses a paid `starter` instance for durable storage —
swap to managed Postgres if you need multi-instance scale.

## License

MIT — see [LICENSE](LICENSE).

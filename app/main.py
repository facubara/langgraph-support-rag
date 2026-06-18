"""FastAPI surface for the demo.

Endpoints:
- GET  /health                  — liveness + active provider/model
- GET  /tools                   — list tools and their JSON arg schemas
- POST /tools/{name}            — validate + invoke a single tool (test harness)
- POST /runs                    — run one conversation turn through the multi-agent graph
- GET  /runs                    — list recent runs
- GET  /runs/{run_id}           — inspect a run and its full step trace
- POST /runs/{run_id}/approve   — HITL: execute the risky action a run is awaiting
- POST /runs/{run_id}/reject    — HITL: reject the proposed action
- POST /runs/{run_id}/replay    — deterministically replay a run and diff vs. the original
- GET  /dashboard               — HTML run list (observability)
- GET  /dashboard/runs/{run_id} — HTML run detail: full trace + replay button

Run with:  uvicorn app.main:app --reload
"""

from __future__ import annotations

from contextlib import asynccontextmanager

from fastapi import FastAPI, HTTPException
from fastapi.responses import HTMLResponse
from pydantic import BaseModel

from . import dashboard, replay
from .agents.approval import execute_approved_action
from .config import settings
from .graph import run_conversation
from .store import run_store
from .tools.registry import TOOLS, ToolValidationError, call_tool


@asynccontextmanager
async def lifespan(app: FastAPI):
    run_store.init_db()
    yield


app = FastAPI(title="langgraph-support-rag", version="0.1.0", lifespan=lifespan)


@app.get("/health")
def health() -> dict[str, str]:
    return {"status": "ok", "provider": settings.llm_provider, "model": settings.llm_model}


@app.get("/tools")
def list_tools() -> list[dict]:
    return [
        {
            "name": t.name,
            "description": t.description,
            "requires_approval": t.requires_approval,
            "args_schema": t.args_model.model_json_schema(),
        }
        for t in TOOLS.values()
    ]


class ToolCallRequest(BaseModel):
    args: dict


@app.post("/tools/{name}")
def invoke_tool(name: str, req: ToolCallRequest) -> dict:
    try:
        return call_tool(name, req.args)
    except ToolValidationError as err:
        raise HTTPException(status_code=400, detail=str(err)) from err


class RunRequest(BaseModel):
    message: str
    customer_id: str | None = None


@app.post("/runs")
def create_run(req: RunRequest) -> dict:
    """Run one conversation turn through the multi-agent graph."""
    return run_conversation(req.message, customer_id=req.customer_id)


@app.get("/runs")
def get_runs() -> list[dict]:
    return run_store.list_runs()


@app.get("/runs/{run_id}")
def get_run(run_id: str) -> dict:
    data = run_store.get_run(run_id)
    if data is None:
        raise HTTPException(status_code=404, detail="run not found")
    return data


def _require_run(run_id: str) -> dict:
    data = run_store.get_run(run_id)
    if data is None:
        raise HTTPException(status_code=404, detail="run not found")
    return data


@app.post("/runs/{run_id}/approve")
def approve_run(run_id: str) -> dict:
    """Human-in-the-loop: execute the risky action this run is waiting on."""
    data = _require_run(run_id)
    run = data["run"]
    if run["status"] != "awaiting_approval" or not run.get("pending_action"):
        raise HTTPException(status_code=400, detail="run is not awaiting approval")

    action = run["pending_action"]
    result = execute_approved_action(action)
    run_store.add_step(
        run_id, step_index=run_store.count_steps(run_id), step_type="tool",
        name=action["action"], input=action, output=result,
    )
    final = f"Approved and executed: {action['action']} → {result}"
    run_store.finish_run(run_id, intent=run.get("intent"), final_response=final,
                         status="completed", pending_action=None)
    return {"run_id": run_id, "status": "completed", "result": result}


@app.post("/runs/{run_id}/replay")
def replay_run(run_id: str) -> dict:
    """Deterministically replay a recorded run and diff the result against the original.

    Re-runs the graph with the original message + resolved customer id, serving the run's
    recorded LLM outputs instead of calling a provider, so the outcome is reproducible.
    """
    original = _require_run(run_id)
    new_run_id = run_conversation(
        original["run"]["user_message"],
        customer_id=replay.recorded_customer_id(original),
        replay_of=run_id,
        recorded_responses=replay.recorded_llm_responses(original),
    )["run_id"]
    new_data = _require_run(new_run_id)
    return {
        "original_run_id": run_id,
        "replay_run_id": new_run_id,
        "comparison": replay.compare_runs(original, new_data),
    }


@app.post("/runs/{run_id}/reject")
def reject_run(run_id: str) -> dict:
    data = _require_run(run_id)
    run = data["run"]
    if run["status"] != "awaiting_approval":
        raise HTTPException(status_code=400, detail="run is not awaiting approval")
    run_store.add_step(
        run_id, step_index=run_store.count_steps(run_id), step_type="approval",
        name="rejected", input=run.get("pending_action"), output={"status": "rejected"},
    )
    run_store.finish_run(run_id, intent=run.get("intent"),
                         final_response="The proposed action was rejected by a human reviewer.",
                         status="rejected", pending_action=None)
    return {"run_id": run_id, "status": "rejected"}


# --------------------------------------------------------------- observability dashboard
@app.get("/dashboard", response_class=HTMLResponse)
def dashboard_index() -> str:
    return dashboard.render_run_list(run_store.list_runs())


@app.get("/dashboard/runs/{run_id}", response_class=HTMLResponse)
def dashboard_run(run_id: str) -> str:
    data = _require_run(run_id)
    return dashboard.render_run_detail(data, run_store.list_replays(run_id))

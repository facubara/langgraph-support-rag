"""FastAPI surface for the demo.

Day 1 endpoints:
- GET  /health            — liveness + active provider/model
- GET  /tools             — list tools and their JSON arg schemas
- POST /tools/{name}      — validate + invoke a single tool (test harness)
- POST /runs              — create a run (Day 1: single mock/LLM step; the multi-agent
                            graph replaces the stub on Day 2)
- GET  /runs              — list recent runs
- GET  /runs/{run_id}     — inspect a run and its full step trace

Run with:  uvicorn app.main:app --reload
"""

from __future__ import annotations

from contextlib import asynccontextmanager

from fastapi import FastAPI, HTTPException
from pydantic import BaseModel

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

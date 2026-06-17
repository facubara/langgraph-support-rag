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

import uuid
from contextlib import asynccontextmanager

from fastapi import FastAPI, HTTPException
from pydantic import BaseModel

from .config import settings
from .llm.factory import get_llm
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


@app.post("/runs")
def create_run(req: RunRequest) -> dict:
    run_id = uuid.uuid4().hex[:12]
    run_store.create_run(run_id, req.message)

    # Day 1 stub: one LLM step, fully traced. The multi-agent graph lands on Day 2.
    llm = get_llm()
    resp = llm.complete(system="You are a helpful SaaS support assistant.", prompt=req.message)
    run_store.add_step(
        run_id,
        step_index=0,
        step_type="llm",
        name=resp.model,
        input={"prompt": req.message},
        output={"text": resp.text},
        latency_ms=resp.latency_ms,
        cost_usd=resp.cost_usd,
    )
    run_store.finish_run(run_id, final_response=resp.text)
    return {"run_id": run_id, "response": resp.text}


@app.get("/runs")
def get_runs() -> list[dict]:
    return run_store.list_runs()


@app.get("/runs/{run_id}")
def get_run(run_id: str) -> dict:
    data = run_store.get_run(run_id)
    if data is None:
        raise HTTPException(status_code=404, detail="run not found")
    return data

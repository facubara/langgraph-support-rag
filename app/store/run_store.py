"""Run + step persistence on SQLite.

A *run* is one conversation turn through the system. Each *step* is one traced unit of
work (router decision, LLM call, tool call, ...) with its input, output, latency, cost,
and error. Recording tool outputs here is what makes deterministic replay possible later.
"""

from __future__ import annotations

import json
import sqlite3
import time
from contextlib import contextmanager
from pathlib import Path
from typing import Any, Iterator

from ..config import settings

_SCHEMA = """
CREATE TABLE IF NOT EXISTS runs (
    id             TEXT PRIMARY KEY,
    created_at     REAL NOT NULL,
    user_message   TEXT NOT NULL,
    intent         TEXT,
    final_response TEXT,
    status         TEXT NOT NULL DEFAULT 'created',
    pending_action TEXT,
    replay_of      TEXT
);

CREATE TABLE IF NOT EXISTS steps (
    id          INTEGER PRIMARY KEY AUTOINCREMENT,
    run_id      TEXT NOT NULL,
    step_index  INTEGER NOT NULL,
    step_type   TEXT NOT NULL,
    name        TEXT,
    input_json  TEXT,
    output_json TEXT,
    latency_ms  REAL,
    cost_usd    REAL,
    error       TEXT,
    created_at  REAL NOT NULL,
    FOREIGN KEY (run_id) REFERENCES runs (id)
);

CREATE INDEX IF NOT EXISTS idx_steps_run ON steps (run_id, step_index);
"""


def _db_path() -> Path:
    path = Path(settings.sqlite_path)
    path.parent.mkdir(parents=True, exist_ok=True)
    return path


@contextmanager
def _conn() -> Iterator[sqlite3.Connection]:
    conn = sqlite3.connect(_db_path())
    conn.row_factory = sqlite3.Row
    try:
        yield conn
        conn.commit()
    finally:
        conn.close()


def init_db() -> None:
    with _conn() as conn:
        conn.executescript(_SCHEMA)


def create_run(run_id: str, user_message: str, replay_of: str | None = None) -> None:
    with _conn() as conn:
        conn.execute(
            "INSERT INTO runs (id, created_at, user_message, status, replay_of) "
            "VALUES (?, ?, ?, ?, ?)",
            (run_id, time.time(), user_message, "created", replay_of),
        )


def add_step(
    run_id: str,
    step_index: int,
    step_type: str,
    name: str | None = None,
    input: Any = None,
    output: Any = None,
    latency_ms: float | None = None,
    cost_usd: float | None = None,
    error: str | None = None,
) -> None:
    with _conn() as conn:
        conn.execute(
            """INSERT INTO steps
               (run_id, step_index, step_type, name, input_json, output_json,
                latency_ms, cost_usd, error, created_at)
               VALUES (?, ?, ?, ?, ?, ?, ?, ?, ?, ?)""",
            (
                run_id,
                step_index,
                step_type,
                name,
                json.dumps(input) if input is not None else None,
                json.dumps(output) if output is not None else None,
                latency_ms,
                cost_usd,
                error,
                time.time(),
            ),
        )


def finish_run(
    run_id: str,
    intent: str | None = None,
    final_response: str | None = None,
    status: str = "completed",
    pending_action: dict[str, Any] | None = None,
) -> None:
    with _conn() as conn:
        conn.execute(
            "UPDATE runs SET intent = ?, final_response = ?, status = ?, pending_action = ? "
            "WHERE id = ?",
            (
                intent,
                final_response,
                status,
                json.dumps(pending_action) if pending_action is not None else None,
                run_id,
            ),
        )


def _decode_step(row: sqlite3.Row) -> dict[str, Any]:
    step = dict(row)
    step["input"] = json.loads(step.pop("input_json")) if step.get("input_json") else None
    step["output"] = json.loads(step.pop("output_json")) if step.get("output_json") else None
    return step


def get_run(run_id: str) -> dict[str, Any] | None:
    with _conn() as conn:
        run = conn.execute("SELECT * FROM runs WHERE id = ?", (run_id,)).fetchone()
        if run is None:
            return None
        steps = conn.execute(
            "SELECT * FROM steps WHERE run_id = ? ORDER BY step_index, id", (run_id,)
        ).fetchall()
        run_dict = dict(run)
        if run_dict.get("pending_action"):
            run_dict["pending_action"] = json.loads(run_dict["pending_action"])
        return {"run": run_dict, "steps": [_decode_step(s) for s in steps]}


def count_steps(run_id: str) -> int:
    with _conn() as conn:
        row = conn.execute("SELECT COUNT(*) AS n FROM steps WHERE run_id = ?", (run_id,)).fetchone()
        return int(row["n"])


def list_runs(limit: int = 50) -> list[dict[str, Any]]:
    with _conn() as conn:
        rows = conn.execute(
            "SELECT * FROM runs ORDER BY created_at DESC LIMIT ?", (limit,)
        ).fetchall()
        return [dict(r) for r in rows]


def list_replays(run_id: str) -> list[dict[str, Any]]:
    """Runs that were created by replaying `run_id`, most recent first."""
    with _conn() as conn:
        rows = conn.execute(
            "SELECT * FROM runs WHERE replay_of = ? ORDER BY created_at DESC", (run_id,)
        ).fetchall()
        return [dict(r) for r in rows]

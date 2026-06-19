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
    id              TEXT PRIMARY KEY,
    created_at      REAL NOT NULL,
    user_message    TEXT NOT NULL,
    intent          TEXT,
    final_response  TEXT,
    status          TEXT NOT NULL DEFAULT 'created',
    pending_action  TEXT,
    replay_of       TEXT,
    conversation_id TEXT,
    turn_index      INTEGER
);

CREATE TABLE IF NOT EXISTS conversations (
    id          TEXT PRIMARY KEY,
    created_at  REAL NOT NULL,
    updated_at  REAL NOT NULL,
    user_id     TEXT,
    customer_id TEXT,
    title       TEXT
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

CREATE TABLE IF NOT EXISTS users (
    id            TEXT PRIMARY KEY,
    email         TEXT,
    name          TEXT,
    first_seen    REAL NOT NULL,
    last_seen     REAL NOT NULL,
    sign_in_count INTEGER NOT NULL DEFAULT 0
);

CREATE TABLE IF NOT EXISTS events (
    id          INTEGER PRIMARY KEY AUTOINCREMENT,
    ts          REAL NOT NULL,
    user_id     TEXT,
    type        TEXT NOT NULL,
    detail_json TEXT
);

CREATE INDEX IF NOT EXISTS idx_steps_run ON steps (run_id, step_index);
CREATE INDEX IF NOT EXISTS idx_runs_conversation ON runs (conversation_id, turn_index);
CREATE INDEX IF NOT EXISTS idx_events_type ON events (type, ts);
"""

# Columns added after the initial schema shipped. SQLite has no "ADD COLUMN IF NOT EXISTS",
# so we check PRAGMA table_info and add what's missing — keeps existing DBs on a volume intact.
_RUNS_MIGRATIONS = {
    "conversation_id": "ALTER TABLE runs ADD COLUMN conversation_id TEXT",
    "turn_index": "ALTER TABLE runs ADD COLUMN turn_index INTEGER",
}


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
        existing = {row["name"] for row in conn.execute("PRAGMA table_info(runs)")}
        for column, ddl in _RUNS_MIGRATIONS.items():
            if column not in existing:
                conn.execute(ddl)


def create_run(
    run_id: str,
    user_message: str,
    replay_of: str | None = None,
    conversation_id: str | None = None,
    turn_index: int | None = None,
) -> None:
    with _conn() as conn:
        conn.execute(
            "INSERT INTO runs (id, created_at, user_message, status, replay_of, "
            "conversation_id, turn_index) VALUES (?, ?, ?, ?, ?, ?, ?)",
            (run_id, time.time(), user_message, "created", replay_of, conversation_id, turn_index),
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


# ---------------------------------------------------------------------- conversations
def create_conversation(
    conversation_id: str,
    user_id: str | None = None,
    customer_id: str | None = None,
    title: str | None = None,
) -> None:
    now = time.time()
    with _conn() as conn:
        conn.execute(
            "INSERT INTO conversations (id, created_at, updated_at, user_id, customer_id, title) "
            "VALUES (?, ?, ?, ?, ?, ?)",
            (conversation_id, now, now, user_id, customer_id, title),
        )


def conversation_exists(conversation_id: str) -> bool:
    with _conn() as conn:
        row = conn.execute(
            "SELECT 1 FROM conversations WHERE id = ?", (conversation_id,)
        ).fetchone()
        return row is not None


def next_turn_index(conversation_id: str) -> int:
    with _conn() as conn:
        row = conn.execute(
            "SELECT COALESCE(MAX(turn_index), -1) AS m FROM runs WHERE conversation_id = ?",
            (conversation_id,),
        ).fetchone()
        return int(row["m"]) + 1


def touch_conversation(conversation_id: str, customer_id: str | None = None) -> None:
    """Bump updated_at, and remember the latest customer id seen on the thread."""
    with _conn() as conn:
        if customer_id:
            conn.execute(
                "UPDATE conversations SET updated_at = ?, customer_id = ? WHERE id = ?",
                (time.time(), customer_id, conversation_id),
            )
        else:
            conn.execute(
                "UPDATE conversations SET updated_at = ? WHERE id = ?",
                (time.time(), conversation_id),
            )


def get_conversation(conversation_id: str) -> dict[str, Any] | None:
    """A conversation plus its runs in turn order (each run includes its step trace)."""
    with _conn() as conn:
        conv = conn.execute(
            "SELECT * FROM conversations WHERE id = ?", (conversation_id,)
        ).fetchone()
        if conv is None:
            return None
        rows = conn.execute(
            "SELECT * FROM runs WHERE conversation_id = ? ORDER BY turn_index, created_at",
            (conversation_id,),
        ).fetchall()
    turns = []
    for r in rows:
        run = dict(r)
        if run.get("pending_action"):
            run["pending_action"] = json.loads(run["pending_action"])
        turns.append(run)
    return {"conversation": dict(conv), "turns": turns}


def list_conversations(user_id: str | None = None, limit: int = 50) -> list[dict[str, Any]]:
    with _conn() as conn:
        if user_id:
            rows = conn.execute(
                "SELECT * FROM conversations WHERE user_id = ? ORDER BY updated_at DESC LIMIT ?",
                (user_id, limit),
            ).fetchall()
        else:
            rows = conn.execute(
                "SELECT * FROM conversations ORDER BY updated_at DESC LIMIT ?", (limit,)
            ).fetchall()
        return [dict(r) for r in rows]


# ------------------------------------------------------------- users / sign-in tracking
def record_sign_in(user_id: str, email: str | None = None, name: str | None = None) -> None:
    """Upsert the user, bump their sign-in count, and log a `sign_in` event."""
    now = time.time()
    with _conn() as conn:
        exists = conn.execute("SELECT 1 FROM users WHERE id = ?", (user_id,)).fetchone()
        if exists is None:
            conn.execute(
                "INSERT INTO users (id, email, name, first_seen, last_seen, sign_in_count) "
                "VALUES (?, ?, ?, ?, ?, 1)",
                (user_id, email, name, now, now),
            )
        else:
            conn.execute(
                "UPDATE users SET email = COALESCE(?, email), name = COALESCE(?, name), "
                "last_seen = ?, sign_in_count = sign_in_count + 1 WHERE id = ?",
                (email, name, now, user_id),
            )
        conn.execute(
            "INSERT INTO events (ts, user_id, type, detail_json) VALUES (?, ?, ?, ?)",
            (now, user_id, "sign_in", json.dumps({"email": email, "name": name})),
        )


def list_users(limit: int = 200) -> list[dict[str, Any]]:
    with _conn() as conn:
        rows = conn.execute(
            "SELECT * FROM users ORDER BY last_seen DESC LIMIT ?", (limit,)
        ).fetchall()
        return [dict(r) for r in rows]


def list_events(limit: int = 200, type: str | None = None) -> list[dict[str, Any]]:
    with _conn() as conn:
        if type:
            rows = conn.execute(
                "SELECT * FROM events WHERE type = ? ORDER BY ts DESC LIMIT ?", (type, limit)
            ).fetchall()
        else:
            rows = conn.execute(
                "SELECT * FROM events ORDER BY ts DESC LIMIT ?", (limit,)
            ).fetchall()
    out = []
    for r in rows:
        e = dict(r)
        e["detail"] = json.loads(e.pop("detail_json")) if e.get("detail_json") else None
        out.append(e)
    return out

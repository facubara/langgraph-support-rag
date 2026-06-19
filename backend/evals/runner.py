"""Offline eval runner.

Runs every case in dataset.json through the multi-agent graph (mock provider, isolated DB)
and scores it on intent, tool correctness, grounding, and action/policy correctness. Writes
a JSON + Markdown report under evals/reports/.

Usage:
    python -m evals.runner                          # baseline report
    python -m evals.runner --label hi_threshold --set rag_min_score=0.5
    python -m evals.runner --label prompt_v1 --set prompt_version=v1

The --set overrides patch settings for the run, which is how prompt/model/config versions
are compared (see evals/compare.py).
"""

from __future__ import annotations

import argparse
import json
import pathlib
import sys
import tempfile

# Make `app` importable whether run as a module or a script.
sys.path.insert(0, str(pathlib.Path(__file__).resolve().parent.parent))

from app.config import settings  # noqa: E402

HERE = pathlib.Path(__file__).resolve().parent
DATASET = HERE / "dataset.json"
REPORTS = HERE / "reports"


def _coerce(value: str):
    for cast in (int, float):
        try:
            return cast(value)
        except ValueError:
            continue
    if value.lower() in ("true", "false"):
        return value.lower() == "true"
    return value


def _apply_overrides(overrides: dict) -> dict:
    previous = {}
    for key, value in overrides.items():
        previous[key] = getattr(settings, key)
        setattr(settings, key, value)
    return previous


def _restore(previous: dict) -> None:
    for key, value in previous.items():
        setattr(settings, key, value)


def _score_case(case: dict, actual: dict, latency_ms: float, cost_usd: float) -> dict:
    expect = case["expect"]
    actual_action = actual["pending_action"]["action"] if actual.get("pending_action") else None
    checks = {
        "intent": actual.get("intent") == expect["intent"],
        "tools": sorted(set(actual.get("tools", []))) == sorted(set(expect["tools"])),
        "grounding": bool(actual.get("grounded")) == expect["grounded"],
        "action": actual_action == expect["action"],
    }
    return {
        "id": case["id"],
        "message": case["message"],
        "expect": expect,
        "actual": {
            "intent": actual.get("intent"),
            "tools": sorted(set(actual.get("tools", []))),
            "grounded": bool(actual.get("grounded")),
            "action": actual_action,
        },
        "checks": checks,
        "passed": all(checks.values()),
        "latency_ms": round(latency_ms, 3),
        "cost_usd": cost_usd,
    }


def run_suite(label: str = "baseline", overrides: dict | None = None) -> dict:
    import time

    from app.graph import run_conversation
    from app.store import run_store

    overrides = overrides or {}
    cases = json.loads(DATASET.read_text(encoding="utf-8"))

    with tempfile.TemporaryDirectory() as tmp:
        prev_db = settings.sqlite_path
        settings.sqlite_path = str(pathlib.Path(tmp) / "evals.sqlite")
        previous = _apply_overrides({**overrides, "llm_provider": "mock"})
        run_store.init_db()
        try:
            results = []
            for case in cases:
                start = time.perf_counter()
                actual = run_conversation(case["message"], customer_id=case.get("customer_id"))
                latency_ms = (time.perf_counter() - start) * 1000
                detail = run_store.get_run(actual["run_id"])
                cost = sum((s.get("cost_usd") or 0.0) for s in detail["steps"])
                results.append(_score_case(case, actual, latency_ms, cost))
        finally:
            _restore(previous)
            settings.sqlite_path = prev_db

    return _summarize(label, overrides, results)


def _rate(items: list[bool]) -> float:
    return round(sum(items) / len(items), 4) if items else 1.0


def _summarize(label: str, overrides: dict, results: list[dict]) -> dict:
    billing = [r for r in results if r["expect"]["intent"] in ("refund_request", "duplicate_charge")]
    escal = [r for r in results if r["expect"]["action"] == "escalate_to_human"
             or r["actual"]["action"] == "escalate_to_human"]
    summary = {
        "n": len(results),
        "task_success": _rate([r["passed"] for r in results]),
        "intent_accuracy": _rate([r["checks"]["intent"] for r in results]),
        "tool_correctness": _rate([r["checks"]["tools"] for r in results]),
        "grounding_accuracy": _rate([r["checks"]["grounding"] for r in results]),
        "action_correctness": _rate([r["checks"]["action"] for r in results]),
        "policy_compliance": _rate([r["checks"]["action"] for r in billing]),
        "escalation_correctness": _rate([r["checks"]["action"] for r in escal]),
        "avg_latency_ms": round(sum(r["latency_ms"] for r in results) / len(results), 3),
        "total_cost_usd": round(sum(r["cost_usd"] for r in results), 6),
    }
    return {"label": label, "config": overrides, "summary": summary, "cases": results}


def _to_markdown(report: dict) -> str:
    s = report["summary"]
    lines = [
        f"# Eval report — `{report['label']}`",
        "",
        f"Config overrides: `{report['config'] or 'none (defaults)'}`",
        "",
        "## Summary",
        "",
        "| Metric | Score |",
        "| --- | --- |",
    ]
    for key, val in s.items():
        lines.append(f"| {key} | {val} |")
    lines += ["", "## Cases", "", "| id | pass | intent | tools | grounding | action |", "| --- | --- | --- | --- | --- | --- |"]
    for c in report["cases"]:
        ch = c["checks"]
        mark = lambda b: "✅" if b else "❌"  # noqa: E731
        lines.append(
            f"| {c['id']} | {mark(c['passed'])} | {mark(ch['intent'])} | {mark(ch['tools'])} "
            f"| {mark(ch['grounding'])} | {mark(ch['action'])} |"
        )
    return "\n".join(lines) + "\n"


def write_report(report: dict) -> tuple[pathlib.Path, pathlib.Path]:
    REPORTS.mkdir(parents=True, exist_ok=True)
    json_path = REPORTS / f"{report['label']}.json"
    md_path = REPORTS / f"{report['label']}.md"
    json_path.write_text(json.dumps(report, indent=2) + "\n", encoding="utf-8")
    md_path.write_text(_to_markdown(report), encoding="utf-8")
    return json_path, md_path


def main(argv: list[str] | None = None) -> int:
    parser = argparse.ArgumentParser(description="Run the offline eval suite.")
    parser.add_argument("--label", default="baseline")
    parser.add_argument("--set", action="append", default=[], metavar="key=value",
                        help="Override a setting for this run (repeatable).")
    args = parser.parse_args(argv)

    overrides = {}
    for item in args.set:
        key, _, value = item.partition("=")
        overrides[key.strip()] = _coerce(value.strip())

    report = run_suite(label=args.label, overrides=overrides)
    json_path, md_path = write_report(report)
    s = report["summary"]
    print(f"[{report['label']}] task_success={s['task_success']} "
          f"intent={s['intent_accuracy']} tools={s['tool_correctness']} "
          f"grounding={s['grounding_accuracy']} action={s['action_correctness']}")
    print(f"wrote {json_path.relative_to(HERE.parent)} and {md_path.relative_to(HERE.parent)}")
    return 0


if __name__ == "__main__":
    raise SystemExit(main())

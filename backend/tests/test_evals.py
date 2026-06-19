from __future__ import annotations

from evals.runner import run_suite


def test_baseline_suite_fully_passes():
    report = run_suite(label="baseline")
    assert report["summary"]["task_success"] == 1.0, [
        c["id"] for c in report["cases"] if not c["passed"]
    ]


def test_high_threshold_regresses_grounding():
    report = run_suite(label="hi", overrides={"rag_min_score": 0.5})
    # Starving retrieval should only hurt grounding (and downstream task success),
    # never intent or tool selection.
    assert report["summary"]["grounding_accuracy"] < 1.0
    assert report["summary"]["intent_accuracy"] == 1.0
    assert report["summary"]["tool_correctness"] == 1.0

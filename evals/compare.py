"""Regression diff between two eval reports.

Usage:
    python -m evals.compare baseline hi_threshold

Prints metric deltas and lists cases whose pass/fail status flipped — the core of
prompt/model/config regression testing.
"""

from __future__ import annotations

import json
import pathlib
import sys

HERE = pathlib.Path(__file__).resolve().parent
REPORTS = HERE / "reports"


def _load(label: str) -> dict:
    return json.loads((REPORTS / f"{label}.json").read_text(encoding="utf-8"))


def compare(base_label: str, new_label: str) -> dict:
    base, new = _load(base_label), _load(new_label)
    deltas = {}
    for key, base_val in base["summary"].items():
        new_val = new["summary"].get(key)
        deltas[key] = {"base": base_val, "new": new_val,
                       "delta": round(new_val - base_val, 4) if isinstance(new_val, (int, float)) else None}

    base_pass = {c["id"]: c["passed"] for c in base["cases"]}
    flips = []
    for c in new["cases"]:
        was = base_pass.get(c["id"])
        if was is not None and was != c["passed"]:
            flips.append({"id": c["id"], "from": was, "to": c["passed"],
                          "actual": c["actual"], "expect": c["expect"]})
    return {"base": base_label, "new": new_label, "deltas": deltas, "flips": flips}


def main(argv: list[str] | None = None) -> int:
    argv = argv if argv is not None else sys.argv[1:]
    if len(argv) != 2:
        print("usage: python -m evals.compare <base_label> <new_label>")
        return 2
    result = compare(argv[0], argv[1])

    print(f"Regression: {result['base']}  ->  {result['new']}\n")
    print(f"{'metric':<24}{'base':>10}{'new':>10}{'delta':>10}")
    for key, d in result["deltas"].items():
        delta = "" if d["delta"] is None else f"{d['delta']:+.4f}"
        print(f"{key:<24}{str(d['base']):>10}{str(d['new']):>10}{delta:>10}")

    if result["flips"]:
        print(f"\n{len(result['flips'])} case(s) changed pass/fail:")
        for f in result["flips"]:
            arrow = "PASS->FAIL" if f["from"] else "FAIL->PASS"
            print(f"  {f['id']:<28}{arrow}  actual={f['actual']}")
    else:
        print("\nNo cases changed pass/fail.")
    return 0


if __name__ == "__main__":
    raise SystemExit(main())

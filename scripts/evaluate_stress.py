#!/usr/bin/env python3
"""Evaluate stressonnx against a small curated Russian stress corpus.

Run after installing requirements.txt:
    python scripts/evaluate_stress.py
The first run may download the neural model. This is an evaluation utility,
not a unit test: corpus coverage is deliberately small and does not establish
general-purpose stress accuracy.
"""
from __future__ import annotations

import json
from pathlib import Path

from main import _stress_index

ROOT = Path(__file__).resolve().parents[1]
CASES = json.loads(
    (ROOT / "data" / "stress_quality_cases.json").read_text(encoding="utf-8")
)


def main() -> None:
    try:
        from stressonnx import stress
    except ImportError as exc:
        raise SystemExit("stressonnx is not installed; install requirements.txt first") from exc

    correct = 0
    failures = []
    for case in CASES:
        word = case["word"]
        marked = stress(word, "ru", fallback=True)
        actual = _stress_index(marked)
        expected = case["expected_stress"]
        if actual == expected:
            correct += 1
        else:
            failures.append({
                "word": word,
                "expected_stress": expected,
                "actual_stress": actual,
                "marked": marked,
            })

    print(json.dumps({
        "cases": len(CASES),
        "correct": correct,
        "accuracy": round(correct / len(CASES), 4) if CASES else 1.0,
        "failures": failures,
        "scope": "curated isolated-word stress check; not a broad accuracy claim",
    }, ensure_ascii=False, indent=2))


if __name__ == "__main__":
    main()

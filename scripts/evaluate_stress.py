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
import sys
from pathlib import Path

ROOT = Path(__file__).resolve().parents[1]
# When executed as "python scripts/evaluate_stress.py", Python puts scripts/
# rather than the repository root on sys.path.
sys.path.insert(0, str(ROOT))

from main import _stress_index

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
        # _stress_index returns a one-based syllable number; the corpus stores
        # zero-based vowel indices, matching the rhyme API contract.
        marked_index = _stress_index(marked)
        actual = marked_index - 1 if marked_index is not None else None
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

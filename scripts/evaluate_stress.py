#!/usr/bin/env python3
"""Evaluate stressonnx and curated overrides against a Russian stress corpus.

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
OVERRIDE_DATA = json.loads(
    (ROOT / "data" / "stress_overrides.json").read_text(encoding="utf-8")
)
OVERRIDES = OVERRIDE_DATA["overrides"]


def main() -> None:
    try:
        from stressonnx import stress
    except ImportError as exc:
        raise SystemExit("stressonnx is not installed; install requirements.txt first") from exc

    model_correct = 0
    corrected_correct = 0
    model_failures = []
    corrected_failures = []

    for case in CASES:
        word = case["word"]
        marked = stress(word, "ru", fallback=True)
        # _stress_index returns a one-based syllable number; the corpus stores
        # zero-based vowel indices, matching the rhyme API contract.
        marked_index = _stress_index(marked)
        model_index = marked_index - 1 if marked_index is not None else None
        expected = case["expected_stress"]
        override = OVERRIDES.get(word, {}).get("stress")
        corrected_index = override if override is not None else model_index

        if model_index == expected:
            model_correct += 1
        else:
            model_failures.append({
                "word": word,
                "expected_stress": expected,
                "actual_stress": model_index,
                "marked": marked,
            })

        if corrected_index == expected:
            corrected_correct += 1
        else:
            corrected_failures.append({
                "word": word,
                "expected_stress": expected,
                "actual_stress": corrected_index,
                "model_stress": model_index,
                "marked": marked,
            })

    total = len(CASES)
    print(json.dumps({
        "cases": total,
        "model": {
            "correct": model_correct,
            "accuracy": round(model_correct / total, 4) if total else 1.0,
            "failures": model_failures,
        },
        "with_curated_overrides": {
            "correct": corrected_correct,
            "accuracy": round(corrected_correct / total, 4) if total else 1.0,
            "failures": corrected_failures,
            "override_count": len(OVERRIDES),
        },
        "scope": "curated isolated-word stress check; not a broad accuracy claim",
    }, ensure_ascii=False, indent=2))


if __name__ == "__main__":
    main()

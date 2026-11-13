#!/usr/bin/env python3
"""Run the curated exact/negative rhyme regression corpus and print metrics."""
from __future__ import annotations

import json
from pathlib import Path

from phonetic_rhyme import rhyme_key

ROOT = Path(__file__).resolve().parents[1]
CASES = json.loads((ROOT / "data" / "rhyme_quality_cases.json").read_text(encoding="utf-8"))


def classify(key_a: str, key_b: str) -> str:
    if key_a == key_b:
        return "exact"
    tail_a = ".".join(key_a.split(".")[-3:])
    tail_b = ".".join(key_b.split(".")[-3:])
    return "near" if tail_a and tail_a == tail_b else "none"


def main() -> None:
    correct = 0
    failures = []
    for case in CASES:
        key_a = str(rhyme_key(case["a"], stress=case["stress_a"]))
        key_b = str(rhyme_key(case["b"], stress=case["stress_b"]))
        actual = classify(key_a, key_b)
        correct += actual == case["expected"]
        if actual != case["expected"]:
            failures.append({
                "pair": f'{case["a"]} — {case["b"]}',
                "expected": case["expected"],
                "actual": actual,
                "key_a": key_a,
                "key_b": key_b,
            })
    print(json.dumps({
        "cases": len(CASES),
        "correct": correct,
        "accuracy": round(correct / len(CASES), 4) if CASES else 1.0,
        "failures": failures,
        "scope": "exact/near/none classification; explicit stress; curated regression set",
    }, ensure_ascii=False, indent=2))
    if failures:
        raise SystemExit(1)


if __name__ == "__main__":
    main()

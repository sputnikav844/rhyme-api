#!/usr/bin/env python3
"""Evaluate raw Russian stress predictions and curated lexical overrides.

Run after installing requirements.txt:
    python scripts/evaluate_stress.py

This is a curated regression evaluation, not a general-purpose accuracy claim.
The corpus distinguishes isolated unambiguous forms, contextual homographs and
unresolved ambiguous forms.
"""
from __future__ import annotations

import json
import sys
import unicodedata
from pathlib import Path

ROOT = Path(__file__).resolve().parents[1]
sys.path.insert(0, str(ROOT))

from main import (  # noqa: E402
    VOWELS,
    MARKED_WORD_RE,
    _apply_stress_overrides,
    _stress_index,
    _strip_marks,
)

CASES = json.loads(
    (ROOT / "data" / "stress_quality_cases.json").read_text(encoding="utf-8")
)
OVERRIDE_DATA = json.loads(
    (ROOT / "data" / "stress_overrides.json").read_text(encoding="utf-8")
)
OVERRIDES = OVERRIDE_DATA["overrides"]


def target_stress_index(marked_text: str, target: str) -> int | None:
    """Return the zero-based stressed-vowel index for the one target token."""
    target_key = _strip_marks(target)
    tokens = [
        token for token in MARKED_WORD_RE.findall(marked_text)
        if _strip_marks(token) == target_key
    ]
    if len(tokens) != 1:
        return None

    token = tokens[0]
    marked_index = _stress_index(token)
    if marked_index is not None:
        return marked_index - 1

    # In standard Russian spelling ё normally carries stress without an acute.
    # Count it only when the case explicitly declares that this ё is stressed.
    if any(case.get("word") == target and case.get("yo_is_stressed") for case in CASES):
        chars = unicodedata.normalize("NFD", token.lower())
        vowel_index = 0
        for char in chars:
            if char in VOWELS:
                if char == "ё":
                    return vowel_index
                vowel_index += 1
    return None


def validate_cases() -> None:
    if len(CASES) < 100:
        raise SystemExit(f"stress corpus must contain at least 100 cases; found {len(CASES)}")

    seen = set()
    for case in CASES:
        word = case["word"]
        context = case.get("context")
        if context:
            if sum(_strip_marks(token) == _strip_marks(word)
                   for token in MARKED_WORD_RE.findall(context)) != 1:
                raise SystemExit(f"context must contain target word exactly once: {word!r}")
        elif case.get("ambiguous") and not case.get("acceptable_stresses"):
            raise SystemExit(f"ambiguous isolated case needs acceptable_stresses: {word!r}")

        expected = case.get("expected_stress")
        if expected is not None:
            vowels = sum(char.lower() in VOWELS for char in word)
            if not isinstance(expected, int) or not 0 <= expected < vowels:
                raise SystemExit(f"invalid zero-based stress index for {word!r}: {expected!r}")
        if not case.get("ambiguous") and expected is None:
            raise SystemExit(f"unambiguous case needs expected_stress: {word!r}")
        seen.add((word, context))

    for word, item in OVERRIDES.items():
        if not item.get("reason") or not item.get("source"):
            raise SystemExit(f"override {word!r} must have reason and source")
        vowels = sum(char.lower() in VOWELS for char in word)
        if not isinstance(item.get("stress"), int) or not 0 <= item["stress"] < vowels:
            raise SystemExit(f"invalid override stress index for {word!r}")


def main() -> None:
    validate_cases()
    try:
        from stressonnx import stress
    except ImportError as exc:
        raise SystemExit("stressonnx is not installed; install requirements.txt first") from exc

    groups = {
        "isolated_unambiguous": [],
        "context_disambiguation": [],
        "ambiguous_variants": [],
    }

    for case in CASES:
        word = case["word"]
        text = case.get("context") or word
        raw_marked = stress(text, "ru", fallback=True)
        corrected_marked = _apply_stress_overrides(raw_marked)
        raw_index = target_stress_index(raw_marked, word)
        corrected_index = target_stress_index(corrected_marked, word)
        expected = case.get("expected_stress")

        if case.get("acceptable_stresses") is not None:
            allowed = case["acceptable_stresses"]
            groups["ambiguous_variants"].append({
                "word": word,
                "raw_prediction": raw_index,
                "corrected_prediction": corrected_index,
                "acceptable_stresses": allowed,
                "raw_accepted": raw_index in allowed,
                "corrected_accepted": corrected_index in allowed,
            })
        elif case.get("context"):
            groups["context_disambiguation"].append({
                "word": word,
                "context": text,
                "expected_stress": expected,
                "raw_prediction": raw_index,
                "corrected_prediction": corrected_index,
                "raw_correct": raw_index == expected,
                "corrected_correct": corrected_index == expected,
            })
        else:
            groups["isolated_unambiguous"].append({
                "word": word,
                "expected_stress": expected,
                "raw_prediction": raw_index,
                "corrected_prediction": corrected_index,
                "raw_correct": raw_index == expected,
                "corrected_correct": corrected_index == expected,
            })

    def summarize(items: list[dict], raw_key: str, corrected_key: str) -> dict:
        total = len(items)
        raw_correct = sum(bool(item[raw_key]) for item in items)
        corrected_correct = sum(bool(item[corrected_key]) for item in items)
        return {
            "cases": total,
            "raw_model": {
                "correct": raw_correct,
                "accuracy": round(raw_correct / total, 4) if total else None,
                "errors": [item for item in items if not item[raw_key]],
            },
            "model_plus_overrides": {
                "correct": corrected_correct,
                "accuracy": round(corrected_correct / total, 4) if total else None,
                "errors": [item for item in items if not item[corrected_key]],
            },
        }

    print(json.dumps({
        "isolated_unambiguous": summarize(
            groups["isolated_unambiguous"], "raw_correct", "corrected_correct"
        ),
        "context_disambiguation": summarize(
            groups["context_disambiguation"], "raw_correct", "corrected_correct"
        ),
        "ambiguous_variants": {
            "cases": len(groups["ambiguous_variants"]),
            "results": groups["ambiguous_variants"],
        },
        "override_count": len(OVERRIDES),
        "scope": "curated stress regression corpus; not general-purpose accuracy",
    }, ensure_ascii=False, indent=2))


if __name__ == "__main__":
    main()

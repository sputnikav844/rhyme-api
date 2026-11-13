"""Regression corpus for Russian phonetic rhyme quality.

Stress positions are explicit (zero-based vowel indices), isolating the
phonetic matcher from the optional neural stress model.
"""
import json
from pathlib import Path

from phonetic_rhyme import rhyme_key

CASES = json.loads(
    (Path(__file__).resolve().parents[1] / "data" / "rhyme_quality_cases.json").read_text(encoding="utf-8")
)

REQUIRED_CATEGORIES = {
    "exact_rhyme",
    "near_rhyme",
    "negative_control",
    "final_devoicing",
    "softness",
    "yo_e",
    "vowel_reduction",
    "consonant_clusters",
    "short_stressed_endings",
}


def classify(case):
    key_a = rhyme_key(case["a"], stress=case["stress_a"])
    key_b = rhyme_key(case["b"], stress=case["stress_b"])
    if key_a == key_b:
        return "exact"
    tail_a = ".".join(key_a.split(".")[-3:])
    tail_b = ".".join(key_b.split(".")[-3:])
    if tail_a and tail_a == tail_b:
        return "near"
    return "none"


def test_corpus_has_release_minimum_and_valid_annotations():
    assert len(CASES) >= 100, f"Expected at least 100 curated cases, got {len(CASES)}"
    for index, case in enumerate(CASES, start=1):
        assert case["expected"] in {"exact", "near", "none"}, f"Unsupported expected class in case {index}"
        assert case.get("reason", "").strip(), f"Missing explanation in case {index}"
        assert case.get("category") in REQUIRED_CATEGORIES, f"Missing/unknown category in case {index}"
        assert isinstance(case["stress_a"], int) and case["stress_a"] >= 0, f"Invalid stress_a in case {index}"
        assert isinstance(case["stress_b"], int) and case["stress_b"] >= 0, f"Invalid stress_b in case {index}"


def test_corpus_covers_all_release_phonetic_categories():
    covered = {case["category"] for case in CASES}
    missing = sorted(REQUIRED_CATEGORIES - covered)
    assert not missing, f"Missing required phonetic categories: {missing}"


def test_curated_rhyme_quality_corpus():
    failures = []
    for case in CASES:
        actual = classify(case)
        if actual != case["expected"]:
            failures.append({
                "pair": f'{case["a"]} — {case["b"]}',
                "expected": case["expected"],
                "actual": actual,
                "keys": [
                    rhyme_key(case["a"], stress=case["stress_a"]),
                    rhyme_key(case["b"], stress=case["stress_b"]),
                ],
                "reason": case["reason"],
                "category": case["category"],
            })
    assert not failures, json.dumps(failures, ensure_ascii=False, indent=2)

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
VOWELS = {"a", "o", "u", "i", "y", "e"}


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
        assert case["stress_a"] < sum(ch in "аеёиоуыэюя" for ch in case["a"]), f"stress_a out of range in case {index}"
        assert case["stress_b"] < sum(ch in "аеёиоуыэюя" for ch in case["b"]), f"stress_b out of range in case {index}"


def test_corpus_covers_all_release_phonetic_categories():
    covered = {case["category"] for case in CASES}
    missing = sorted(REQUIRED_CATEGORIES - covered)
    assert not missing, f"Missing required phonetic categories: {missing}"


def test_consonant_cluster_category_contains_real_post_stress_clusters():
    cluster_cases = [case for case in CASES if case["category"] == "consonant_clusters"]
    assert cluster_cases, "No consonant-cluster cases"
    def has_adjacent_consonants(word, stress):
        tokens = rhyme_key(word, stress=stress).split(".")
        return any(
            left not in VOWELS and right not in VOWELS
            for left, right in zip(tokens, tokens[1:])
        )
    assert any(
        has_adjacent_consonants(case["a"], case["stress_a"])
        or has_adjacent_consonants(case["b"], case["stress_b"])
        for case in cluster_cases
    ), "Consonant-cluster labels must be backed by actual adjacent consonants in the stressed tails"


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

def test_reviewed_stress_positions_for_known_words():
    # Russian lexical stress: мо́лодость is stressed on its first vowel.
    cases = [case for case in CASES if case["a"] == "молодость"]
    assert len(cases) >= 2
    assert all(case["stress_a"] == 0 for case in cases)
    original_reviewed_pairs = {
        case["b"] for case in cases if case["b"] in {"гордость", "скорость"}
    }
    assert original_reviewed_pairs == {"гордость", "скорость"}

    # Reviewed dictionary stress: о́блако has stress on its first vowel.
    cloud_cases = [case for case in CASES if case["a"] == "молоко" and case["b"] == "облако"]
    assert len(cloud_cases) == 1
    assert cloud_cases[0]["stress_b"] == 0


def test_named_phonetic_features_are_exercised_by_engine():
    # Final devoicing: both final voiced stops surface as /t/.
    assert rhyme_key("рад", stress=0) == "a.t"
    assert rhyme_key("брат", stress=0) == "a.t"

    # The ё / е contrast is phonemic under stress; ё maps to /o/, е to /e/.
    assert rhyme_key("лёд", stress=0) == "o.t"
    assert rhyme_key("лет", stress=0) == "e.t"

    # The engine preserves final consonant softness.
    assert rhyme_key("угол", stress=0) != rhyme_key("уголь", stress=0)

    # The documented -ого -> /ovo/ orthographic rule is actually exercised.
    assert rhyme_key("готова", stress=1) == "o.v.a"
    assert rhyme_key("какого", stress=1) == "o.v.a"

    # Post-vocalic consonant clusters remain part of the stressed tail.
    assert rhyme_key("волк", stress=0) == rhyme_key("толк", stress=0)
    assert rhyme_key("мост", stress=0) == rhyme_key("хвост", stress=0)


def test_near_rhyme_cases_are_distinct_from_exact_rhymes():
    near_cases = [case for case in CASES if case["category"] == "near_rhyme"]
    assert len(near_cases) >= 6
    for case in near_cases:
        key_a = rhyme_key(case["a"], stress=case["stress_a"])
        key_b = rhyme_key(case["b"], stress=case["stress_b"])
        assert key_a != key_b
        assert ".".join(key_a.split(".")[-3:]) == ".".join(key_b.split(".")[-3:])

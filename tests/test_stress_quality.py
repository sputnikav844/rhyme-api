import json
from collections import defaultdict
from pathlib import Path

from main import MARKED_WORD_RE, VOWELS, _strip_marks
from scripts.evaluate_stress import target_stress_index

ROOT = Path(__file__).resolve().parents[1]
CASES = json.loads((ROOT / "data" / "stress_quality_cases.json").read_text(encoding="utf-8"))
OVERRIDE_DATA = json.loads((ROOT / "data" / "stress_overrides.json").read_text(encoding="utf-8"))


def test_stress_corpus_has_at_least_100_unique_unambiguous_isolated_forms():
    isolated = [
        case for case in CASES
        if not case.get("context") and not case.get("ambiguous")
    ]
    assert len(isolated) >= 100
    assert len({case["word"] for case in isolated}) >= 100


def test_every_reference_stress_is_a_valid_zero_based_vowel_index():
    for case in CASES:
        assert case.get("source")
        expected = case.get("expected_stress")
        assert isinstance(expected, int)
        vowel_count = sum(char.lower() in VOWELS for char in case["word"])
        assert 0 <= expected < vowel_count


def test_context_homographs_are_explicitly_ambiguous_and_have_distinct_stresses():
    groups = defaultdict(list)
    for case in CASES:
        if case.get("context"):
            assert case.get("ambiguous") is True
            tokens = MARKED_WORD_RE.findall(case["context"])
            assert sum(_strip_marks(token) == _strip_marks(case["word"]) for token in tokens) == 1
            groups[case["ambiguity_group"]].append(case["expected_stress"])

    expected_groups = {
        "замок", "мука", "атлас", "орган", "ирис", "плачу",
        "трусы", "село", "дорога", "потом", "среда",
    }
    assert set(groups) == expected_groups
    assert all(len(set(stresses)) >= 2 for stresses in groups.values())


def test_ambiguous_homographs_are_not_given_word_level_overrides():
    ambiguous_words = {case["word"] for case in CASES if case.get("ambiguous")}
    assert not (ambiguous_words & set(OVERRIDE_DATA["overrides"]))


def test_yo_is_counted_as_stress_only_when_case_declares_it():
    assert target_stress_index("зелёный", "зелёный", yo_is_stressed=True) == 1
    assert target_stress_index("жёлтый", "жёлтый", yo_is_stressed=True) == 0
    assert target_stress_index("моло\u0301ко", "молоко") == 1

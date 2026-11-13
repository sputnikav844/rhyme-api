from main import _apply_stress_overrides, _stress_index


def test_curated_override_marks_nachalsya_on_final_syllable():
    marked = _apply_stress_overrides("начался")
    assert marked == "начался\u0301"
    assert _stress_index(marked) == 3


def test_override_replaces_model_stress_mark():
    # Existing model marks are removed before the reviewed dictionary entry
    # is applied, so the override wins even when the model chose another vowel.
    marked = _apply_stress_overrides("на\u0301чался")
    assert marked == "начался\u0301"
    assert _stress_index(marked) == 3


def test_words_without_override_are_not_rewritten():
    assert _apply_stress_overrides("молоко") == "молоко"


def test_override_preserves_model_stress_on_other_words():
    marked = _apply_stress_overrides("моло\u0301ко и на\u0301чался")
    assert marked == "моло\u0301ко и начался\u0301"


def test_override_preserves_all_non_overridden_word_marks():
    marked = _apply_stress_overrides("на\u0301чался, а моло\u0301ко осталось")
    assert marked == "начался\u0301, а моло\u0301ко осталось"

import gzip
import hashlib
import json

from fastapi.testclient import TestClient

import main
from scripts.build_phonetic_index import BUILD_ALGORITHM, build
from scripts.download_dictionary import SHA256


def test_index_build_is_byte_for_byte_deterministic_and_deduplicates(tmp_path):
    source = tmp_path / "words.txt.gz"
    with gzip.open(source, "wt", encoding="utf-8") as stream:
        stream.write("рад\nбрат\nрад\nкровь\nкровь\n")
    first = tmp_path / "first.json.gz"
    second = tmp_path / "second.json.gz"

    stats_a = build(source, first)
    stats_b = build(source, second)

    assert first.read_bytes() == second.read_bytes()
    assert stats_a["source_lines"] == 5
    assert stats_a["duplicate_entries"] == 2
    assert stats_a["indexed_wordforms"] == 3
    assert stats_a["wordlist_sha256"] == stats_b["wordlist_sha256"]

    with gzip.open(first, "rt", encoding="utf-8") as stream:
        index = json.load(stream)
    assert index["schema_version"] == 1
    assert index["build_algorithm"] == "sorted-unique-wordforms-gzip-mtime0-v1"
    assert index["unique_wordforms"] == 3
    assert index["indexed_wordforms"] == 3
    assert index["exact_key_count"] == len(index["exact"])
    assert index["near_bucket_count"] == len(index["near"])
    assert all(words == sorted(set(words)) for words in index["exact"].values())
    assert all(words == sorted(set(words)) for words in index["near"].values())


def test_search_deduplicates_orders_and_applies_limit_after_sort(monkeypatch):
    monkeypatch.setattr(main, "_phonetic_index", lambda: {
        "schema_version": 1,
        "indexed_wordforms": 4,
        "exact": {"x.a.b.c": ["рад", "брат", "кот", "брат"]},
        "near": {"a.b.c": ["срочно", "рад", "брат", "срочно"]},
    })
    keys = {
        "кот": "x.a.b.c",
        "брат": "x.a.b.c",
        "рад": "x.a.b.c",
        "срочно": "x.a.b.c",
    }
    monkeypatch.setattr(main, "_rhyme_key", lambda word, stress=None, **kwargs: keys[word])
    client = TestClient(main.app)

    response = client.post("/rhyme/search", json={"word": "кот", "strict": False, "limit": 2})
    assert response.status_code == 200
    body = response.json()
    assert body["source"] == "full_phonetic_index"
    assert body["total_matches"] == 3
    assert body["count"] == 2
    assert [item["word"] for item in body["results"]] == ["брат", "рад"]
    assert [item["match"] for item in body["results"]] == ["exact", "exact"]


def test_search_missing_index_uses_full_wordlist_fallback(monkeypatch):
    monkeypatch.setattr(main, "_phonetic_index", lambda: {})
    monkeypatch.setattr(main, "_wordlist", lambda: ("рад", "брат", "сад", "дом"))
    main._wordlist_suffix_index.cache_clear()
    monkeypatch.setattr(
        main, "_rhyme_key",
        lambda word, stress=None, **kwargs: "same.key" if word in {"рад", "брат"} else word,
    )
    try:
        client = TestClient(main.app)
        response = client.post("/rhyme/search", json={"word": "рад", "limit": 10})
        assert response.status_code == 200
        body = response.json()
        assert body["source"] == "full_wordlist_spelling_fallback"
        assert [item["word"] for item in body["results"]] == ["брат"]
    finally:
        main._wordlist_suffix_index.cache_clear()


def test_search_missing_index_and_full_dictionary_uses_seed_fallback(monkeypatch, tmp_path):
    seed = tmp_path / "seed.txt"
    seed.write_text("рад\nбрат\n", encoding="utf-8")
    monkeypatch.setattr(main, "_phonetic_index", lambda: {})
    monkeypatch.setattr(main, "FULL_WORDLIST_PATH", tmp_path / "missing.gz")
    monkeypatch.setattr(main, "WORDLIST_PATH", seed)
    main._wordlist.cache_clear()
    main._wordlist_suffix_index.cache_clear()
    monkeypatch.setattr(main, "_rhyme_key", lambda word, stress=None, **kwargs: "same.key")
    try:
        client = TestClient(main.app)
        response = client.post("/rhyme/search", json={"word": "рад"})
        assert response.status_code == 200
        assert response.json()["source"] == "bundled_seed_lexicon"
        assert [item["word"] for item in response.json()["results"]] == ["брат"]
    finally:
        main._wordlist.cache_clear()
        main._wordlist_suffix_index.cache_clear()


def test_ci_dictionary_archive_and_built_index_are_pinned_and_consistent():
    archive = main.FULL_WORDLIST_PATH
    if not archive.exists():
        import pytest
        pytest.skip("Full dictionary archive is downloaded in the CI build job")
    actual = hashlib.sha256(archive.read_bytes()).hexdigest()
    assert actual == SHA256
    main._phonetic_index.cache_clear()
    try:
        index = main._phonetic_index()
        assert index["wordlist_sha256"] == SHA256
        assert index["build_algorithm"] == BUILD_ALGORITHM
        assert index["indexed_wordforms"] == index["unique_wordforms"]
        assert index["exact_key_count"] == len(index["exact"])
        assert index["near_bucket_count"] == len(index["near"])
        assert index["duplicate_entries"] >= 0
        assert index["source_lines"] >= index["indexed_wordforms"]
    finally:
        main._phonetic_index.cache_clear()


def test_search_limit_validation_boundaries():
    client = TestClient(main.app)
    for limit in (0, 51):
        response = client.post("/rhyme/search", json={"word": "любовь", "limit": limit})
        assert response.status_code == 422

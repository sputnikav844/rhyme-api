from fastapi.testclient import TestClient
import main

client = TestClient(main.app)


def test_health():
    response = client.get("/health")
    assert response.status_code == 200
    assert response.json()["status"] == "ok"


def test_legacy_rhyme_contract():
    response = client.post("/rhyme", json={"word1": "рад", "word2": "брат"})
    assert response.status_code == 200
    body = response.json()
    assert {"word1", "word2", "key1", "key2", "rhymes"} <= body.keys()


def test_check_endpoint():
    response = client.post("/rhyme/check", json={"word1": "рад", "word2": "брат"})
    assert response.status_code == 200
    assert response.json()["classification"] in {"exact", "near", "none"}


def test_search_uses_supplied_candidates(monkeypatch):
    monkeypatch.setattr(main, "_rhyme_key", lambda word, stress=None, **kwargs: "test-key" if word in {"кот", "рот"} else word)
    response = client.post("/rhyme/search", json={
        "word": "кот", "candidates": ["рот", "дом", "кот"], "limit": 10
    })
    assert response.status_code == 200
    body = response.json()
    assert body["source"] == "request_candidates"
    assert any(item["word"] == "рот" for item in body["results"])


def test_lines_endpoint():
    response = client.post("/rhyme/check-lines", json={
        "lines": ["Я вижу свет", "И слышу ответ"]
    })
    assert response.status_code == 200
    assert len(response.json()["lines"]) == 2


def test_prosody_counts_syllables_without_stress_engine():
    response = client.post("/prosody/analyze", json={"text": "молоко и хлеб"})
    assert response.status_code == 200
    body = response.json()
    assert body["total_syllables"] == 5
    assert len(body["words"]) == 3


def test_search_rejects_multiword_target():
    response = client.post("/rhyme/search", json={"word": "добрый день"})
    assert response.status_code == 422


def test_rhyme_key_uses_model_stress_position(monkeypatch):
    captured = {}
    monkeypatch.setattr(main, "_mark_stress", lambda text: ("любо́вь", "test-model"))

    def fake_rhyme_key(word, stress=None):
        captured["word"] = word
        captured["stress"] = stress
        return "test-key"

    monkeypatch.setattr(main, "rhyme_key", fake_rhyme_key)
    assert main._rhyme_key("любовь") == "test-key"
    assert captured == {"word": "любовь", "stress": 1}


def test_explicit_stress_skips_model(monkeypatch):
    monkeypatch.setattr(main, "_mark_stress", lambda text: ("любо́вь", "test-model"))
    monkeypatch.setattr(main, "rhyme_key", lambda word, stress=None: str(stress))
    assert main._rhyme_key("любовь", stress=1) == "1"



def test_full_wordlist_loader_reads_gzip(tmp_path, monkeypatch):
    import gzip

    archive = tmp_path / "words.txt.gz"
    with gzip.open(archive, "wt", encoding="utf-8") as stream:
        stream.write("любовь\nответ\n# comment\n123\n")
    monkeypatch.setattr(main, "FULL_WORDLIST_PATH", archive)
    main._wordlist.cache_clear()
    try:
        assert main._wordlist() == ("любовь", "ответ")
    finally:
        main._wordlist.cache_clear()



def test_spelling_bucket_groups_final_voicing_pairs():
    assert main._spelling_bucket_key("рад") == main._spelling_bucket_key("брат")
    assert main._spelling_bucket_key("любовь") == main._spelling_bucket_key("кровь")



def test_stress_index_and_marked_word_regex():
    marked = "любо́вь"
    assert main._stress_index(marked) == 2
    assert [m.group(0) for m in main.MARKED_WORD_RE.finditer(marked)] == [marked]

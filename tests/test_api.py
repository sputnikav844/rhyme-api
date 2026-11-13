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
    monkeypatch.setattr(main, "_rhyme_key", lambda word, stress=None: "test-key" if word in {"кот", "рот"} else word)
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

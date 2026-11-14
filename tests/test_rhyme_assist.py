from fastapi.testclient import TestClient

import main


client = TestClient(main.app)


def test_rhyme_assist_natural_mode_uses_relaxed_search(monkeypatch):
    captured = {}

    def fake_search(data):
        captured["strict"] = data.strict
        captured["limit"] = data.limit
        return {
            "word": "любовь",
            "rhyme_key": "test",
            "total_matches": 3,
            "results": [
                {"word": "кровь", "match": "exact", "syllables": 1},
                {"word": "вновь", "match": "near", "syllables": 1},
                {"word": "морковь", "match": "near", "syllables": 2},
            ],
            "source": "test_index",
            "limitations": ["phonetic only"],
        }

    monkeypatch.setattr(main, "search_rhymes", fake_search)
    response = client.post("/rhyme/assist", json={
        "word": "любовь", "mode": "natural", "limit": 7, "syllables": 1
    })

    assert response.status_code == 200
    body = response.json()
    assert captured == {"strict": False, "limit": 50}
    assert body["mode"] == "natural"
    assert [item["word"] for item in body["results"]] == ["кровь", "вновь"]
    assert "грамматическую уместность" in body["guidance"][0]


def test_rhyme_assist_exact_mode_uses_strict_search(monkeypatch):
    captured = {}

    def fake_search(data):
        captured["strict"] = data.strict
        return {
            "word": "кот", "rhyme_key": "k", "total_matches": 1,
            "results": [{"word": "рот", "match": "exact", "syllables": 1}],
            "source": "test_index", "limitations": [],
        }

    monkeypatch.setattr(main, "search_rhymes", fake_search)
    response = client.post("/rhyme/assist", json={"word": "кот", "mode": "exact"})

    assert response.status_code == 200
    assert captured["strict"] is True
    assert response.json()["results"][0]["match"] == "exact"


def test_rhyme_assist_free_mode_does_not_search(monkeypatch):
    def fail_if_called(_data):
        raise AssertionError("free mode must not call rhyme search")

    monkeypatch.setattr(main, "search_rhymes", fail_if_called)
    response = client.post("/rhyme/assist", json={"word": "дорога", "mode": "free"})

    assert response.status_code == 200
    body = response.json()
    assert body["status"] == "skipped"
    assert body["results"] == []
    assert any("Рифма необязательна" in item for item in body["guidance"])


def test_rhyme_assist_validates_mode_and_word():
    assert client.post("/rhyme/assist", json={"word": "добрый день"}).status_code == 422
    assert client.post("/rhyme/assist", json={"word": "кот", "mode": "forced"}).status_code == 422
    assert client.post("/rhyme/assist", json={"word": "кот", "syllables": 0}).status_code == 422

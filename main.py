"""Russian rhyme API.

The legacy POST /rhyme contract is kept intact. New endpoints add lexical search,
line checks and prosody analysis. Stress inference is optional at runtime and is
never presented as certain when the model cannot resolve a word.
"""
from __future__ import annotations

import gzip
import json
import os
import re
import unicodedata
from functools import lru_cache
from pathlib import Path
from typing import Literal

from fastapi import FastAPI, HTTPException
from pydantic import BaseModel, Field
from phonetic_rhyme import do_rhyme, rhyme_key

APP_DIR = Path(__file__).resolve().parent
WORDLIST_PATH = Path(os.getenv("RHYME_WORDLIST", APP_DIR / "data" / "rhyme_words.txt"))
FULL_WORDLIST_PATH = Path(os.getenv("RHYME_FULL_WORDLIST", APP_DIR / "data" / "ru_RU.txt.gz"))
PHONETIC_INDEX_PATH = Path(os.getenv("RHYME_PHONETIC_INDEX", APP_DIR / "data" / "phonetic_index.json.gz"))
STRESS_OVERRIDES_PATH = Path(os.getenv("RHYME_STRESS_OVERRIDES", APP_DIR / "data" / "stress_overrides.json"))
VOWELS = "аеёиоуыэюя"
WORD_RE = re.compile(r"[а-яё]+", re.IGNORECASE)
MARKED_WORD_RE = re.compile(r"(?:[а-яё]\u0301?)+", re.IGNORECASE)

app = FastAPI(
    title="Russian Rhyme API",
    version="2.0.0",
    description="Phonetic rhyme search, pair and line checks, and syllable/stress analysis.",
)


class RhymeRequest(BaseModel):
    word1: str = Field(min_length=1, max_length=100)
    word2: str = Field(min_length=1, max_length=100)
    stress1: int | None = Field(default=None, ge=0)
    stress2: int | None = Field(default=None, ge=0)


class LegacyRhymeRequest(BaseModel):
    """Original /rhyme input schema retained for existing integrations."""
    word1: str
    word2: str
    stress1: int | None = None
    stress2: int | None = None


class SearchRequest(BaseModel):
    word: str = Field(min_length=1, max_length=100)
    limit: int = Field(default=10, ge=1, le=50)
    candidates: list[str] | None = Field(default=None, max_length=5000)
    stress: int | None = Field(default=None, ge=0)
    strict: bool = True


class LinesRequest(BaseModel):
    lines: list[str] = Field(min_length=2, max_length=16)
    strict: bool = True


class ProsodyRequest(BaseModel):
    text: str = Field(min_length=1, max_length=5000)


def _clean_word(word: str) -> str:
    found = WORD_RE.findall(word.lower().replace("ё", "ё"))
    if len(found) != 1:
        raise HTTPException(status_code=422, detail="Ожидается одно русское слово.")
    return found[0]


@lru_cache(maxsize=1)
def _stress_overrides() -> dict[str, int]:
    """Load curated zero-based stress positions; an absent file is harmless."""
    if not STRESS_OVERRIDES_PATH.exists():
        return {}
    payload = json.loads(STRESS_OVERRIDES_PATH.read_text(encoding="utf-8"))
    if payload.get("schema_version") != 1 or payload.get("index_base") != 0:
        raise RuntimeError("Unsupported stress override schema")
    result = {}
    for word, item in payload.get("overrides", {}).items():
        position = item.get("stress")
        if isinstance(position, int) and position >= 0:
            result[word.lower()] = position
    return result


def _mark_word_with_stress(word: str, stress_position: int) -> str:
    """Add a combining acute accent after the selected zero-based vowel."""
    chars = list(word)
    vowel_index = 0
    for index, char in enumerate(chars):
        if char.lower() in VOWELS:
            if vowel_index == stress_position:
                return "".join(chars[:index + 1]) + "\u0301" + "".join(chars[index + 1:])
            vowel_index += 1
    return word


def _apply_stress_overrides(text: str) -> str:
    overrides = _stress_overrides()
    if not overrides:
        return text
    # Remove model accents before token replacement so combining marks do not
    # split a word into multiple regex matches.
    unmarked = text.replace("\u0301", "")

    def replace(match: re.Match[str]) -> str:
        word = match.group(0)
        position = overrides.get(word.lower())
        return _mark_word_with_stress(word, position) if position is not None else word

    return WORD_RE.sub(replace, unmarked)


def _mark_stress(text: str) -> tuple[str, str]:
    """Return marked text and provider status; apply reviewed lexical overrides."""
    try:
        from stressonnx import stress
        marked = stress(text, "ru", fallback=True)
        return _apply_stress_overrides(marked), "stressonnx+lexicon"
    except ImportError:
        return _apply_stress_overrides(text), "lexicon" if _stress_overrides() else "unavailable"
    except Exception:
        return _apply_stress_overrides(text), "lexicon" if _stress_overrides() else "error"


def _stress_package_available() -> bool:
    try:
        import importlib.util
        return importlib.util.find_spec("stressonnx") is not None
    except (ImportError, ValueError):
        return False


def _strip_marks(word: str) -> str:
    return "".join(c for c in unicodedata.normalize("NFD", word.lower())
                   if unicodedata.category(c) != "Mn")


def _syllables(word: str) -> int:
    return sum(ch in VOWELS for ch in _strip_marks(word))


def _stress_index(marked_word: str) -> int | None:
    normalized = unicodedata.normalize("NFD", marked_word.lower())
    for i, char in enumerate(normalized):
        if char in VOWELS and i + 1 < len(normalized) and unicodedata.category(normalized[i + 1]) == "Mn":
            return sum(c in VOWELS for c in normalized[:i + 1])
    return None


def _last_word(text: str) -> str | None:
    words = WORD_RE.findall(text.lower())
    return words[-1] if words else None


@lru_cache(maxsize=1)
def _wordlist() -> tuple[str, ...]:
    """Load the verified full word-form list, falling back to the tiny seed list."""
    values: list[str] = []
    if FULL_WORDLIST_PATH.exists():
        with gzip.open(FULL_WORDLIST_PATH, "rt", encoding="utf-8", errors="ignore") as source:
            for line in source:
                word = line.strip().lower()
                if word and WORD_RE.fullmatch(word):
                    values.append(word)
    elif WORDLIST_PATH.exists():
        for line in WORDLIST_PATH.read_text(encoding="utf-8").splitlines():
            word = line.strip().lower()
            if word and not word.startswith("#") and WORD_RE.fullmatch(word):
                values.append(word)
    return tuple(dict.fromkeys(values))


_FINAL_SOUND = {
    "б": "п", "п": "п", "д": "т", "т": "т", "г": "к", "к": "к",
    "з": "с", "с": "с", "ж": "ш", "ш": "ш", "в": "ф", "ф": "ф",
}


def _spelling_bucket_key(word: str) -> str:
    cleaned = word.rstrip("ьъ")
    if not cleaned:
        return ""
    ending = cleaned[-2:]
    if ending:
        ending = ending[:-1] + _FINAL_SOUND.get(ending[-1], ending[-1])
    return ending


@lru_cache(maxsize=1)
def _wordlist_suffix_index() -> dict[str, tuple[str, ...]]:
    buckets: dict[str, list[str]] = {}
    for word in _wordlist():
        key = _spelling_bucket_key(word)
        if key:
            buckets.setdefault(key, []).append(word)
    return {key: tuple(words) for key, words in buckets.items()}

@lru_cache(maxsize=1)
def _phonetic_index() -> dict:
    """Load the offline-built phonetic index without doing work at startup."""
    if not PHONETIC_INDEX_PATH.exists():
        return {}
    with gzip.open(PHONETIC_INDEX_PATH, "rt", encoding="utf-8") as source:
        index = json.load(source)
    if index.get("schema_version") != 1:
        raise RuntimeError("Unsupported phonetic index schema version")
    return index


def _phonetic_tail(key: str, size: int = 3) -> str:
    parts = [part for part in key.split(".") if part]
    return ".".join(parts[-size:]) if parts else ""


def _classify_rhyme_keys(key_a: str, key_b: str, *, allow_near: bool = True) -> str:
    """Use one phonetic-key classifier across pair and line endpoints."""
    if key_a == key_b:
        return "exact"
    if allow_near and _phonetic_tail(key_a) and _phonetic_tail(key_a) == _phonetic_tail(key_b):
        return "near"
    return "none"


def _rhyme_key(word: str, stress: int | None = None, *, infer: bool = True) -> str:
    # Prefer a model-inferred stress position; otherwise the phonetic library
    # falls back to its documented heuristic (last vowel / small exception list).
    resolved_stress = stress
    if resolved_stress is None and infer:
        marked, _engine = _mark_stress(word)
        marked_index = _stress_index(marked)
        if marked_index is not None:
            resolved_stress = marked_index - 1  # phonetic-rhyme uses zero-based vowel indices
    return str(rhyme_key(word, stress=resolved_stress))


@app.get("/")
def home():
    return {"status": "ok", "service": "Russian Rhyme API", "version": app.version}


@app.get("/health")
def health():
    # Liveness checks must not download or initialize a neural model.
    available = _stress_package_available()
    return {
        "status": "ok",
        "version": app.version,
        "stress_engine": "installed" if available else "unavailable",
        "wordlist_available": FULL_WORDLIST_PATH.exists() or WORDLIST_PATH.exists(),
        "stress_engine_ready": available,
        "stress_engine_note": "Модель загружается при первом запросе анализа ударений.",
    }


@app.post("/rhyme")
def check_rhyme(data: LegacyRhymeRequest):
    """Backward-compatible endpoint used by n8n V28."""
    # Preserve the original endpoint's key generation (no model-inferred stress):
    key1 = str(rhyme_key(data.word1, stress=data.stress1))
    key2 = str(rhyme_key(data.word2, stress=data.stress2))
    # Preserve the original endpoint semantics used by existing clients:
    # the boolean is produced by phonetic-rhyme's do_rhyme, not key equality.
    result = do_rhyme(data.word1, data.word2, data.stress1, data.stress2)
    return {
        "word1": data.word1,
        "word2": data.word2,
        "key1": key1,
        "key2": key2,
        "rhymes": result,
    }


@app.post("/rhyme/check")
def check_pair(data: RhymeRequest):
    # New endpoint uses model-aware stress; legacy /rhyme remains independent.
    key1 = _rhyme_key(data.word1, data.stress1)
    key2 = _rhyme_key(data.word2, data.stress2)
    classification = _classify_rhyme_keys(key1, key2)
    return {
        "word1": data.word1,
        "word2": data.word2,
        "key1": key1,
        "key2": key2,
        "rhymes": classification == "exact",
        "classification": classification,
        "confidence": "phonetic-engine",
        "note": "Фонетическая оценка не определяет смысловую и художественную уместность.",
    }


@app.post("/rhyme/search")
def search_rhymes(data: SearchRequest):
    target = _clean_word(data.word)
    target_key = _rhyme_key(target, data.stress)
    index = _phonetic_index() if data.candidates is None else {}
    if data.candidates is not None:
        pool = data.candidates
        source = "request_candidates"
    elif index:
        exact_pool = index.get("exact", {}).get(target_key, [])
        near_pool = [] if data.strict else index.get("near", {}).get(_phonetic_tail(target_key), [])
        pool = list(dict.fromkeys([*exact_pool, *near_pool]))
        source = "full_phonetic_index"
    else:
        pool = _wordlist_suffix_index().get(_spelling_bucket_key(target), ())
        source = "full_wordlist_spelling_fallback" if FULL_WORDLIST_PATH.exists() else "bundled_seed_lexicon"

    results = []
    seen = {target}
    for raw in pool:
        try:
            candidate = _clean_word(raw)
        except HTTPException:
            continue
        if candidate in seen:
            continue
        seen.add(candidate)
        try:
            key = _rhyme_key(candidate, infer=False)
            exact = key == target_key
            near = not exact and not data.strict and _phonetic_tail(key) == _phonetic_tail(target_key)
            if exact or near:
                results.append({
                    "word": candidate,
                    "rhyme_key": key,
                    "match": "exact" if exact else "near",
                    "syllables": _syllables(candidate),
                })
        except Exception:
            continue
    results.sort(key=lambda item: (item["match"] != "exact", item["syllables"], item["word"]))
    return {
        "word": target,
        "rhyme_key": target_key,
        "count": min(len(results), data.limit),
        "total_matches": len(results),
        "results": results[:data.limit],
        "source": source,
        "dictionary_size": len(pool),
        "index_stats": {
            "indexed_wordforms": index.get("indexed_wordforms") if index else None,
            "phonetic_keys": len(index.get("exact", {})) if index else None,
        },
        "limitations": [
            "Полный фонетический индекс строится отдельной командой; при его отсутствии используется резервная буквенная индексация.",
            "Ударение словаря построено по эвристике phonetic-rhyme; неоднозначные слова требуют явного ударения или проверки моделью.",
            "Фонетическое совпадение не гарантирует грамматическую или смысловую уместность.",
        ],
    }

@app.post("/rhyme/check-lines")
def check_lines(data: LinesRequest):
    details = []
    for line in data.lines:
        last = _last_word(line)
        if not last:
            details.append({"line": line, "ending": None, "error": "Не найдено слово в конце строки"})
            continue
        marked, engine = _mark_stress(line)
        marked_words = MARKED_WORD_RE.findall(marked)
        marked_ending = marked_words[-1] if marked_words else last
        marked_stress = _stress_index(marked_ending)
        ending_stress = marked_stress - 1 if marked_stress is not None else None
        details.append({
            "line": line,
            "ending": last,
            "marked_line": marked,
            "stress_engine": engine,
            "rhyme_key": _rhyme_key(last, stress=ending_stress),
            "syllables": _syllables(line),
        })
    pairs = []
    for i in range(len(details)):
        for j in range(i + 1, len(details)):
            a, b = details[i], details[j]
            if a["ending"] and b["ending"]:
                ka, kb = a["rhyme_key"], b["rhyme_key"]
                pairs.append({
                    "line_a": i + 1, "line_b": j + 1,
                    "word_a": a["ending"], "word_b": b["ending"],
                    "classification": _classify_rhyme_keys(ka, kb, allow_near=not data.strict),
                })
    return {
        "lines": details,
        "pairs": pairs,
        "warning": "Проверяются последние слова строк; внутренние и составные рифмы требуют отдельной интерпретации.",
    }


@app.post("/prosody/analyze")
def analyze_prosody(data: ProsodyRequest):
    marked, engine = _mark_stress(data.text)
    words = []
    for match in MARKED_WORD_RE.finditer(marked):
        token = match.group(0)
        words.append({
            "word": token,
            "syllables": _syllables(token),
            "stressed_syllable": _stress_index(token),
        })
    return {
        "text": data.text,
        "marked_text": marked,
        "stress_engine": engine,
        "total_syllables": sum(item["syllables"] for item in words),
        "words": words,
        "stress_note": None if engine == "stressonnx" else "Движок ударений недоступен: позиции ударений не определены.",
    }

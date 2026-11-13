#!/usr/bin/env python3
"""Build a deterministic phonetic rhyme index from the pinned Russian wordlist.

Candidate stress uses phonetic-rhyme's documented fallback (heuristic / exception
list). Target words may use stressonnx at query time. The index is generated
offline and is never built during API startup.
"""
from __future__ import annotations

import argparse
import gzip
import hashlib
import json
import os
import tempfile
from collections import defaultdict
from pathlib import Path

from phonetic_rhyme import rhyme_key

ROOT = Path(__file__).resolve().parents[1]
DEFAULT_WORDLIST = ROOT / "data" / "ru_RU.txt.gz"
DEFAULT_OUTPUT = ROOT / "data" / "phonetic_index.json.gz"
VOWELS = set("аеёиоуыэюя")


def normalize_key(key: str) -> str:
    return ".".join(part for part in key.split(".") if part)


def tail_key(key: str, size: int = 3) -> str:
    parts = normalize_key(key).split(".")
    return ".".join(parts[-size:]) if parts else ""


def build(wordlist: Path, output: Path) -> dict:
    exact: dict[str, list[str]] = defaultdict(list)
    near: dict[str, list[str]] = defaultdict(list)
    count = 0
    with gzip.open(wordlist, "rt", encoding="utf-8", errors="ignore") as stream:
        for line in stream:
            word = line.strip().lower()
            if not word or any(ch not in "абвгдеёжзийклмнопрстуфхцчшщъыьэюя" for ch in word):
                continue
            if not any(ch in VOWELS for ch in word):
                continue
            try:
                key = normalize_key(str(rhyme_key(word)))
            except Exception:
                continue
            if not key:
                continue
            exact[key].append(word)
            near[tail_key(key)].append(word)
            count += 1

    payload = {
        "schema_version": 1,
        "wordlist_sha256": hashlib.sha256(wordlist.read_bytes()).hexdigest(),
        "stress_mode": "phonetic-rhyme-default-heuristic",
        "tail_phonemes": 3,
        "indexed_wordforms": count,
        "exact": dict(exact),
        "near": dict(near),
    }
    output.parent.mkdir(parents=True, exist_ok=True)
    fd, temp_name = tempfile.mkstemp(prefix=output.name, dir=output.parent)
    os.close(fd)
    try:
        with gzip.open(temp_name, "wt", encoding="utf-8", compresslevel=9) as target:
            json.dump(payload, target, ensure_ascii=False, separators=(",", ":"))
        os.replace(temp_name, output)
    finally:
        if os.path.exists(temp_name):
            os.unlink(temp_name)
    return {"indexed_wordforms": count, "exact_keys": len(exact), "near_keys": len(near), "output": str(output)}


def main() -> None:
    parser = argparse.ArgumentParser(description=__doc__)
    parser.add_argument("--wordlist", type=Path, default=DEFAULT_WORDLIST)
    parser.add_argument("--output", type=Path, default=DEFAULT_OUTPUT)
    args = parser.parse_args()
    if not args.wordlist.exists():
        raise SystemExit(f"Wordlist not found: {args.wordlist}. Run scripts/download_dictionary.py first.")
    print(json.dumps(build(args.wordlist, args.output), ensure_ascii=False))


if __name__ == "__main__":
    main()

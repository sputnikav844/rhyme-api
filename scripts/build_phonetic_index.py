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
import io
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
BUILD_ALGORITHM = "sorted-unique-wordforms-gzip-mtime0-v1"


def normalize_key(key: str) -> str:
    return ".".join(part for part in key.split(".") if part)


def tail_key(key: str, size: int = 3) -> str:
    parts = normalize_key(key).split(".")
    return ".".join(parts[-size:]) if parts else ""


def build(wordlist: Path, output: Path) -> dict:
    exact: dict[str, set[str]] = defaultdict(set)
    near: dict[str, set[str]] = defaultdict(set)
    seen: set[str] = set()
    source_lines = 0
    duplicate_entries = 0
    invalid_entries = 0
    key_failures = 0
    with gzip.open(wordlist, "rt", encoding="utf-8", errors="ignore") as stream:
        for line in stream:
            source_lines += 1
            word = line.strip().lower()
            if not word or any(ch not in "абвгдеёжзийклмнопрстуфхцчшщъыьэюя" for ch in word):
                invalid_entries += 1
                continue
            if not any(ch in VOWELS for ch in word):
                invalid_entries += 1
                continue
            if word in seen:
                duplicate_entries += 1
                continue
            seen.add(word)
            try:
                key = normalize_key(str(rhyme_key(word)))
            except Exception:
                key_failures += 1
                continue
            if not key:
                key_failures += 1
                continue
            exact[key].add(word)
            near[tail_key(key)].add(word)

    exact_index = {key: sorted(words) for key, words in sorted(exact.items())}
    near_index = {key: sorted(words) for key, words in sorted(near.items())}
    unique_wordforms = sum(len(words) for words in exact_index.values())
    payload = {
        "schema_version": 1,
        "build_algorithm": BUILD_ALGORITHM,
        "wordlist_sha256": hashlib.sha256(wordlist.read_bytes()).hexdigest(),
        "source_lines": source_lines,
        "duplicate_entries": duplicate_entries,
        "invalid_entries": invalid_entries,
        "key_failures": key_failures,
        "skipped_entries": invalid_entries + key_failures,
        "stress_mode": "phonetic-rhyme-default-heuristic",
        "tail_phonemes": 3,
        "indexed_wordforms": unique_wordforms,
        "unique_wordforms": unique_wordforms,
        "exact_key_count": len(exact_index),
        "near_bucket_count": len(near_index),
        "max_exact_bucket_size": max((len(v) for v in exact_index.values()), default=0),
        "max_near_bucket_size": max((len(v) for v in near_index.values()), default=0),
        "exact": exact_index,
        "near": near_index,
    }
    output.parent.mkdir(parents=True, exist_ok=True)
    fd, temp_name = tempfile.mkstemp(prefix=output.name, dir=output.parent)
    os.close(fd)
    try:
        # Fix gzip mtime and filename so identical inputs produce identical bytes.
        with open(temp_name, "wb") as raw:
            with gzip.GzipFile(filename="", mode="wb", fileobj=raw, compresslevel=9, mtime=0) as compressed:
                with io.TextIOWrapper(compressed, encoding="utf-8", newline="") as target:
                    json.dump(payload, target, ensure_ascii=False, separators=(",", ":"))
        os.replace(temp_name, output)
    finally:
        if os.path.exists(temp_name):
            os.unlink(temp_name)
    return {
        "source_lines": source_lines,
        "duplicate_entries": duplicate_entries,
        "invalid_entries": invalid_entries,
        "key_failures": key_failures,
        "skipped_entries": invalid_entries + key_failures,
        "indexed_wordforms": unique_wordforms,
        "exact_keys": len(exact_index),
        "near_keys": len(near_index),
        "max_exact_bucket_size": payload["max_exact_bucket_size"],
        "max_near_bucket_size": payload["max_near_bucket_size"],
        "wordlist_sha256": payload["wordlist_sha256"],
        "output": str(output),
    }


def main() -> None:
    parser = argparse.ArgumentParser(description=__doc__)
    parser.add_argument("--wordlist", type=Path, default=DEFAULT_WORDLIST)
    parser.add_argument("--output", type=Path, default=DEFAULT_OUTPUT)
    args = parser.parse_args()
    if not args.wordlist.exists():
        raise SystemExit(f"Wordlist not found: {args.wordlist}. Run scripts/download_dictionary.py first.")
    print(json.dumps(build(args.wordlist, args.output), ensure_ascii=False, sort_keys=True))


if __name__ == "__main__":
    main()

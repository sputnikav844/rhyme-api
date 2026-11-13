#!/usr/bin/env python3
"""Download the pinned Russian Hunspell-derived word-form list.

Source: Goudron/ru-spelling-dictionary release v1.0.9.
The source publishes the CSpell list under MPL-2.0.
"""
from __future__ import annotations

import hashlib
import urllib.request
from pathlib import Path

URL = "https://github.com/Goudron/ru-spelling-dictionary/releases/download/v1.0.9/ru_RU.txt.gz"
SHA256 = "8ac7fbc26204d437d3e8be8609ba6a6e2a0afae17548cdfa0ff01c13de55e3fa"
DEST = Path(__file__).resolve().parents[1] / "data" / "ru_RU.txt.gz"


def main() -> None:
    DEST.parent.mkdir(parents=True, exist_ok=True)
    request = urllib.request.Request(URL, headers={"User-Agent": "rhyme-api-dictionary-fetch/1.0"})
    with urllib.request.urlopen(request, timeout=60) as response:
        payload = response.read()
    actual = hashlib.sha256(payload).hexdigest()
    if actual != SHA256:
        raise SystemExit(f"Dictionary checksum mismatch: expected {SHA256}, got {actual}")
    DEST.write_bytes(payload)
    print(f"Downloaded verified dictionary: {DEST} ({len(payload)} bytes)")


if __name__ == "__main__":
    main()

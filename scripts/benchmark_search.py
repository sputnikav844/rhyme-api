#!/usr/bin/env python3
"""Measure cold index load and warm common-query latency on the current runner."""
from __future__ import annotations

import argparse
import json
import math
import time

from fastapi.testclient import TestClient

from main import app


QUERIES = ("любовь", "рад", "молоко", "дом", "свет")


def percentile(values: list[float], fraction: float) -> float:
    ordered = sorted(values)
    return ordered[max(0, math.ceil(fraction * len(ordered)) - 1)]


def main() -> None:
    parser = argparse.ArgumentParser(description=__doc__)
    parser.add_argument("--iterations", type=int, default=5)
    parser.add_argument("--max-warm-p95-ms", type=float, default=1000.0)
    args = parser.parse_args()
    if args.iterations < 1:
        raise SystemExit("--iterations must be at least 1")

    client = TestClient(app)
    started = time.perf_counter()
    first = client.post("/rhyme/search", json={"word": QUERIES[0], "limit": 10})
    cold_ms = (time.perf_counter() - started) * 1000
    if first.status_code != 200:
        raise SystemExit(f"Cold query failed: {first.status_code} {first.text}")

    for word in QUERIES:
        response = client.post("/rhyme/search", json={"word": word, "limit": 10})
        if response.status_code != 200:
            raise SystemExit(f"Warm-up query {word!r} failed: {response.status_code}")

    timings = []
    for _ in range(args.iterations):
        for word in QUERIES:
            started = time.perf_counter()
            response = client.post("/rhyme/search", json={"word": word, "limit": 10})
            elapsed = (time.perf_counter() - started) * 1000
            if response.status_code != 200:
                raise SystemExit(f"Query {word!r} failed: {response.status_code}")
            timings.append(elapsed)

    report = {
        "runner": "GitHub Actions ubuntu-latest",
        "queries": list(QUERIES),
        "warm_samples": len(timings),
        "cold_first_query_ms": round(cold_ms, 2),
        "warm_median_ms": round(percentile(timings, 0.50), 2),
        "warm_p95_ms": round(percentile(timings, 0.95), 2),
        "warm_max_ms": round(max(timings), 2),
        "threshold_warm_p95_ms": args.max_warm_p95_ms,
    }
    print(json.dumps(report, ensure_ascii=False, indent=2))
    if report["warm_p95_ms"] > args.max_warm_p95_ms:
        raise SystemExit("Warm search latency exceeded the documented CI threshold")


if __name__ == "__main__":
    main()

#!/usr/bin/env python3
"""Summarize newline-delimited JSON records from headless game runs.

Required fields per line: seed, won, reached_stage.
Optional numeric fields: score, duration_seconds.
"""

from __future__ import annotations

import argparse
import json
import math
import statistics
import sys
from collections import Counter
from pathlib import Path


def percentile(values: list[float], fraction: float) -> float:
    if not values:
        return 0.0
    ordered = sorted(values)
    position = fraction * (len(ordered) - 1)
    low = math.floor(position)
    high = math.ceil(position)
    if low == high:
        return ordered[low]
    return ordered[low] + (ordered[high] - ordered[low]) * (position - low)


def read_records(path: Path) -> list[dict]:
    records: list[dict] = []
    with path.open("r", encoding="utf-8") as handle:
        for line_number, line in enumerate(handle, 1):
            if not line.strip():
                continue
            try:
                record = json.loads(line)
            except json.JSONDecodeError as error:
                raise ValueError(f"{path}:{line_number}: invalid JSON: {error}") from error
            for field in ("seed", "won", "reached_stage"):
                if field not in record:
                    raise ValueError(f"{path}:{line_number}: missing required field {field!r}")
            if not isinstance(record["won"], bool):
                raise ValueError(f"{path}:{line_number}: 'won' must be true or false")
            records.append(record)
    if not records:
        raise ValueError(f"{path}: no run records")
    return records


def numeric(records: list[dict], field: str) -> list[float]:
    return [float(record[field]) for record in records if isinstance(record.get(field), (int, float))]


def summary(records: list[dict]) -> dict:
    stages = numeric(records, "reached_stage")
    scores = numeric(records, "score")
    durations = numeric(records, "duration_seconds")
    failures = Counter(str(record.get("failure_reason", "unspecified")) for record in records if not record["won"])
    wins = sum(1 for record in records if record["won"])
    result = {
        "runs": len(records),
        "wins": wins,
        "losses": len(records) - wins,
        "win_rate": wins / len(records),
        "reached_stage": {
            "mean": statistics.fmean(stages),
            "median": statistics.median(stages),
            "p10": percentile(stages, 0.10),
            "p90": percentile(stages, 0.90),
            "max": max(stages),
        },
        "failure_reasons": dict(sorted(failures.items())),
    }
    if scores:
        result["score"] = {"mean": statistics.fmean(scores), "median": statistics.median(scores), "p90": percentile(scores, 0.90)}
    if durations:
        result["duration_seconds"] = {"mean": statistics.fmean(durations), "median": statistics.median(durations)}
    return result


def main() -> int:
    parser = argparse.ArgumentParser(description=__doc__)
    parser.add_argument("jsonl", type=Path, help="Path to newline-delimited run records")
    parser.add_argument("--compact", action="store_true", help="Emit compact JSON")
    args = parser.parse_args()
    try:
        records = read_records(args.jsonl)
    except (OSError, ValueError) as error:
        print(error, file=sys.stderr)
        return 2
    print(json.dumps(summary(records), indent=None if args.compact else 2, sort_keys=True))
    return 0


if __name__ == "__main__":
    raise SystemExit(main())

#!/usr/bin/env python3
"""Run and persist the automated Głodne Cienie playtest matrix."""

from __future__ import annotations

import argparse
import csv
import json
from collections import defaultdict
from pathlib import Path

from dnd_board_game.runtime.glodne_cienie_playtest import (
    default_playtest_cases,
    run_playtest_matrix,
)


def main() -> int:
    parser = argparse.ArgumentParser()
    parser.add_argument("--runs", type=int, default=20)
    parser.add_argument("--base-seed", type=int, default=41000)
    parser.add_argument("--max-rounds", type=int, default=15)
    parser.add_argument(
        "--output-dir",
        default="artifacts/playtests/glodne_cienie",
    )
    args = parser.parse_args()
    output = Path(args.output_dir)
    output.mkdir(parents=True, exist_ok=True)
    results, events = run_playtest_matrix(
        default_playtest_cases(args.runs),
        base_seed=args.base_seed,
        max_rounds=args.max_rounds,
    )
    (output / "events.jsonl").write_text(
        "".join(json.dumps(event, ensure_ascii=False) + "\n" for event in events),
        encoding="utf-8",
    )
    payloads = [result.as_payload() for result in results]
    (output / "results.json").write_text(
        json.dumps(payloads, ensure_ascii=False, indent=2) + "\n",
        encoding="utf-8",
    )
    fieldnames = [
        "case_id", "seed", "hero_ids", "party_size", "outcome", "rounds",
        "turns", "hero_casualties", "hero_hp_remaining", "hero_hp_maximum",
        "enemies_dead", "enemies_escaped", "enemy_intents", "morale_events",
    ]
    with (output / "results.csv").open("w", newline="", encoding="utf-8") as handle:
        writer = csv.DictWriter(handle, fieldnames=fieldnames)
        writer.writeheader()
        for payload in payloads:
            writer.writerow(
                {
                    **payload,
                    "hero_ids": ",".join(payload["hero_ids"]),
                    "enemy_intents": json.dumps(payload["enemy_intents"], ensure_ascii=False),
                    "morale_events": ",".join(payload["morale_events"]),
                }
            )
    grouped = defaultdict(list)
    for result in results:
        grouped[result.case_id].append(result)
    summary = []
    for case_id, rows in grouped.items():
        summary.append(
            {
                "case_id": case_id,
                "hero_ids": list(rows[0].hero_ids),
                "party_size": rows[0].party_size,
                "runs": len(rows),
                "victories": sum(row.outcome == "victory" for row in rows),
                "defeats": sum(row.outcome == "defeat" for row in rows),
                "timeouts": sum(row.outcome == "timeout" for row in rows),
                "win_rate": round(sum(row.outcome == "victory" for row in rows) / len(rows), 3),
                "mean_rounds": round(sum(row.rounds for row in rows) / len(rows), 2),
                "mean_casualties": round(sum(row.hero_casualties for row in rows) / len(rows), 2),
                "mean_hp_ratio": round(
                    sum(row.hero_hp_remaining / row.hero_hp_maximum for row in rows) / len(rows),
                    3,
                ),
            }
        )
    (output / "summary.json").write_text(
        json.dumps(summary, ensure_ascii=False, indent=2) + "\n",
        encoding="utf-8",
    )
    print(json.dumps(summary, ensure_ascii=False, indent=2))
    return 0


if __name__ == "__main__":
    raise SystemExit(main())

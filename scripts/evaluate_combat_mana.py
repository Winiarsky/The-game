#!/usr/bin/env python3
"""Reproducible trump-card economy baseline, using the actual pooled-card rules."""
from __future__ import annotations

import argparse
import csv
from datetime import datetime, timezone
import hashlib
import html
import json
from pathlib import Path
import subprocess
import sys

sys.path.insert(0, str(Path(__file__).resolve().parents[1] / "src"))
from dnd_board_game.evaluation.pooled_mana import compare
from dnd_board_game.scenarios.pooled_mana_catalog import DEFAULT_PATH, load_catalog


def main() -> None:
    parser = argparse.ArgumentParser(description=__doc__)
    parser.add_argument("--samples", type=int, default=21)
    parser.add_argument("--rounds", type=int, default=8)
    parser.add_argument("--seed", type=int, default=20260914)
    parser.add_argument("--sizes", default="3,4,5,6")
    parser.add_argument("--catalog", type=Path, default=DEFAULT_PATH)
    parser.add_argument("--output", type=Path, default=Path("/tmp/combat-mana-evaluation"))
    args = parser.parse_args()
    sizes = tuple(int(n) for n in args.sizes.split(","))
    if not 1 <= args.samples <= 10000 or not 1 <= args.rounds <= 100 or any(n not in range(1, 8) for n in sizes):
        parser.error("samples: 1–10000, rounds: 1–100, sizes: 1–7")
    rows = compare(load_catalog(str(args.catalog.resolve())), args.samples, args.rounds, args.seed, sizes)
    limitations = ["Ładunek ponad próg jest zachowany, a nie wydawany. Ekonomia kart, bez modelu obrażeń, leczenia, pozycji i zwycięstwa w walce.",
                  "Uwzględnia limit 6 fizycznych kart i próg ulty 6 ładunku (atut = 2, reszta = 1), spalanie akcji, wygaśnięcie co rundę i odzysk Loriana. Nie mierzy siły bojowej premii kolorów ani sytuacyjnych skaz.",
                  "Strategie są heurystyczne; medianę dojścia do ulta czytaj razem z odsetkiem nieosiągnięcia.",
                  "Składy i inicjatywa rotują cyklicznie; to nie wszystkie kombinacje drużyn.",
                  "Symulowane rundy nie określają czasu obsługi przez człowieka."]
    root = Path(__file__).resolve().parents[1]
    commit = subprocess.run(["git", "rev-parse", "HEAD"], cwd=root, capture_output=True, text=True, timeout=5).stdout.strip()
    dirty = subprocess.run(["git", "status", "--porcelain"], cwd=root, capture_output=True, text=True, timeout=5).stdout
    report = dict(stage="card_economy", created=datetime.now(timezone.utc).isoformat(), seed=args.seed,
                  catalog_sha256=hashlib.sha256(args.catalog.read_bytes()).hexdigest(), commit=commit,
                  worktree_dirty=bool(dirty), samples=args.samples, rounds=args.rounds, sizes=sizes,
                  pressure_schedule="Na koniec każdej rundy: oferta 1 karta albo wierzch 2 karty. To próba obciążeniowa, nie harmonogram produkcyjnych wrogów.",
                  limitations=limitations, rows=rows)
    args.output.mkdir(parents=True, exist_ok=True)
    (args.output / "catalog.json").write_bytes(args.catalog.read_bytes())
    (args.output / "report.json").write_text(json.dumps(report, ensure_ascii=False, indent=2) + "\n")
    columns = ("players", "cards", "pressure", "policy", "trials", "ultimate_median_when_reached",
               "ultimate_unreached_fraction", "drains_per_trial", "basic_attack_fraction", "fully_charged_fraction", "ability_uses_per_hero", "held_cards_mean", "charge_above_threshold_mean", "charge_lost_per_drain")
    with (args.output / "report.csv").open("w", newline="") as stream:
        writer = csv.DictWriter(stream, columns, extrasaction="ignore")
        writer.writeheader()
        writer.writerows(rows)
    body = "".join("<tr>" + "".join(f"<td>{html.escape(str(row[c]))}</td>" for c in columns) + "</tr>" for row in rows)
    (args.output / "report.html").write_text("<!doctype html><html lang='pl'><meta charset='utf-8'><title>Ewaluacja many</title>"
        "<style>body{font:16px system-ui;margin:24px}table{border-collapse:collapse}td,th{padding:8px;border:1px solid #aaa}thead{position:sticky;top:0;background:#fff}</style>"
        "<h1>Ekonomia pul many — punkt odniesienia</h1><p>Seed: " + str(args.seed) + "</p><ul>" +
        "".join(f"<li>{html.escape(t)}</li>" for t in limitations) + "</ul><label>Filtr <input oninput=\"document.querySelectorAll('tbody tr').forEach(r=>r.hidden=!r.textContent.includes(this.value))\"></label>"
        "<table><thead><tr>" + "".join(f"<th>{c}</th>" for c in columns) + "</tr></thead><tbody>" + body + "</tbody></table></html>")
    print(json.dumps(dict(output=str(args.output), experiments=len(rows), trials=sum(r["trials"] for r in rows), limitations=limitations), ensure_ascii=False))


if __name__ == "__main__":
    main()

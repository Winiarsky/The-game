"""Repeatable Mission 0 confrontation and encounter baseline, using production rules."""
from __future__ import annotations

import argparse
from itertools import combinations
import json
from pathlib import Path
from statistics import mean
import sys

ROOT = Path(__file__).resolve().parents[1]
sys.path.insert(0, str(ROOT / 'src'))
from evaluate_party_confrontations import simulate
from dnd_board_game.application.confrontation import build
from dnd_board_game.rules.exploration_mana_catalog import HEROES
from dnd_board_game.scenarios.loader import load_scenario, build_encounter_from_scenario, encounter_for_party_size
from dnd_board_game.ui.training_arena import training_hero


def main() -> None:
    parser = argparse.ArgumentParser(description=__doc__)
    parser.add_argument('--trials', type=int, default=10, help='Seeds per party composition')
    args = parser.parse_args()
    if not 1 <= args.trials <= 1000:
        parser.error('trials: 1–1000')
    pack = ROOT / 'content/scenarios/misja_0_dzwon'
    scenes = json.loads((pack / 'mechanics/confrontations.json').read_text())
    actors = {h: training_hero(h) for h in HEROES}
    lines = ['# Misja 0 — punkt odniesienia do ogrania', '',
        'Skrypt używa produkcyjnych zasad. Sprawdza wszystkie składy 3–6 z siedmiu bohaterów.',
        f'{args.trials} ziaren na skład. Polityka: karta z największą liczbą punktów, najwyższa dostępna premia;',
        'pomoc przy szansie trafienia poniżej 35%. Bez przyjmowania kompromisu Nessy.',
        'To porównanie jednej prostej strategii, nie pomiar optymalnej gry ani czasu przy stole.',
        'Pomieszczenia: bez wskazówki −2 ST i bez pomocy naprawiającej uszkodzenia. Nessa: bez komplementu.', '',
        '| Osoby | Scena | Próby | Sukces | Średnie rundy | Średnia liczba testów |',
        '|---:|---|---:|---:|---:|---:|']
    for n in (3, 4, 5, 6):
        for key, scene in scenes.items():
            results = []
            for party in combinations(HEROES, n):
                template = build(tuple(actors[h] for h in party), scene)
                results.extend(simulate(template, seed, cooperation=True) for seed in range(args.trials))
            lines.append(f'| {n} | {key} | {len(results)} | {mean(r[0] for r in results):.1%} | {mean(r[1] for r in results):.2f} | {mean(r[2] for r in results):.2f} |')
            print(n, key, len(results), flush=True)
    encounter = build_encounter_from_scenario(load_scenario(pack / 'mechanics/battle.json'))
    lines += ['', '## Skład walki', '', '| Bohaterowie | Wrogowie | Suma HP wrogów |', '|---:|---:|---:|']
    for n in (3, 4, 5, 6):
        enemies = [a for a in encounter_for_party_size(encounter, n).actors if a.faction.value == 'enemy']
        lines.append(f'| {n} | {len(enemies)} | {sum(a.hp for a in enemies)} |')
    lines += ['', 'Walka: N+2 wrogów, jednorazowa oferta rozejmu po pierwszym pokonanym przeciwniku.',
        'Ta część raportu jest kontrolą konfiguracji, nie symulacją zwycięstw. Nie modeluje ruchu,',
        'celowania, leczenia ani decyzji przy poddaniu. W testach ręcznych porównać 0 i 4 rundy',
        'zmęczenia, tempo ładowania oraz moment poddania. Zapisać czas scen i odczucia każdego gracza.',
        'Zwykłe ataki wieśniaków nie spalają many; presja wynika z użycia zdolności i upływu rund.', '']
    (pack / 'BALANCE_REPORT.md').write_text('\n'.join(lines), encoding='utf-8')

if __name__ == '__main__':
    main()

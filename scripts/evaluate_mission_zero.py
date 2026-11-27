"""Seeded Mission 0 report sharing the progress_v1 builder and rules with /play."""
from __future__ import annotations

import argparse
from collections import Counter
from dataclasses import asdict, dataclass
from itertools import combinations
import json
from pathlib import Path
import random
from statistics import mean
import sys
from typing import Any

ROOT = Path(__file__).resolve().parents[1]
sys.path[:0] = [str(ROOT / 'src'), str(ROOT)]

from dnd_board_game.application.progress_confrontation import ENGINE, build
from dnd_board_game.rules import progress_confrontation as rules
from dnd_board_game.rules.exploration_mana_catalog import HEROES
from dnd_board_game.scenarios.loader import load_scenario, build_encounter_from_scenario, encounter_for_party_size
from dnd_board_game.ui.training_arena import training_hero

MODEL = 'mission_progress_v1.1'
POLICIES = ('best_no_spend_v1', 'random_no_spend_v1', 'best_minimum_reputation_v1')


@dataclass(frozen=True)
class Run:
    policy: str
    seed: int
    outcome: str
    tier: str
    progress: int
    tests: int
    reputation_spent: int
    natural_one_seen: bool
    trace: tuple[dict[str, Any], ...]


def simulate(
    template: rules.Confrontation, seed: int, *, policy: str = POLICIES[0], reputation: int = 20,
) -> Run:
    if policy not in POLICIES or reputation < 0:
        raise ValueError('Nieznana strategia lub ujemna reputacja.')
    dice = random.Random(seed)
    # Pre-draw by participant: option choice and early termination cannot shift
    # another participant's paired dice between variants.
    rolls = tuple((dice.randint(1, 20), dice.randint(1, 20)) for _ in template.participants)
    decisions = random.Random(seed ^ 0xB0A7)
    state = rules.begin(template)
    balance = reputation
    trace: list[dict[str, Any]] = []
    while state.stage != 'result':
        options = rules.available_approaches(state)
        if not options:
            state = rules.pass_turn(state)
        else:
            option = (decisions.choice(options) if policy == 'random_no_spend_v1'
                      else max(options, key=lambda candidate: candidate.modifier - candidate.dc))
            actor_id, turn = state.actor.id, state.turn
            state = rules.roll(rules.choose(state, option.id), rolls[turn][0])
            if policy == 'best_minimum_reputation_v1':
                preview = rules.preview(state)
                available = rules.available_boosts(state, balance)
                if preview['delta'] <= 0:
                    deficit = option.dc - preview['total']
                    boost = ('plus_one' if 0 < deficit <= 1 and 'plus_one' in available
                             else 'plus_five' if 0 < deficit <= 5 and 'plus_five' in available
                             else 'extra_die' if 'extra_die' in available else '')
                    if boost:
                        state = rules.select_boost(state, boost, balance)
            state, cost = rules.confirm(state, balance)
            balance -= cost
            if state.stage == 'extra_check':
                state = rules.roll(state, rolls[turn][1])
                state, second_cost = rules.confirm(state, balance)
                balance -= second_cost
            trace.append(dict(actor=actor_id, approach=option.id, dc=option.dc, roll=state.last_roll,
                              total=state.last_total, impact=state.last_impact, progress=state.progress,
                              reputation=balance))
        if state.stage == 'after_action':
            state = rules.advance(state)
    return Run(policy, seed, state.outcome, state.tier, state.progress, len(trace),
               reputation - balance, state.natural_one_seen, tuple(trace))


def main() -> None:
    parser = argparse.ArgumentParser(description=__doc__)
    parser.add_argument('--trials', type=int, default=10, help='Seeds 0..N-1 per party composition')
    parser.add_argument('--output', type=Path, default=ROOT / 'content/scenarios/misja_0_dzwon/BALANCE_REPORT.md')
    parser.add_argument('--jsonl', type=Path, help='Optional individual runs with traces')
    args = parser.parse_args()
    if not 1 <= args.trials <= 1000:
        parser.error('trials: 1–1000')
    pack = ROOT / 'content/scenarios/misja_0_dzwon'
    scenes = json.loads((pack / 'mechanics/confrontations.json').read_text())
    actors = {hero: training_hero(hero) for hero in HEROES}
    lines = ['# Misja 0 — konfrontacje jednej kolejki', '',
             f'Model `{MODEL}`, silnik `{ENGINE}`. Wszystkie 98 składów 3–6 spośród siedmiu bohaterów.',
             f'{args.trials} ziaren na skład: 100000 × liczba osób + 1000 × indeks składu + 0…{args.trials - 1}.',
             'Składy w kolejności combinations(HEROES, N); kości sparowane między wariantami i strategiami.',
             'Wspólny z grą konstruktor i reguły, ST 14; wskazówka: ST 12 w kwaterze. Bez komplementu Nessy.',
             '`best_no_spend_v1`: legalne podejście z najwyższą różnicą modyfikator − ST;',
             '`random_no_spend_v1`: losowe legalne podejście; `best_minimum_reputation_v1`: najlepsze podejście,',
             'po porażce najtańsza wystarczająca premia lub dodatkowa kość. Każda scena zaczyna z 20 reputacji.',
             'To nie model całej ekonomii wyprawy ani zachowania ludzi. Pas bez podejść kończy kolej bohatera.',
             'Kolejność bohaterów to HEROES; raport nie sprawdza jej permutacji ani optymalizacji przydziału podejść.',
             'Sukces oznacza wynik `success`; częściowy wynik jest osobno. Rozkład podaje liczności poziomów.', '',
             '| Osób | Scena | Wariant | Strategia | Prób | Sukces | Częściowy | Testy min–max | Śr. koszt reputacji | Rozkład poziomów |',
             '|---:|---|---|---|---:|---:|---:|---|---:|---|']
    checks = 0
    run_count = 0
    if args.jsonl:
        args.jsonl.parent.mkdir(parents=True, exist_ok=True)
    # Stream the optional traces instead of retaining a whole benchmark in memory.
    from contextlib import nullcontext
    output = args.jsonl.open('w', encoding='utf-8') if args.jsonl else nullcontext(None)
    with output as stream:
        for count in (3, 4, 5, 6):
            for name, scene in scenes.items():
                for policy in POLICIES:
                    baseline: dict[tuple[tuple[str, ...], int], Run] = {}
                    for clue in ((False, True) if name == 'quarters' else (False,)):
                        results = []
                        for party_index, members in enumerate(combinations(HEROES, count)):
                            spec = {**scene, 'progress_dc_adjustment': -2 if clue else 0}
                            template = build(tuple(actors[hero] for hero in members), spec)
                            for offset in range(args.trials):
                                seed = 100000 * count + 1000 * party_index + offset
                                run = simulate(template, seed, policy=policy)
                                assert -1 <= run.progress <= count and run.tests <= count, (members, seed, run)
                                assert 0 <= run.reputation_spent <= 20, (members, seed, run)
                                if clue:
                                    before = baseline[(members, seed)]
                                    assert not (before.outcome == 'success' and run.outcome != 'success'), (members, seed)
                                    checks += 1
                                else:
                                    baseline[(members, seed)] = run
                                results.append(run)
                                run_count += 1
                                if stream:
                                    record = dict(model=MODEL, engine=ENGINE, scene=name, party=members, clue=clue, **asdict(run))
                                    stream.write(json.dumps(record, ensure_ascii=False) + '\n')
                        distribution = ', '.join(f'{key}: {value}' for key, value in sorted(Counter(r.tier for r in results).items()))
                        variant = 'wskazówka' if clue else 'bez wskazówki'
                        lines.append(f'| {count} | {name} | {variant} | {policy} | {len(results)} | '
                                     f"{mean(r.outcome == 'success' for r in results):.1%} | {mean(r.outcome == 'compromise' for r in results):.1%} | "
                                     f'{min(r.tests for r in results)}–{max(r.tests for r in results)} | {mean(r.reputation_spent for r in results):.2f} | {distribution} |')
    encounter = build_encounter_from_scenario(load_scenario(pack / 'mechanics/battle.json'))
    lines += ['', '## Kontrola konfiguracji walki', '', '| Bohaterowie | Wrogowie | Suma PW wrogów |', '|---:|---:|---:|']
    for count in (3, 4, 5, 6):
        enemies = [a for a in encounter_for_party_size(encounter, count).actors if a.faction.value == 'enemy']
        lines.append(f'| {count} | {len(enemies)} | {sum(a.hp for a in enemies)} |')
    lines += ['', f'Kontrole granic, kosztów i zakończenia przeszły w {run_count} przebiegach. Wskazówka nie pogorszyła sukcesu w {checks} parach.',
              'To kontrola mechaniki, nie ocena atrakcyjności ani czasu gry. Brak symulacji ruchu, Rezonansu,',
              'ataków, leczenia i negocjowania rozejmu. Naprawa uszkodzenia po rozejmie nie zmienia szansy znalezienia przedmiotu.',
              'Wskazówka po rozejmie jest darmowa, poza nim kosztuje 1 sz (złoto nie w kolumnie reputacji).',
              'Raport zastępuje wcześniejszą symulację talii, która nie odpowiadała aktualnej Misji 0.', '']
    args.output.parent.mkdir(parents=True, exist_ok=True)
    args.output.write_text('\n'.join(lines), encoding='utf-8')
    print(f'{args.output}: OK; {run_count} przebiegów, {checks} par ze wskazówką')


if __name__ == '__main__':
    main()

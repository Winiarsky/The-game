"""Seeded finite-deck policy comparison, not a claim of optimal play or balance."""
from __future__ import annotations

import argparse
import json
from random import Random

from dnd_board_game.rules.exploration_mana import ManaAttempt, choose_color, declare_draw, stand, next_value
from dnd_board_game.rules.exploration_mana_catalog import COLORS, METHODS, PROFILES, OBSTACLES
from dnd_board_game.application.exploration_mana_flow import method_modifiers
from dnd_board_game.ui.training_arena import training_hero


def compare(samples: int, seed: int) -> dict[str, object]:
    rng = Random(seed)
    rows = []
    for method in METHODS:
        base = sum(m.value for m in method_modifiers(training_hero(method.hero_id), method))
        dc = 16 if method.kind == 'npc' else 15
        for profile, values in PROFILES:
            for obstacle, _, _ in OBSTACLES:
                for stop in (17, 18, 19, 20):
                    won = exact = bust = choices = 0
                    for _ in range(samples):
                        deck = list(COLORS) * 5
                        rng.shuffle(deck)
                        attempt = ManaAttempt('simulation', 'comparison', method.id, values, obstacle)
                        while attempt.phase in {'offer', 'decision'}:
                            if attempt.phase == 'decision':
                                if attempt.total >= stop:
                                    attempt = stand(attempt)
                                    break
                                attempt = declare_draw(attempt)
                            if not deck:
                                attempt = stand(attempt, empty_deck=True)
                                break
                            offer = [deck.pop() for _ in range(min(2, len(deck)))]
                            while len(set(offer)) == 1 and deck:
                                offer.append(deck.pop())
                            def rank(color: str) -> tuple[int, int]:
                                total = attempt.total + next_value(attempt, color)
                                return (0, 0) if total == 21 else (1, -total) if total <= stop else (2, total) if total <= 21 else (3, total)
                            attempt = choose_color(attempt, min(dict.fromkeys(offer), key=rank))
                        exact += int(attempt.total == 21)
                        bust += int(attempt.busted)
                        choices += len(attempt.colors)
                        die = rng.randint(1,20)
                        if attempt.busted:
                            die = min(die,rng.randint(1,20))
                        success = attempt.success or die + base + attempt.bonus >= dc
                        if not success and method.id == 'inspiration':
                            die = rng.randint(1,20)
                            if attempt.busted:
                                die = min(die,rng.randint(1,20))
                            success = die + base + attempt.bonus >= dc
                        won += int(bool(success))
                    rows.append(dict(method=method.id, profile=profile, obstacle=obstacle, stop=stop,
                        base=base, dc=dc, success=round(won/samples,4), exact=round(exact/samples,4),
                        bust=round(bust/samples,4), mean_choices=round(choices/samples,2)))
    return dict(seed=seed, samples_per_cell=samples, policy='Greedy threshold with exact-21 priority; optional duplicate redraw always used; no clairvoyance.', rows=rows)


if __name__ == '__main__':
    parser = argparse.ArgumentParser()
    parser.add_argument('--samples', type=int, default=200)
    parser.add_argument('--seed', type=int, default=20260914)
    args = parser.parse_args()
    if args.samples < 1:
        parser.error('--samples must be positive')
    print(json.dumps(compare(args.samples,args.seed),ensure_ascii=False,indent=2))

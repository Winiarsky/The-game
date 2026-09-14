"""Compare simple choices on finite decks; report benefits and costs separately."""
from __future__ import annotations

import argparse
from collections import Counter
import json
from random import Random

from dnd_board_game.rules.exploration_mana import (
    ManaAttempt, answer_bargain, choose_color, declare_draw, next_value, set_favor, stand, request_reroll,
)
from dnd_board_game.rules.exploration_mana_catalog import COLORS, METHODS, profile_values
from dnd_board_game.application.exploration_mana_flow import resolve_attempt
from dnd_board_game.scenarios.exploration_mana import scene_by_id
from dnd_board_game.ui.training_arena import training_hero


def compare(samples: int, seed: int) -> dict[str, object]:
    rows = []
    for kind in ('compromise','sensitive_topic','color_goal','favor'):
        condition = scene_by_id('irena_'+kind).condition
        for policy in ('cautious', 'tempted'):
            counts: Counter[str] = Counter()
            for method_index, method in enumerate(m for m in METHODS if m.kind == 'npc'):
                actor = training_hero(method.hero_id)
                for trial_index in range(samples):
                    rng = Random(seed + method_index * 100000 + trial_index)
                    deck = list(COLORS) * 5
                    rng.shuffle(deck)
                    a = ManaAttempt('sim','scene',method.id,profile_values('balanced'),condition=condition)
                    while a.phase != 'result':
                        if a.phase == 'bargain':
                            a = answer_bargain(a, accept=policy=='cautious')
                        elif a.phase == 'decision':
                            pursue_goal = kind=='color_goal' and policy=='tempted' and not a.goal_met
                            a = stand(a) if a.total >= 18 and not pursue_goal else declare_draw(a)
                        elif a.phase == 'offer':
                            if not deck:
                                a = stand(a, empty_deck=True)
                                continue
                            offer = [deck.pop() for _ in range(min(2,len(deck)))]
                            while len(set(offer)) == 1 and deck:
                                offer.append(deck.pop())
                            def rank(c: str) -> tuple[int, int, int]:
                                total = a.total + next_value(a,c)
                                priority = (1 if c=='C' else 0) if kind=='sensitive_topic' and policy=='cautious' else (-1 if c=='N' and not a.goal_met else 0) if kind=='color_goal' and policy=='tempted' else 0
                                return (priority, 0 if total==21 else 1 if total<=21 else 2, -total if total<=21 else total)
                            color = min(dict.fromkeys(offer),key=rank)
                            if kind=='favor' and policy=='tempted' and a.favor_status=='available' and (a.total==20 or a.total+next_value(a,color)>21):
                                a = set_favor(a,armed=True)
                            a = choose_color(a,color)
                        elif a.phase == 'roll':
                            rolls = tuple(rng.randint(1,20) for _ in range(2 if a.busted else 1))
                            a = resolve_attempt(actor,a,16,rolls,improvisation_available=True)
                        elif a.phase == 'reroll_choice':
                            a = request_reroll(a)
                    counts[a.outcome_kind] += 1
                    counts['extra_information'] += int(a.success is True and (a.goal_met or a.sensitive_used))
                    counts['relationship_cost'] += int(a.success is True and a.sensitive_used)
                    counts['obligation'] += int(a.favor_status=='used')
                    counts['bust'] += int(a.busted)
            rows.append(dict(condition=kind,policy=policy,trials=7*samples,**{k:counts[k] for k in ('success','compromise','failure','extra_information','relationship_cost','obligation','bust')}))
    return dict(seed=seed, samples_per_hero=samples, rows=rows,
                limitation='Simple greedy policies, not optimal play. Narrative costs have no invented numeric utility.')


if __name__ == '__main__':
    parser=argparse.ArgumentParser()
    parser.add_argument('--samples',type=int,default=100)
    parser.add_argument('--seed',type=int,default=20260914)
    args=parser.parse_args()
    if args.samples<1: parser.error('samples must be positive')
    print(json.dumps(compare(args.samples,args.seed),ensure_ascii=False,indent=2))

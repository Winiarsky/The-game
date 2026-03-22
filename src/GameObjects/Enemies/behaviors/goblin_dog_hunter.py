from __future__ import annotations

import logging

from GameObjects.events import EventContext
from GameObjects.events.registry import dispatch_event

from .tactical_utils import (
    best_weapon,
    can_attack_from_position,
    count_adjacent_heroes,
    distance_ft,
    hp_ratio,
    living_heroes,
    reachable_positions,
    ranged_cover_rank,
    target_is_lone,
)

logger = logging.getLogger(__name__)


def _focus_target(enemy, game):
    best_target = None
    best_score = -10_000
    for hero in living_heroes(game):
        score = 0
        score += int((1.0 - hp_ratio(hero)) * 30)
        if target_is_lone(game, hero):
            score += 12
        score -= distance_ft(getattr(enemy, "position", None), getattr(hero, "position", None))
        if score > best_score:
            best_score = score
            best_target = hero
    if best_target is not None:
        enemy.ai_memory["focus_target_id"] = getattr(best_target, "object_id", None)
    return best_target


def _nearest_hero(enemy, game):
    heroes = living_heroes(game)
    if not heroes:
        return None
    return min(heroes, key=lambda hero: distance_ft(getattr(enemy, "position", None), getattr(hero, "position", None)))


def _score_hunt_position(enemy, game, target, jaws, pos) -> int:
    score = 0
    if can_attack_from_position(game, enemy, target, jaws, pos):
        score += 14
    score += int((1.0 - hp_ratio(target)) * 12)
    if target_is_lone(game, target):
        score += 8
    score += ranged_cover_rank(game, attacker=target, defender_pos=pos) * 2
    score -= max(0, count_adjacent_heroes(game, pos) - 1) * 7
    if pos == getattr(enemy, "position", None):
        score += 1
    return score


def _score_retreat_position(enemy, game, pos) -> int:
    nearest = _nearest_hero(enemy, game)
    if nearest is None:
        return 0
    score = distance_ft(pos, getattr(nearest, "position", None))
    score += ranged_cover_rank(game, attacker=nearest, defender_pos=pos) * 10
    score -= count_adjacent_heroes(game, pos) * 12
    if pos == getattr(enemy, "position", None):
        score -= 5
    return score


def goblin_dog_hunter(enemy, game, combat_state, actions_left: int = 1) -> int:
    if getattr(enemy, "position", None) is None:
        return 0

    used = 0
    jaws = best_weapon(enemy, weapon_id="jaws", ranged=False)

    while used < actions_left:
        remaining = actions_left - used
        current_pos = getattr(enemy, "position", None)
        target = _focus_target(enemy, game)
        if target is None:
            break

        if hp_ratio(enemy) <= 0.4:
            candidates = reachable_positions(game, enemy, include_current=False)
            if candidates:
                best = max(candidates, key=lambda item: _score_retreat_position(enemy, game, item["position"]))
                result = dispatch_event(
                    "enemy_move",
                    EventContext(game=game, actor=enemy, metadata={"goal_position": best["position"]}),
                )
                used += 1 if result.consumed_action else 0
                if result.consumed_action:
                    continue

        if remaining >= 2 and count_adjacent_heroes(game, current_pos) >= 2:
            result = dispatch_event("goblin_dog_scratch", EventContext(game=game, actor=enemy))
            used += int(result.actions_spent or 0) if result.consumed_action else 0
            if result.consumed_action:
                continue

        if jaws is not None and can_attack_from_position(game, enemy, target, jaws, current_pos):
            result = dispatch_event(
                "enemy_strike",
                EventContext(game=game, actor=enemy, metadata={"forced_target": target, "weapon_id": "jaws"}),
            )
            used += 1 if result.consumed_action else 0
            if result.consumed_action:
                continue

        if jaws is not None:
            candidates = reachable_positions(game, enemy, include_current=False)
            if candidates:
                best = max(candidates, key=lambda item: _score_hunt_position(enemy, game, target, jaws, item["position"]))
                result = dispatch_event(
                    "enemy_move",
                    EventContext(game=game, actor=enemy, metadata={"goal_position": best["position"]}),
                )
                used += 1 if result.consumed_action else 0
                if result.consumed_action:
                    continue

        break

    return used

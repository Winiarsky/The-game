from __future__ import annotations

import logging

from combat import refresh_flanking_statuses
from GameObjects.events import EventContext
from GameObjects.events.registry import dispatch_event

from .tactical_utils import (
    best_weapon,
    can_attack_from_position,
    count_adjacent_allies,
    count_adjacent_enemies_to_target,
    count_adjacent_heroes,
    distance_ft,
    flank_positions_for_target,
    hp_ratio,
    living_heroes,
    reachable_positions,
)

logger = logging.getLogger(__name__)


def _focus_target(enemy, game):
    current_id = str((getattr(enemy, "ai_memory", {}) or {}).get("focus_target_id", "") or "")
    for hero in living_heroes(game):
        if str(getattr(hero, "object_id", "") or "") == current_id:
            return hero

    best_target = None
    best_score = -10_000
    for hero in living_heroes(game):
        score = 0
        score -= distance_ft(getattr(enemy, "position", None), getattr(hero, "position", None))
        score += count_adjacent_enemies_to_target(game, hero) * 15
        score += int((1.0 - hp_ratio(hero)) * 20)
        if score > best_score:
            best_score = score
            best_target = hero
    if best_target is not None:
        enemy.ai_memory["focus_target_id"] = getattr(best_target, "object_id", None)
    return best_target


def _score_pack_position(enemy, game, target, pos, melee_weapon) -> int:
    flank_positions = set(flank_positions_for_target(game, enemy, target))
    score = 0
    if pos in flank_positions:
        score += 20
    if can_attack_from_position(game, enemy, target, melee_weapon, pos):
        score += 10
    score += count_adjacent_allies(game, pos, actor=enemy) * 4
    score += count_adjacent_enemies_to_target(game, target) * 3
    score -= max(0, count_adjacent_heroes(game, pos) - 1) * 6
    if pos == getattr(enemy, "position", None):
        score -= 1
    return score


def _score_bow_position(enemy, game, target, bow, pos) -> int:
    if not can_attack_from_position(game, enemy, target, bow, pos):
        return -999
    desired = 30
    score = 0
    score -= abs(distance_ft(pos, getattr(target, "position", None)) - desired) // 5
    score -= count_adjacent_heroes(game, pos) * 8
    if pos == getattr(enemy, "position", None):
        score += 1
    return score


def goblin_warrior_pack(enemy, game, combat_state, actions_left: int = 1) -> int:
    if getattr(enemy, "position", None) is None:
        return 0

    used = 0
    melee_weapon = best_weapon(enemy, weapon_id="dogslicer", ranged=False)
    bow = best_weapon(enemy, weapon_id="shortbow", ranged=True)

    while used < actions_left:
        remaining = actions_left - used
        try:
            refresh_flanking_statuses(game)
        except Exception:
            logger.debug("Nie udało się odświeżyć flankowania goblin warrior.", exc_info=True)

        target = _focus_target(enemy, game)
        if target is None:
            break

        outnumbered = count_adjacent_enemies_to_target(game, target) < 1 or hp_ratio(enemy) <= 0.4
        current_pos = getattr(enemy, "position", None)

        if melee_weapon is not None and not outnumbered and can_attack_from_position(game, enemy, target, melee_weapon, current_pos):
            result = dispatch_event(
                "enemy_strike",
                EventContext(game=game, actor=enemy, metadata={"forced_target": target, "weapon_id": "dogslicer"}),
            )
            used += 1 if result.consumed_action else 0
            if result.consumed_action:
                continue

        if melee_weapon is not None and not outnumbered:
            candidates = reachable_positions(game, enemy, include_current=False)
            if candidates:
                best = max(candidates, key=lambda item: _score_pack_position(enemy, game, target, item["position"], melee_weapon))
                if _score_pack_position(enemy, game, target, best["position"], melee_weapon) >= 10:
                    result = dispatch_event(
                        "enemy_move",
                        EventContext(game=game, actor=enemy, metadata={"goal_position": best["position"]}),
                    )
                    used += 1 if result.consumed_action else 0
                    if result.consumed_action:
                        continue

        if bow is not None and can_attack_from_position(game, enemy, target, bow, current_pos):
            result = dispatch_event(
                "enemy_strike",
                EventContext(game=game, actor=enemy, metadata={"forced_target": target, "weapon_id": "shortbow"}),
            )
            used += 1 if result.consumed_action else 0
            if result.consumed_action:
                continue

        if bow is not None:
            candidates = reachable_positions(game, enemy, include_current=False)
            if candidates:
                best = max(candidates, key=lambda item: _score_bow_position(enemy, game, target, bow, item["position"]))
                if _score_bow_position(enemy, game, target, bow, best["position"]) > -999:
                    result = dispatch_event(
                        "enemy_move",
                        EventContext(game=game, actor=enemy, metadata={"goal_position": best["position"]}),
                    )
                    used += 1 if result.consumed_action else 0
                    if result.consumed_action:
                        continue

        break

    return used

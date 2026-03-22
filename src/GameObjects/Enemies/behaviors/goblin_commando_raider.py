from __future__ import annotations

import logging

from combat import refresh_flanking_statuses
from GameObjects.events import EventContext
from GameObjects.events.registry import dispatch_event

from .tactical_utils import (
    best_weapon,
    can_attack_from_position,
    count_adjacent_enemies_to_target,
    count_adjacent_heroes,
    distance_ft,
    hp_ratio,
    living_heroes,
    reachable_positions,
)

logger = logging.getLogger(__name__)


def _has_status(actor, status_id: str) -> bool:
    checker = getattr(actor, "has_status", None)
    if callable(checker):
        try:
            return bool(checker(status_id))
        except Exception:
            return False
    for status in getattr(actor, "statuses", []) or []:
        if str(getattr(status, "id", status) or "").strip().lower() == status_id:
            return True
    return False


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
        score += count_adjacent_enemies_to_target(game, hero) * 10
        score += int((1.0 - hp_ratio(hero)) * 18)
        if not _has_status(hero, "frightened"):
            score += 4
        if score > best_score:
            best_score = score
            best_target = hero
    if best_target is not None:
        enemy.ai_memory["focus_target_id"] = getattr(best_target, "object_id", None)
    return best_target


def _score_reach_position(enemy, game, target, polearm, pos) -> int:
    if not can_attack_from_position(game, enemy, target, polearm, pos):
        return -999
    dist = distance_ft(pos, getattr(target, "position", None))
    score = 0
    if dist == 10:
        score += 14
    elif dist == 5:
        score += 9
    score += count_adjacent_enemies_to_target(game, target) * 3
    score -= max(0, count_adjacent_heroes(game, pos) - 1) * 7
    if pos == getattr(enemy, "position", None):
        score += 1
    return score


def _score_bow_position(enemy, game, target, bow, pos) -> int:
    if not can_attack_from_position(game, enemy, target, bow, pos):
        return -999
    desired = 35
    score = 0
    score -= abs(distance_ft(pos, getattr(target, "position", None)) - desired) // 5
    score -= count_adjacent_heroes(game, pos) * 8
    return score


def goblin_commando_raider(enemy, game, combat_state, actions_left: int = 1) -> int:
    if getattr(enemy, "position", None) is None:
        return 0

    used = 0
    polearm = best_weapon(enemy, weapon_id="horsechopper", ranged=False)
    bow = best_weapon(enemy, weapon_id="shortbow", ranged=True)

    while used < actions_left:
        remaining = actions_left - used
        try:
            refresh_flanking_statuses(game)
        except Exception:
            logger.debug("Nie udało się odświeżyć flankowania goblin commando.", exc_info=True)

        target = _focus_target(enemy, game)
        if target is None:
            break
        current_pos = getattr(enemy, "position", None)
        target_key = str(getattr(target, "object_id", getattr(target, "name", "target")) or "target")

        if (
            remaining >= 1
            and distance_ft(current_pos, getattr(target, "position", None)) <= 30
            and not _has_status(target, "frightened")
            and not enemy.ai_memory.get(f"demoralized:{target_key}", False)
        ):
            result = dispatch_event(
                "demoralize",
                EventContext(game=game, actor=enemy, metadata={"forced_target": target}),
            )
            used += 1 if result.consumed_action else 0
            enemy.ai_memory[f"demoralized:{target_key}"] = bool(result.success)
            if result.consumed_action:
                continue

        if polearm is not None and can_attack_from_position(game, enemy, target, polearm, current_pos):
            should_trip = remaining >= 1 and not _has_status(target, "prone") and count_adjacent_enemies_to_target(game, target) >= 2
            if should_trip:
                result = dispatch_event(
                    "enemy_trip",
                    EventContext(game=game, actor=enemy, metadata={"forced_target": target, "weapon_id": "horsechopper"}),
                )
                used += 1 if result.consumed_action else 0
                if result.consumed_action:
                    continue
            result = dispatch_event(
                "enemy_strike",
                EventContext(game=game, actor=enemy, metadata={"forced_target": target, "weapon_id": "horsechopper"}),
            )
            used += 1 if result.consumed_action else 0
            if result.consumed_action:
                continue

        if polearm is not None and remaining >= 1:
            candidates = reachable_positions(game, enemy, include_current=False)
            if candidates:
                best = max(candidates, key=lambda item: _score_reach_position(enemy, game, target, polearm, item["position"]))
                if _score_reach_position(enemy, game, target, polearm, best["position"]) >= 9:
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

from __future__ import annotations

from dataclasses import dataclass
import logging
import random
from typing import Any

logger = logging.getLogger(__name__)

DEFAULT_AWARENESS_RANGE_FEET = 30
DEFAULT_TRIGGER_THRESHOLDS = {
    "move_trigger_threshold": 0.70,
    "interaction_trigger_threshold": 0.20,
    "spell_trigger_threshold": 0.40,
    "stealth_failure_trigger_threshold": 0.20,
}


@dataclass(frozen=True)
class ExplorationCombatTriggerProfile:
    mode: str = "never"
    trigger_kind: str | None = None
    awareness_range_feet: int = DEFAULT_AWARENESS_RANGE_FEET
    reason: str = ""
    trigger_target: object | None = None


def maybe_trigger_exploration_combat(*, event_name: str, event, ctx, result) -> None:
    game = getattr(ctx, "game", None)
    actor = getattr(ctx, "actor", None)
    if game is None or actor is None:
        return
    if getattr(ctx, "in_combat", False):
        return
    if actor not in (getattr(game, "heroes", []) or []):
        return
    if getattr(game, "_exploration_combat_triggered_in_dispatch", False):
        return
    if getattr(game, "state", None).__class__.__name__ == "Combat":
        return
    if getattr(actor, "position", None) is None:
        return

    profile = _build_trigger_profile(game=game, event_name=event_name, event=event, ctx=ctx, result=result)
    if profile.mode == "never":
        return

    observers = _observing_enemies(
        game,
        actor_pos=actor.position,
        fallback_awareness_range_feet=profile.awareness_range_feet,
    )
    trigger_target = profile.trigger_target or (observers[0] if observers else None)

    if profile.mode == "immediate":
        if trigger_target is None and not _has_any_combat_ready_enemy(game):
            return
        _start_combat(game, trigger_target, reason=profile.reason)
        return

    if not observers:
        logger.debug(
            "Pomijam trigger walki po akcji '%s' (%s): brak obserwujących przeciwników.",
            event_name,
            profile.reason,
        )
        return

    roll = random.random()
    detected_by = _detecting_observer(observers, trigger_kind=profile.trigger_kind, roll=roll)
    if detected_by is not None:
        trigger_target = profile.trigger_target or detected_by
        threshold = _observer_trigger_threshold(detected_by, profile.trigger_kind)
        _start_combat(game, trigger_target, reason=f"{profile.reason}:roll={roll:.3f}:threshold={threshold:.3f}")
        return

    logger.info(
        "Akcja '%s' nie wywołała walki (%s, roll=%.3f, best_threshold=%.3f).",
        event_name,
        profile.reason,
        roll,
        _best_observer_threshold(observers, profile.trigger_kind),
    )


def _build_trigger_profile(*, game, event_name: str, event, ctx, result) -> ExplorationCombatTriggerProfile:
    tags = {str(tag or "").strip().lower() for tag in _event_tags(event, ctx)}
    action_executed = _action_executed(result)
    trigger_target = _extract_enemy_target(game, ctx, result)
    stealth_outcome = _stealth_outcome(result)

    if "stealth" in tags:
        if stealth_outcome in {"failure", "critical_failure"}:
            return ExplorationCombatTriggerProfile(
                mode="check",
                trigger_kind="stealth_failure",
                reason=f"stealth:{stealth_outcome}",
                trigger_target=trigger_target,
            )
        return ExplorationCombatTriggerProfile()

    if _is_attack_action(event_name=event_name, tags=tags):
        return ExplorationCombatTriggerProfile(
            mode="immediate",
            reason="hostile_attack",
            trigger_target=trigger_target,
        )

    if _is_spell_action(tags=tags):
        if _is_hostile_spell(event_name=event_name, tags=tags, trigger_target=trigger_target):
            return ExplorationCombatTriggerProfile(
                mode="immediate",
                reason="hostile_spell",
                trigger_target=trigger_target,
            )
        if action_executed:
            return ExplorationCombatTriggerProfile(
                mode="check",
                trigger_kind="spell",
                reason="spell_cast",
                trigger_target=trigger_target,
            )
        return ExplorationCombatTriggerProfile()

    if "move" in tags and action_executed:
        return ExplorationCombatTriggerProfile(
            mode="check",
            trigger_kind="move",
            reason="move",
            trigger_target=trigger_target,
        )

    if ("interaction" in tags or "manipulate" in tags) and action_executed:
        return ExplorationCombatTriggerProfile(
            mode="check",
            trigger_kind="interaction",
            reason="interaction",
            trigger_target=trigger_target,
        )

    return ExplorationCombatTriggerProfile()


def _event_tags(event, ctx) -> list[str]:
    getter = getattr(event, "_effective_tags", None)
    if callable(getter):
        try:
            return list(getter(ctx) or [])
        except Exception:
            logger.debug("Nie udało się pobrać tagów eventu.", exc_info=True)
    return list(getattr(event, "default_tags", None) or [])


def _action_executed(result) -> bool:
    if not getattr(result, "success", False):
        return False
    if bool(getattr(result, "consumed_action", False)):
        return True
    try:
        return int(getattr(result, "actions_spent", 0) or 0) > 0
    except Exception:
        return False


def _stealth_outcome(result) -> str | None:
    data = getattr(result, "data", None)
    if not isinstance(data, dict):
        return None
    raw = data.get("stealth_outcome")
    normalized = str(raw or "").strip().lower()
    return normalized or None


def _is_attack_action(*, event_name: str, tags: set[str]) -> bool:
    if str(event_name or "").strip().lower() == "attack":
        return False
    return (
        "attack" in tags
        or "attack_melee" in tags
        or "attack_ranged" in tags
        or "ranged_attack" in tags
        or any(tag.startswith("attack_") for tag in tags)
    )


def _is_spell_action(*, tags: set[str]) -> bool:
    return "magic" in tags or "spell" in tags


def _is_hostile_spell(*, event_name: str, tags: set[str], trigger_target: object | None) -> bool:
    if trigger_target is not None:
        return True
    hostile_markers = {"hostile", "offensive", "attack", "attack_melee", "attack_ranged", "ranged_attack", "damage"}
    if hostile_markers.intersection(tags):
        return True
    normalized_name = str(event_name or "").strip().lower()
    return normalized_name.startswith("attack_")


def _extract_enemy_target(game, ctx, result) -> object | None:
    candidates: list[Any] = []
    result_data = getattr(result, "data", None)
    if isinstance(result_data, dict):
        for key in ("combat_trigger_target", "target", "enemy"):
            candidates.append(result_data.get(key))
    metadata = getattr(ctx, "metadata", None)
    if isinstance(metadata, dict):
        for key in ("target", "enemy"):
            candidates.append(metadata.get(key))
    for candidate in candidates:
        if candidate in (getattr(game, "enemies", []) or []) and _is_enemy_combat_ready(game, candidate):
            return candidate
    return None


def _observing_enemies(game, *, actor_pos: tuple[int, int], fallback_awareness_range_feet: int) -> list[object]:
    board = getattr(game, "board", None)
    actor_rooms = set()
    if board is not None:
        try:
            actor_rooms = set(board.rooms_at(actor_pos) or ())
        except Exception:
            actor_rooms = set()

    observed: list[tuple[int, int, object]] = []
    for enemy in getattr(game, "enemies", []) or []:
        if not _is_enemy_combat_ready(game, enemy):
            continue
        enemy_pos = getattr(enemy, "position", None)
        if enemy_pos is None:
            continue
        same_room = 0
        if actor_rooms and board is not None:
            try:
                if actor_rooms.intersection(board.rooms_at(enemy_pos) or ()):
                    same_room = 1
            except Exception:
                same_room = 0
        try:
            distance_ft = _grid_distance_feet(actor_pos, enemy_pos)
        except Exception:
            continue
        awareness_range_feet = _observer_awareness_range(enemy, fallback_awareness_range_feet)
        if same_room or distance_ft <= awareness_range_feet:
            observed.append((0 if same_room else 1, distance_ft, enemy))

    observed.sort(key=lambda item: (item[0], item[1]))
    return [enemy for _same_room_rank, _distance, enemy in observed]


def _is_enemy_combat_ready(game, enemy: object) -> bool:
    checker = getattr(game, "_is_enemy_combat_ready", None)
    if callable(checker):
        try:
            return bool(checker(enemy))
        except Exception:
            return False
    if enemy is None:
        return False
    if getattr(enemy, "position", None) is None:
        return False
    try:
        return int(getattr(enemy, "hp", 1) or 0) > 0
    except Exception:
        return True


def _has_any_combat_ready_enemy(game) -> bool:
    return any(_is_enemy_combat_ready(game, enemy) for enemy in getattr(game, "enemies", []) or [])


def _start_combat(game, trigger_target: object | None, *, reason: str) -> None:
    starter = getattr(game, "start_combat", None)
    if not callable(starter):
        return
    setattr(game, "_exploration_combat_triggered_in_dispatch", True)
    logger.info("Wywołuję walkę po akcji eksploracyjnej (%s).", reason)
    try:
        starter(trigger=trigger_target)
    except Exception:
        logger.debug("Nie udało się uruchomić walki po akcji eksploracyjnej.", exc_info=True)


def _grid_distance_feet(a: tuple[int, int], b: tuple[int, int]) -> int:
    dx, dy = abs(a[0] - b[0]), abs(a[1] - b[1])
    diag = min(dx, dy)
    straight = abs(dx - dy)
    diag_cost = 5 * (diag + diag // 2)
    return diag_cost + straight * 5


def _enemy_awareness_profile(enemy: object) -> dict[str, object]:
    payload = dict(DEFAULT_TRIGGER_THRESHOLDS)
    payload["awareness_range_feet"] = DEFAULT_AWARENESS_RANGE_FEET
    raw = getattr(enemy, "awareness_profile", None)
    if isinstance(raw, dict):
        for key, value in raw.items():
            payload[str(key)] = value
    return payload


def _observer_awareness_range(enemy: object, fallback_awareness_range_feet: int) -> int:
    profile = _enemy_awareness_profile(enemy)
    try:
        return max(0, int(profile.get("awareness_range_feet") or fallback_awareness_range_feet))
    except Exception:
        return fallback_awareness_range_feet


def _observer_trigger_threshold(enemy: object, trigger_kind: str | None) -> float:
    if not trigger_kind:
        return 0.0
    profile = _enemy_awareness_profile(enemy)
    key = f"{trigger_kind}_trigger_threshold"
    raw = profile.get(key, DEFAULT_TRIGGER_THRESHOLDS.get(key, 0.0))
    try:
        return max(0.0, min(1.0, float(raw or 0.0)))
    except Exception:
        return float(DEFAULT_TRIGGER_THRESHOLDS.get(key, 0.0))


def _detecting_observer(observers: list[object], *, trigger_kind: str | None, roll: float) -> object | None:
    if not trigger_kind:
        return None
    passing = [enemy for enemy in observers if roll < _observer_trigger_threshold(enemy, trigger_kind)]
    if not passing:
        return None
    passing.sort(
        key=lambda enemy: _observer_trigger_threshold(enemy, trigger_kind),
        reverse=True,
    )
    return passing[0]


def _best_observer_threshold(observers: list[object], trigger_kind: str | None) -> float:
    if not trigger_kind or not observers:
        return 0.0
    return max(_observer_trigger_threshold(enemy, trigger_kind) for enemy in observers)

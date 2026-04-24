from __future__ import annotations

from typing import Any

from combat.hp_engine import current_hp as combat_current_hp

def _actor_uid(actor: Any) -> str:
    return str(getattr(actor, "object_id", None) or id(actor))


def current_hp_value(actor: Any) -> int | None:
    if actor is None:
        return None
    current_hp = getattr(actor, "current_hp", None)
    if callable(current_hp):
        try:
            return int(current_hp())
        except Exception:
            pass
    try:
        hp = combat_current_hp(actor)
    except Exception:
        hp = None
    if hp is not None:
        try:
            return int(hp)
        except Exception:
            return None
    raw_hp = getattr(actor, "hp", None)
    if raw_hp is None:
        return None
    try:
        return int(raw_hp)
    except Exception:
        return None


def is_targetable_actor(actor: Any) -> bool:
    if actor is None:
        return False
    if getattr(actor, "position", None) is None:
        return False
    try:
        hp = current_hp_value(actor)
        if hp is not None and hp <= 0:
            return False
    except Exception:
        return False
    checker = getattr(actor, "is_dead", None)
    if callable(checker):
        try:
            if bool(checker()):
                return False
        except Exception:
            return False
    checker = getattr(actor, "has_status", None)
    if callable(checker):
        try:
            if bool(checker("dead")) or bool(checker("unconscious")):
                return False
        except Exception:
            return False
    for status in getattr(actor, "statuses", []) or []:
        status_id = str(getattr(status, "id", status) or "").strip().lower()
        if status_id in {"dead", "unconscious", "stable"} or status_id.startswith("dying"):
            return False
    return True


def _is_alive(actor: Any) -> bool:
    return is_targetable_actor(actor)


def _animal_companions(game: Any) -> list[Any]:
    state = getattr(game, "state", None)
    mapping = getattr(state, "animal_companions", None)
    if not isinstance(mapping, dict):
        return []
    companions: list[Any] = []
    for companion in mapping.values():
        if companion is None:
            continue
        companions.append(companion)
    return companions


def hero_side_targets(game: Any, *, only_living: bool = True) -> list[Any]:
    actors: list[Any] = []
    seen: set[str] = set()
    for actor in list(getattr(game, "heroes", []) or []) + _animal_companions(game):
        uid = _actor_uid(actor)
        if uid in seen:
            continue
        seen.add(uid)
        if only_living and not _is_alive(actor):
            continue
        actors.append(actor)
    return actors


def is_hero_side_target(game: Any, actor: Any, *, only_living: bool = False) -> bool:
    if actor is None:
        return False
    for candidate in hero_side_targets(game, only_living=only_living):
        if candidate is actor:
            return True
    return False

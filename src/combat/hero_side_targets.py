from __future__ import annotations

from typing import Any


def _actor_uid(actor: Any) -> str:
    return str(getattr(actor, "object_id", None) or id(actor))


def _is_alive(actor: Any) -> bool:
    if actor is None:
        return False
    if getattr(actor, "position", None) is None:
        return False
    try:
        if int(getattr(actor, "hp", 1) or 0) <= 0:
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
    return True


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


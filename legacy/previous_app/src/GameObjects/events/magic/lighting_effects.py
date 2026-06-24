from __future__ import annotations

from typing import Any

from statuses import BLINDED_STATUS, IN_DARK_STATUS, IN_DIM_LIGHT_STATUS
from .magic_utils import grid_distance_feet


def _state(game) -> dict[str, Any]:
    current = getattr(game, "_magic_lighting", None)
    if isinstance(current, dict):
        current.setdefault("dancing_positions", set())
        current.setdefault("light_sources", {})
        current.setdefault("light_radius_feet", 30)
        return current
    state = {
        "dancing_positions": set(),
        "light_sources": {},
        "light_radius_feet": 30,
    }
    setattr(game, "_magic_lighting", state)
    return state


def clear_magic_lighting(game) -> None:
    try:
        setattr(game, "_magic_lighting", {"dancing_positions": set(), "light_sources": {}, "light_radius_feet": 30})
    except Exception:
        pass


def set_dancing_positions(game, positions: list[tuple[int, int]]) -> None:
    state = _state(game)
    state["dancing_positions"] = set(positions or [])


def set_light_source(game, actor, *, radius_feet: int = 30) -> None:
    source_id = getattr(actor, "object_id", None) or getattr(actor, "name", None) or str(id(actor))
    state = _state(game)
    state["light_radius_feet"] = max(0, int(radius_feet))
    state["light_sources"][source_id] = actor


def is_position_in_light_aura(game, pos: tuple[int, int] | None) -> bool:
    if pos is None:
        return False
    state = _state(game)
    radius = int(state.get("light_radius_feet", 30) or 30)
    sources = state.get("light_sources", {}) or {}
    for _sid, source in list(sources.items()):
        source_pos = getattr(source, "position", None)
        if source_pos is None:
            continue
        if grid_distance_feet(source_pos, pos) <= radius:
            return True
    return False


def is_position_illuminated(game, pos: tuple[int, int] | None) -> bool:
    if pos is None:
        return False
    state = _state(game)
    if pos in (state.get("dancing_positions") or set()):
        return True
    return is_position_in_light_aura(game, pos)


def apply_lighting_to_actor(game, actor) -> None:
    pos = getattr(actor, "position", None)
    if not is_position_illuminated(game, pos):
        return
    remover = getattr(actor, "remove_status", None)
    if callable(remover):
        try:
            remover(IN_DARK_STATUS)
        except Exception:
            pass
        try:
            remover(IN_DIM_LIGHT_STATUS)
        except Exception:
            pass
        try:
            remover(BLINDED_STATUS)
        except Exception:
            pass


def refresh_lighting_on_board(game) -> None:
    actors = list(getattr(game, "heroes", []) or []) + list(getattr(game, "enemies", []) or [])
    for actor in actors:
        apply_lighting_to_actor(game, actor)


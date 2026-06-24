from __future__ import annotations

from typing import Any

from .magic_utils import grid_distance_feet


def _state(game) -> dict[str, Any]:
    data = getattr(game, "_occult_runtime", None)
    if not isinstance(data, dict):
        data = {}
        try:
            game._occult_runtime = data
        except Exception:
            pass
    return data


def add_alarm_ward(
    game,
    *,
    source_id: str | None,
    source_name: str,
    center: tuple[int, int],
    radius_feet: int = 10,
    trigger_kind: str = "enemy",
) -> dict[str, Any]:
    state = _state(game)
    wards = state.setdefault("alarm_wards", [])
    ward = {
        "source_id": source_id,
        "source_name": source_name,
        "center": tuple(center),
        "radius_feet": int(radius_feet),
        "trigger_kind": trigger_kind,
        "one_shot": True,
    }
    wards.append(ward)
    return ward


def process_alarm_wards_for_move(game, mover, position: tuple[int, int] | None) -> list[str]:
    if game is None or position is None:
        return []
    state = _state(game)
    wards = list(state.get("alarm_wards", []) or [])
    if not wards:
        return []

    is_enemy = mover in getattr(game, "enemies", [])
    is_hero = mover in getattr(game, "heroes", [])
    mover_id = getattr(mover, "object_id", None) or getattr(mover, "name", None)
    mover_name = getattr(mover, "name", None) or str(mover_id or "creature")

    remaining = []
    triggered_messages: list[str] = []

    for ward in wards:
        kind = str(ward.get("trigger_kind", "enemy")).strip().lower()
        if kind == "enemy" and not is_enemy:
            remaining.append(ward)
            continue
        if kind == "hero" and not is_hero:
            remaining.append(ward)
            continue
        if mover_id is not None and mover_id == ward.get("source_id"):
            remaining.append(ward)
            continue

        center = ward.get("center")
        if not isinstance(center, tuple) or len(center) != 2:
            remaining.append(ward)
            continue
        try:
            radius = int(ward.get("radius_feet", 10) or 10)
        except Exception:
            radius = 10

        in_area = grid_distance_feet(tuple(center), tuple(position)) <= radius
        if not in_area:
            remaining.append(ward)
            continue

        source_name = ward.get("source_name") or "Caster"
        msg = f"Alarm ({source_name}): wykryto intruza ({mover_name}) na polu {position}."
        triggered_messages.append(msg)
        if not ward.get("one_shot", True):
            remaining.append(ward)

    state["alarm_wards"] = remaining

    for msg in triggered_messages:
        try:
            game.ui_log(msg)
        except Exception:
            pass

    return triggered_messages


__all__ = ["add_alarm_ward", "process_alarm_wards_for_move"]

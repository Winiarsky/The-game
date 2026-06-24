from __future__ import annotations

from dataclasses import replace
from typing import Any

from bonuses import BonusEffect, BonusType
from statuses.base import Status


def _actor_id(actor) -> str | None:
    if actor is None:
        return None
    return str(getattr(actor, "object_id", None) or getattr(actor, "name", None) or id(actor))


def _get_status(actor, status_id: str):
    if actor is None:
        return None
    getter = getattr(actor, "get_status", None)
    if callable(getter):
        try:
            return getter(status_id)
        except Exception:
            return None
    for status in getattr(actor, "statuses", []) or []:
        if getattr(status, "id", None) == status_id:
            return status
    return None


def _replace_status_data(actor, status_id: str, updates: dict[str, Any]) -> bool:
    if actor is None or not isinstance(updates, dict):
        return False
    statuses = getattr(actor, "statuses", None)
    if not isinstance(statuses, list):
        return False
    for idx, item in enumerate(statuses):
        if getattr(item, "id", None) != status_id:
            continue
        data = dict(getattr(item, "data", None) or {})
        data.update(updates)
        try:
            statuses[idx] = replace(item, data=data)
            return True
        except Exception:
            return False
    return False


def _remove_status(actor, status_id: str) -> None:
    if actor is None:
        return
    remover = getattr(actor, "remove_status", None)
    if callable(remover):
        try:
            remover(status_id)
            return
        except Exception:
            pass
    statuses = getattr(actor, "statuses", None)
    if isinstance(statuses, list):
        for idx in range(len(statuses) - 1, -1, -1):
            if getattr(statuses[idx], "id", statuses[idx]) == status_id:
                del statuses[idx]
                break


def is_ranger(actor) -> bool:
    class_name = str(getattr(actor, "class_name", "") or "").strip().lower()
    if class_name == "ranger":
        return True
    checker = getattr(actor, "has_status", None)
    if callable(checker):
        try:
            return bool(checker("ranger"))
        except Exception:
            return False
    return False


def ranger_setup(actor) -> dict[str, Any]:
    status = _get_status(actor, "ranger")
    data = getattr(status, "data", None) or {}
    raw = data.get("ranger_setup")
    if isinstance(raw, dict):
        return dict(raw)
    return {}


def hunter_edge(actor) -> str | None:
    setup = ranger_setup(actor)
    value = setup.get("hunter_edge")
    if value is None:
        value = getattr(actor, "ranger_hunter_edge", None)
    raw = str(value or "").strip().lower()
    return raw if raw in {"flurry", "precision", "outwit"} else None


def hunted_prey_id(actor) -> str | None:
    setup = ranger_setup(actor)
    value = setup.get("hunted_prey_target_id")
    if not value:
        value = getattr(actor, "ranger_hunted_prey_target_id", None)
    raw = str(value or "").strip()
    return raw or None


def hunted_prey_position(actor) -> tuple[int, int] | None:
    setup = ranger_setup(actor)
    value = setup.get("hunted_prey_position")
    if value is None:
        value = getattr(actor, "ranger_hunted_prey_position", None)
    if isinstance(value, tuple) and len(value) == 2:
        try:
            return int(value[0]), int(value[1])
        except Exception:
            return None
    if isinstance(value, list) and len(value) == 2:
        try:
            return int(value[0]), int(value[1])
        except Exception:
            return None
    return None


def is_hunted_prey(actor, target) -> bool:
    target_id = _actor_id(target)
    hunted_id = hunted_prey_id(actor)
    return bool(target_id and hunted_id and target_id == hunted_id)


def set_hunted_prey(actor, target, *, position: tuple[int, int] | None = None) -> None:
    target_id = _actor_id(target)
    payload = {
        "hunted_prey_target_id": target_id,
        "hunted_prey_position": position,
    }
    status = _get_status(actor, "ranger")
    if status is not None:
        data = dict(getattr(status, "data", None) or {})
        setup = dict(data.get("ranger_setup") or {})
        setup.update(payload)
        data["ranger_setup"] = setup
        _replace_status_data(actor, "ranger", data)
    try:
        setattr(actor, "ranger_hunted_prey_target_id", target_id)
    except Exception:
        pass
    try:
        setattr(actor, "ranger_hunted_prey_position", position)
    except Exception:
        pass


def _remove_bonuses_with_source(actor, source: str) -> None:
    bonuses = getattr(actor, "bonuses", None)
    if isinstance(bonuses, list):
        actor.bonuses = [b for b in bonuses if str(getattr(b, "source", "") or "") != source]
        return
    remover = getattr(actor, "remove_bonuses_by_source", None)
    if callable(remover):
        try:
            remover(source)
        except Exception:
            pass


def refresh_outwit_bonus(actor) -> None:
    if actor is None:
        return
    source = "ranger:outwit:ac"
    _remove_bonuses_with_source(actor, source)
    if hunter_edge(actor) != "outwit":
        return
    prey_id = hunted_prey_id(actor)
    if not prey_id:
        return
    adder = getattr(actor, "add_bonus", None)
    if not callable(adder):
        return
    try:
        adder(
            BonusEffect(
                type=BonusType.CIRCUMSTANCE,
                value=1,
                tag="ac",
                source=source,
                target_id=prey_id,
                label="outwit",
            )
        )
    except Exception:
        pass


def precision_allowed(actor, target, *, round_index: int | None) -> bool:
    if hunter_edge(actor) != "precision":
        return False
    if not is_hunted_prey(actor, target):
        return False
    if round_index is None:
        return True
    setup = ranger_setup(actor)
    applied_round = setup.get("precision_applied_round")
    applied_target = str(setup.get("precision_applied_target_id") or "")
    target_id = _actor_id(target)
    try:
        if int(applied_round) == int(round_index) and applied_target and applied_target == str(target_id):
            return False
    except Exception:
        pass
    return True


def mark_precision_applied(actor, target, *, round_index: int | None) -> None:
    target_id = _actor_id(target)
    payload = {
        "precision_applied_round": round_index,
        "precision_applied_target_id": target_id,
    }
    status = _get_status(actor, "ranger")
    if status is not None:
        data = dict(getattr(status, "data", None) or {})
        setup = dict(data.get("ranger_setup") or {})
        setup.update(payload)
        data["ranger_setup"] = setup
        _replace_status_data(actor, "ranger", data)


def monster_hunter_used_targets(actor) -> set[str]:
    setup = ranger_setup(actor)
    raw = list(setup.get("monster_hunter_used_target_ids") or [])
    return {str(item).strip() for item in raw if str(item).strip()}


def mark_monster_hunter_used(actor, target) -> None:
    target_id = _actor_id(target)
    if not target_id:
        return
    used = monster_hunter_used_targets(actor)
    used.add(str(target_id))
    status = _get_status(actor, "ranger")
    if status is None:
        return
    data = dict(getattr(status, "data", None) or {})
    setup = dict(data.get("ranger_setup") or {})
    setup["monster_hunter_used_target_ids"] = sorted(used)
    data["ranger_setup"] = setup
    _replace_status_data(actor, "ranger", data)


def _target_tags(target) -> set[str]:
    tags: set[str] = set()
    if target is None:
        return tags

    has_tag = getattr(target, "has_tag", None)
    if callable(has_tag):
        for tag in ("undead", "construct", "ooze", "incorporeal", "precision_immune", "no_vitals"):
            try:
                if bool(has_tag(tag)):
                    tags.add(tag)
            except Exception:
                continue

    raw_tags = getattr(target, "tags", None)
    if isinstance(raw_tags, (list, tuple, set)):
        for item in raw_tags:
            raw = str(item or "").strip().lower()
            if raw:
                tags.add(raw)

    enemy_type = str(getattr(target, "enemy_type", "") or "").strip().lower()
    if enemy_type:
        tags.add(enemy_type)

    return tags


def target_allows_precision_damage(target) -> bool:
    tags = _target_tags(target)
    if "precision_immune" in tags or "no_vitals" in tags:
        return False
    if tags.intersection({"undead", "construct", "ooze", "incorporeal"}):
        return False
    return True


def set_crossbow_ace_ready(actor, weapon_id: str | None, *, source: str = "hunt_prey") -> bool:
    if actor is None:
        return False
    _remove_status(actor, "crossbow_ace_ready")
    adder = getattr(actor, "add_status", None)
    if not callable(adder):
        return False
    try:
        adder(
            Status(
                id="crossbow_ace_ready",
                label="Crossbow Ace (Ready)",
                duration=2,
                source=str(source or "hunt_prey"),
                data={"weapon_id": str(weapon_id or "")},
            )
        )
    except Exception:
        return False
    return True


def clear_daily_ranger_preparations(actor) -> None:
    if actor is None:
        return
    status = _get_status(actor, "ranger")
    if status is not None:
        data = dict(getattr(status, "data", None) or {})
        setup = dict(data.get("ranger_setup") or {})
        for key in (
            "hunted_prey_target_id",
            "hunted_prey_position",
            "precision_applied_round",
            "precision_applied_target_id",
            "monster_hunter_used_target_ids",
        ):
            setup.pop(key, None)
        data["ranger_setup"] = setup
        _replace_status_data(actor, "ranger", data)

    try:
        setattr(actor, "ranger_hunted_prey_target_id", None)
    except Exception:
        pass
    try:
        setattr(actor, "ranger_hunted_prey_position", None)
    except Exception:
        pass
    _remove_status(actor, "crossbow_ace_ready")
    refresh_outwit_bonus(actor)

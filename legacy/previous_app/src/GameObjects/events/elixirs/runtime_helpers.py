from __future__ import annotations

import random
from dataclasses import replace
from typing import Any

from GameObjects.events.magic.magic_utils import grid_distance_feet
from GameObjects.interactions_mixin.skill_check_resolver import resolve_skill_check_with_sources_from_roll
from skills import Skill
from statuses import Status


def _normalize(value: object) -> str:
    return str(value or "").strip().lower().replace("-", "_").replace(" ", "_")


def _iter_statuses(actor) -> list[Status]:
    statuses = getattr(actor, "statuses", None)
    if not isinstance(statuses, list):
        return []
    return [status for status in statuses if isinstance(status, Status)]


def _status_matches(status: Status, status_id: str | None = None) -> bool:
    if not status_id:
        return True
    return _normalize(getattr(status, "id", "")) == _normalize(status_id)


def best_status_int(actor, key: str, *, status_id: str | None = None, default: int = 0) -> int:
    best = int(default)
    for status in _iter_statuses(actor):
        if not _status_matches(status, status_id=status_id):
            continue
        data = getattr(status, "data", None) or {}
        if key not in data:
            continue
        try:
            value = int(data.get(key, default) or default)
        except Exception:
            continue
        if value > best:
            best = value
    return int(best)


def any_status_flag(actor, key: str, *, status_id: str | None = None) -> bool:
    for status in _iter_statuses(actor):
        if not _status_matches(status, status_id=status_id):
            continue
        data = getattr(status, "data", None) or {}
        if bool(data.get(key, False)):
            return True
    return False


def _replace_status(actor, target_status: Status, *, new_data: dict[str, object]) -> bool:
    statuses = getattr(actor, "statuses", None)
    if not isinstance(statuses, list):
        return False
    for idx, status in enumerate(statuses):
        if status is not target_status:
            continue
        try:
            statuses[idx] = replace(status, data=dict(new_data))
            return True
        except Exception:
            return False
    return False


def _remove_status_by_id(actor, status_id: str) -> bool:
    remover = getattr(actor, "remove_status", None)
    if callable(remover):
        try:
            return bool(remover(status_id))
        except Exception:
            pass
    statuses = getattr(actor, "statuses", None)
    if not isinstance(statuses, list):
        return False
    before = len(statuses)
    filtered = [status for status in statuses if _normalize(getattr(status, "id", status)) != _normalize(status_id)]
    if len(filtered) == before:
        return False
    try:
        actor.statuses = filtered
    except Exception:
        return False
    return True


def healing_block_reason(actor) -> str | None:
    for status in _iter_statuses(actor):
        data = getattr(status, "data", None) or {}
        if not bool(data.get("healing_blocked", False)):
            continue
        reason = str(data.get("healing_blocked_reason", "") or "").strip()
        if reason:
            return reason
        label = str(getattr(status, "label", None) or getattr(status, "id", "status") or "status").strip()
        return f"Leczenie zablokowane przez {label}."
    return None


def healing_block_amount(actor) -> int:
    blocked = 0
    for status in _iter_statuses(actor):
        data = getattr(status, "data", None) or {}
        try:
            blocked += max(0, int(data.get("healing_blocked_amount", 0) or 0))
        except Exception:
            continue
    return max(0, int(blocked))


def _apply_immediate_poison_save(target, game) -> str:
    from statuses.poisoned import _shift_stage, _stage_shift_for_outcome

    poisoned = None
    for status in _iter_statuses(target):
        if _normalize(getattr(status, "id", "")) == "poisoned":
            poisoned = status
            break
    if poisoned is None:
        return "Brak aktywnej trucizny do natychmiastowego save."

    data = dict(getattr(poisoned, "data", None) or {})
    try:
        dc = int(data.get("dc", 0) or 0)
    except Exception:
        dc = 0
    if dc <= 0:
        return "Aktywna trucizna nie ma poprawnego DC."

    result = resolve_skill_check_with_sources_from_roll(
        skill_id=Skill.FORTITUDE.value,
        dc=dc,
        actor=target,
        target=None,
        tags=["poison", Skill.FORTITUDE.value],
        roll=random.randint(1, 20),
        game=game,
        apply_modifiers=True,
        consume_statuses=False,
    )
    outcome = str(getattr(result, "outcome", "failure") or "failure")

    stages = list(data.get("stages") or [])
    current_stage = int(data.get("stage", 1) or 1)
    virulent = bool(data.get("virulent", False))

    if stages:
        new_stage = _shift_stage(
            current_stage,
            _stage_shift_for_outcome(target, outcome=outcome, virulent=virulent),
            len(stages),
        )
        if new_stage <= 0:
            _remove_status_by_id(target, "poisoned")
            return f"Antidote: {outcome} - trucizna usunieta."
        data["stage"] = int(new_stage)
        _replace_status(target, poisoned, new_data=data)
        return f"Antidote: {outcome} - stage trucizny zmienia sie na {new_stage}."

    if outcome in {"success", "critical_success"}:
        _remove_status_by_id(target, "poisoned")
        return f"Antidote: {outcome} - trucizna usunieta."
    return f"Antidote: {outcome} - trucizna pozostaje aktywna."


def _apply_immediate_disease_save(target, game) -> str:
    disease_status = None
    for status in _iter_statuses(target):
        data = getattr(status, "data", None) or {}
        tags = {_normalize(tag) for tag in list(data.get("effect_tags") or [])}
        if "disease" in tags or _normalize(getattr(status, "id", "")) in {"disease", "diseased"}:
            disease_status = status
            break
    if disease_status is None:
        return "Brak aktywnej choroby do natychmiastowego save."

    data = dict(getattr(disease_status, "data", None) or {})
    try:
        dc = int(data.get("dc", 0) or 0)
    except Exception:
        dc = 0
    if dc <= 0:
        return "Aktywna choroba nie ma poprawnego DC."

    result = resolve_skill_check_with_sources_from_roll(
        skill_id=Skill.FORTITUDE.value,
        dc=dc,
        actor=target,
        target=None,
        tags=["disease", Skill.FORTITUDE.value],
        roll=random.randint(1, 20),
        game=game,
        apply_modifiers=True,
        consume_statuses=False,
    )
    outcome = str(getattr(result, "outcome", "failure") or "failure")
    if outcome in {"success", "critical_success"}:
        _remove_status_by_id(target, getattr(disease_status, "id", "disease"))
        return f"Antiplague: {outcome} - choroba usunieta."
    return f"Antiplague: {outcome} - choroba pozostaje aktywna."


def resolve_major_affliction_save(target, game, *, kind: str) -> str:
    normalized = _normalize(kind)
    if normalized == "poison":
        return _apply_immediate_poison_save(target, game)
    if normalized == "disease":
        return _apply_immediate_disease_save(target, game)
    return "Nieznany typ affliction."


def eagle_eye_auto_check(actor, game) -> list[str]:
    radius = best_status_int(actor, "eagle_eye_auto_check_radius_feet", status_id="eagle_eye", default=0)
    if radius <= 0:
        return []
    board = getattr(game, "board", None)
    origin = getattr(actor, "position", None)
    if board is None or origin is None:
        return []

    notes: list[str] = []
    seen_hidden_ids: set[int] = set()
    seen_trap_ids: set[int] = set()
    for col in range(int(getattr(board, "cols", 0) or 0)):
        for row in range(int(getattr(board, "rows", 0) or 0)):
            pos = (col, row)
            if not board.in_bounds(pos):
                continue
            if grid_distance_feet(origin, pos) > radius:
                continue
            for obj in list(getattr(board, "interactables_at", lambda _pos: [])(pos) or []):
                if getattr(obj, "hidden", False) and not getattr(obj, "revealed", False):
                    marker = id(obj)
                    if marker not in seen_hidden_ids:
                        seen_hidden_ids.add(marker)
                        dc = int(getattr(obj, "reveal_dc", 18) or 18)
                        resolution = resolve_skill_check_with_sources_from_roll(
                            skill_id=Skill.PERCEPTION.value,
                            dc=dc,
                            actor=actor,
                            target=obj,
                            tags=["perception", "search", "secret", "eagle_eye"],
                            roll=random.randint(1, 20),
                            game=game,
                            apply_modifiers=True,
                            consume_statuses=False,
                        )
                        total = int(getattr(resolution, "total", 0) or 0)
                        if hasattr(obj, "try_reveal"):
                            obj.try_reveal(total)
                        elif total >= dc:
                            obj.revealed = True
                        if getattr(obj, "revealed", False):
                            desc = (
                                getattr(obj, "description_on_reveal", None)
                                or getattr(obj, "reveal_description", None)
                                or getattr(obj, "description", None)
                                or "Wykryto ukryty obiekt."
                            )
                            notes.append(str(desc))

                is_trap_like = bool(
                    hasattr(obj, "trap_armed")
                    and callable(getattr(obj, "detect_trap", None))
                    and callable(getattr(obj, "disable_trap", None))
                )
                if not is_trap_like or not bool(getattr(obj, "trap_armed", False)) or bool(getattr(obj, "trap_detected", False)):
                    continue
                marker = id(obj)
                if marker in seen_trap_ids:
                    continue
                seen_trap_ids.add(marker)
                dc = int(getattr(obj, "trap_detection_dc", 18) or 18)
                resolution = resolve_skill_check_with_sources_from_roll(
                    skill_id=Skill.PERCEPTION.value,
                    dc=dc,
                    actor=actor,
                    target=obj,
                    tags=["perception", "trap", "search", "eagle_eye", "auto_detect"],
                    roll=random.randint(1, 20),
                    game=game,
                    apply_modifiers=True,
                    consume_statuses=False,
                )
                outcome, msg = obj.detect_trap(int(getattr(resolution, "total", 0) or 0))
                if outcome in {"success", "critical_success"}:
                    trap_name = str(getattr(obj, "trap_name", "") or "").strip() or "Pułapka"
                    notes.append(f"{trap_name}: {msg}")

    deduped: list[str] = []
    seen_messages: set[str] = set()
    for note in notes:
        normalized = str(note or "").strip()
        if not normalized or normalized in seen_messages:
            continue
        seen_messages.add(normalized)
        deduped.append(normalized)
    return deduped


__all__ = [
    "any_status_flag",
    "best_status_int",
    "eagle_eye_auto_check",
    "healing_block_amount",
    "healing_block_reason",
    "resolve_major_affliction_save",
]

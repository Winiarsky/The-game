from __future__ import annotations

from statuses.base import Status


def actor_id(actor) -> str | None:
    if actor is None:
        return None
    return getattr(actor, "object_id", None) or getattr(actor, "name", None) or str(actor)


def has_status(actor, status_id: str) -> bool:
    if actor is None:
        return False
    checker = getattr(actor, "has_status", None)
    if callable(checker):
        try:
            return bool(checker(status_id))
        except Exception:
            return False
    for status in getattr(actor, "statuses", []) or []:
        if getattr(status, "id", status) == status_id:
            return True
    return False


def get_status(actor, status_id: str):
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


def remove_statuses(target, status_id: str) -> None:
    if target is None:
        return
    remover = getattr(target, "remove_status", None)
    if callable(remover):
        while True:
            try:
                if not bool(remover(status_id)):
                    break
            except Exception:
                break
        return
    statuses = getattr(target, "statuses", None)
    if not isinstance(statuses, list) or not statuses:
        return
    try:
        target.statuses = [status for status in statuses if getattr(status, "id", None) != status_id]
    except Exception:
        pass


def is_bard(actor) -> bool:
    if has_status(actor, "bard"):
        return True
    class_name = str(getattr(actor, "class_name", "") or "").strip().lower()
    return class_name == "bard"


def get_focus_points(actor) -> int:
    raw = getattr(actor, "focus_point", None)
    if raw is None and is_bard(actor):
        try:
            setattr(actor, "focus_point", 1)
        except Exception:
            return 0
        raw = 1
    try:
        return max(0, int(raw or 0))
    except Exception:
        return 0


def set_focus_points(actor, value: int) -> None:
    try:
        setattr(actor, "focus_point", max(0, int(value or 0)))
    except Exception:
        return


def add_status(actor, status: Status) -> bool:
    if actor is None:
        return False
    adder = getattr(actor, "add_status", None)
    if not callable(adder):
        return False
    try:
        return bool(adder(status))
    except Exception:
        return False


def composition_blocked(actor) -> bool:
    return has_status(actor, "composition_locked")


def lingering_ready_rounds(actor) -> int | None:
    status = get_status(actor, "lingering_composition_ready")
    if status is None:
        return None
    data = getattr(status, "data", None) or {}
    try:
        rounds = int(data.get("composition_rounds", 0) or 0)
    except Exception:
        rounds = 0
    return rounds if rounds > 0 else None


def consume_lingering_ready(actor, *, default_rounds: int = 1) -> int:
    rounds = lingering_ready_rounds(actor)
    remove_statuses(actor, "lingering_composition_ready")
    if rounds is None:
        return max(1, int(default_rounds or 1))
    return max(1, int(rounds))


def set_lingering_ready(actor, *, rounds: int, source: str) -> bool:
    remove_statuses(actor, "lingering_composition_ready")
    return add_status(
        actor,
        Status(
            id="lingering_composition_ready",
            label=f"Lingering Composition ({max(1, int(rounds))} rundy)",
            duration=1,
            source=source,
            data={
                "composition_rounds": max(1, int(rounds)),
                "duration_tick_phase": "turn_end",
                "source_id": actor_id(actor),
                "effect_tags": ["composition", "metamagic", "bard"],
            },
        ),
    )


def set_composition_lock(actor, *, source: str) -> bool:
    remove_statuses(actor, "composition_locked")
    return add_status(
        actor,
        Status(
            id="composition_locked",
            label="Composition Locked",
            duration=1,
            source=source,
            data={
                "duration_tick_phase": "turn_end",
                "source_id": actor_id(actor),
                "effect_tags": ["composition", "bard"],
            },
        ),
    )

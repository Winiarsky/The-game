from __future__ import annotations

from typing import Any

from statuses import HiddenStatus, OBSERVABLE_STATUS, STEALTH_STATUS, UndetectedStatus


def _status_id(status: object) -> str:
    return str(getattr(status, "id", status) or "").strip().lower()


def has_status_id(actor: Any, status_id: str) -> bool:
    if actor is None:
        return False
    wanted = str(status_id or "").strip().lower()
    has_status = getattr(actor, "has_status", None)
    if callable(has_status):
        try:
            if bool(has_status(wanted)):
                return True
        except Exception:
            pass
    for status in list(getattr(actor, "statuses", []) or []):
        if _status_id(status) == wanted:
            return True
    return False


def has_combat_stealth_state(actor: Any) -> bool:
    return any(has_status_id(actor, status_id) for status_id in ("hidden", "undetected", "unnoticed"))


def clear_combat_stealth(
    actor: Any,
    *,
    clear_stealth: bool = False,
    add_observable: bool = False,
) -> bool:
    if actor is None:
        return False
    target_ids = {"hidden", "undetected", "unnoticed"}
    if clear_stealth:
        target_ids.add(STEALTH_STATUS.id)
    removed_any = False

    remover = getattr(actor, "remove_status", None)
    if callable(remover):
        for status_id in tuple(target_ids):
            try:
                removed_any = bool(remover(status_id)) or removed_any
            except Exception:
                continue

    statuses = getattr(actor, "statuses", None)
    if isinstance(statuses, list):
        kept = [item for item in statuses if _status_id(item) not in target_ids]
        removed_any = len(kept) != len(statuses) or removed_any
        try:
            actor.statuses = kept
        except Exception:
            pass

    if add_observable:
        try:
            if hasattr(actor, "remove_status"):
                actor.remove_status(OBSERVABLE_STATUS.id)
        except Exception:
            pass
        adder = getattr(actor, "add_status", None)
        if callable(adder):
            try:
                adder(OBSERVABLE_STATUS)
            except Exception:
                pass
        else:
            statuses = getattr(actor, "statuses", None)
            if isinstance(statuses, list) and not any(_status_id(item) == OBSERVABLE_STATUS.id for item in statuses):
                statuses.append(OBSERVABLE_STATUS)

    return removed_any


def apply_combat_stealth_state(actor: Any, *, mode: str, source: str = "stealth") -> bool:
    if actor is None:
        return False
    normalized = str(mode or "").strip().lower()
    if normalized not in {"hidden", "undetected"}:
        return False

    clear_combat_stealth(actor, clear_stealth=False, add_observable=False)
    try:
        actor.remove_status(OBSERVABLE_STATUS.id)
    except Exception:
        pass

    source_id = str(getattr(actor, "object_id", None) or getattr(actor, "name", None) or "")
    status_obj = (
        HiddenStatus(source=source, source_id=source_id)
        if normalized == "hidden"
        else UndetectedStatus(source=source, source_id=source_id)
    )

    adder = getattr(actor, "add_status", None)
    if callable(adder):
        try:
            return bool(adder(status_obj))
        except Exception:
            return False

    statuses = getattr(actor, "statuses", None)
    if not isinstance(statuses, list):
        return False
    statuses.append(status_obj)
    return True

from __future__ import annotations

from dataclasses import replace
from typing import Any

from GameObjects.interactions_mixin import prompt_for_roll
from combat.degree_of_success import natural_shift_from_roll, resolve_outcome
from combat.hp_engine import computed_max_hp
from combat.hp_engine import current_hp as hp_current_hp
from combat.hp_engine import uses_wounds_model

from .base import Status


def _iter_statuses(actor: Any) -> list[Status]:
    statuses = getattr(actor, "statuses", None)
    if not isinstance(statuses, list):
        return []
    result: list[Status] = []
    for status in statuses:
        if isinstance(status, Status):
            result.append(status)
    return result


def _status_id(status: Status) -> str:
    return str(getattr(status, "id", "") or "").strip().lower()


def _has_status(actor: Any, status_id: str) -> bool:
    checker = getattr(actor, "has_status", None)
    if callable(checker):
        try:
            return bool(checker(status_id))
        except Exception:
            return False
    wanted = str(status_id or "").strip().lower()
    return any(_status_id(s) == wanted for s in _iter_statuses(actor))


def _remove_status(actor: Any, status_id: str) -> None:
    remover = getattr(actor, "remove_status", None)
    if callable(remover):
        try:
            remover(status_id)
            return
        except Exception:
            pass
    statuses = getattr(actor, "statuses", None)
    if isinstance(statuses, list):
        wanted = str(status_id or "").strip().lower()
        actor.statuses = [s for s in statuses if _status_id(s) != wanted]


def _remove_statuses_by_prefix(actor: Any, prefix: str) -> None:
    statuses = getattr(actor, "statuses", None)
    if not isinstance(statuses, list):
        return
    wanted = str(prefix or "").strip().lower()
    actor.statuses = [s for s in statuses if not _status_id(s).startswith(wanted)]


def _add_status(actor: Any, status: Status) -> None:
    adder = getattr(actor, "add_status", None)
    if callable(adder):
        try:
            adder(status)
            return
        except Exception:
            pass
    statuses = getattr(actor, "statuses", None)
    if isinstance(statuses, list):
        statuses.append(status)


def _replace_status(actor: Any, status_id: str, *, data_updates: dict[str, Any]) -> None:
    statuses = getattr(actor, "statuses", None)
    if not isinstance(statuses, list):
        return
    wanted = str(status_id or "").strip().lower()
    for idx, status in enumerate(statuses):
        if _status_id(status) != wanted:
            continue
        data = dict(getattr(status, "data", None) or {})
        data.update(data_updates)
        statuses[idx] = replace(status, data=data)
        return


def dying_value(actor: Any) -> int:
    best = 0
    for status in _iter_statuses(actor):
        sid = _status_id(status)
        if sid == "dying":
            try:
                best = max(best, int((getattr(status, "data", None) or {}).get("value", 0) or 0))
            except Exception:
                pass
            continue
        if not sid.startswith("dying_"):
            continue
        try:
            val = int(sid.split("_", 1)[1])
        except Exception:
            continue
        if val > best:
            best = val
    return max(0, best)


def wounded_value(actor: Any) -> int:
    for status in _iter_statuses(actor):
        if _status_id(status) != "wounded":
            continue
        data = getattr(status, "data", None) or {}
        try:
            return max(0, int(data.get("value", 0) or 0))
        except Exception:
            return 0
    return 0


def is_dead(actor: Any) -> bool:
    if actor is None:
        return False
    if _has_status(actor, "dead"):
        return True
    hp = getattr(actor, "hp", None)
    if hp is not None:
        try:
            if int(hp) <= 0 and not hasattr(actor, "wounds"):
                return True
        except Exception:
            pass
    return False


def is_unconscious(actor: Any) -> bool:
    return _has_status(actor, "unconscious")


def is_stable(actor: Any) -> bool:
    return _has_status(actor, "stable")


def death_threshold(actor: Any) -> int:
    return 5 if _has_status(actor, "diehard") else 4


def recovery_dc(actor: Any) -> int:
    base = 10 + dying_value(actor)
    if _has_status(actor, "toughness"):
        base -= 1
    return max(5, base)


def current_hp(actor: Any) -> tuple[int | None, int | None, bool]:
    """Return (current_hp, max_hp, uses_wounds_model)."""
    hp = hp_current_hp(actor)
    if hp is None:
        return None, None, False
    max_hp = computed_max_hp(actor)
    return int(hp), max_hp, bool(uses_wounds_model(actor))


def _ensure_unconscious(actor: Any, *, source: str | None = None) -> None:
    if _has_status(actor, "unconscious"):
        return
    _add_status(
        actor,
        Status(
            id="unconscious",
            label="Unconscious",
            source=source,
            data={"from_dying": True},
        ),
    )


def set_wounded(actor: Any, value: int, *, source: str | None = None) -> int:
    amount = max(0, int(value or 0))
    _remove_status(actor, "wounded")
    if amount <= 0:
        return 0
    _add_status(
        actor,
        Status(
            id="wounded",
            label=f"Wounded {amount}",
            source=source,
            data={"value": amount},
        ),
    )
    return amount


def increase_wounded(actor: Any, amount: int = 1, *, source: str | None = None) -> int:
    new_val = wounded_value(actor) + max(0, int(amount or 0))
    return set_wounded(actor, new_val, source=source)


def clear_dying(actor: Any) -> None:
    _remove_statuses_by_prefix(actor, "dying")


def set_dying(actor: Any, value: int, *, source: str | None = None) -> int:
    amount = max(0, int(value or 0))
    clear_dying(actor)
    _remove_status(actor, "stable")
    if amount <= 0:
        return 0
    _add_status(
        actor,
        Status(
            id=f"dying_{amount}",
            label=f"Dying {amount}",
            source=source,
            data={"value": amount},
        ),
    )
    _ensure_unconscious(actor, source=source)
    return amount


def mark_dead(actor: Any, *, source: str | None = None, reason: str | None = None) -> None:
    if _has_status(actor, "dead"):
        return
    clear_dying(actor)
    _remove_status(actor, "stable")
    _remove_status(actor, "unconscious")
    _add_status(
        actor,
        Status(
            id="dead",
            label="Dead",
            source=source,
            data={"reason": str(reason or "")},
        ),
    )


def _try_orc_ferocity(actor: Any, *, source: str | None = None) -> bool:
    if not _has_status(actor, "orc_ferocity"):
        return False
    statuses = _iter_statuses(actor)
    orc = next((s for s in statuses if _status_id(s) == "orc_ferocity"), None)
    data = dict(getattr(orc, "data", None) or {}) if orc is not None else {}
    if bool(data.get("used_today", False)):
        return False

    cur_hp, max_hp, uses_wounds = current_hp(actor)
    if cur_hp is None:
        return False
    if uses_wounds and max_hp is not None and max_hp > 0:
        try:
            setattr(actor, "wounds", max(0, max_hp - 1))
        except Exception:
            return False
    elif hasattr(actor, "hp"):
        try:
            setattr(actor, "hp", 1)
        except Exception:
            return False
    else:
        return False

    _replace_status(actor, "orc_ferocity", data_updates={"used_today": True})
    increase_wounded(actor, 1, source=source)
    clear_dying(actor)
    _remove_status(actor, "stable")
    _remove_status(actor, "unconscious")
    return True


def on_reduced_to_zero(
    actor: Any,
    *,
    source: str | None = None,
    critical: bool = False,
    nonlethal: bool = False,
) -> dict[str, Any]:
    if actor is None:
        return {"dead": False, "dying": 0, "message": ""}
    if is_dead(actor):
        return {"dead": True, "dying": 0, "message": "Already dead."}

    if nonlethal:
        _ensure_unconscious(actor, source=source)
        return {"dead": False, "dying": 0, "message": "Knocked out (nonlethal)."}

    if _try_orc_ferocity(actor, source=source):
        return {"dead": False, "dying": 0, "message": "Orc Ferocity keeps actor at 1 HP."}

    current_dying = dying_value(actor)
    crit_inc = 1 if bool(critical) else 0
    if current_dying > 0:
        new_dying = current_dying + 1 + crit_inc
    else:
        new_dying = 1 + wounded_value(actor) + crit_inc

    final_dying = set_dying(actor, new_dying, source=source)
    if final_dying >= death_threshold(actor):
        mark_dead(actor, source=source, reason="dying_threshold")
        return {"dead": True, "dying": final_dying, "message": "Actor died."}

    return {"dead": False, "dying": final_dying, "message": f"Actor is dying {final_dying}."}


def lose_dying(actor: Any, *, source: str | None = None, keep_unconscious: bool = True) -> None:
    if dying_value(actor) <= 0:
        return
    clear_dying(actor)
    increase_wounded(actor, 1, source=source)
    if keep_unconscious:
        _ensure_unconscious(actor, source=source)
        if not _has_status(actor, "stable"):
            _add_status(actor, Status(id="stable", label="Stable", source=source))


def on_heal(actor: Any, *, source: str | None = None) -> dict[str, Any]:
    cur_hp, _max_hp, _uses_wounds = current_hp(actor)
    if cur_hp is None:
        return {"changed": False, "message": ""}

    had_dying = dying_value(actor) > 0
    if cur_hp > 0:
        if had_dying:
            lose_dying(actor, source=source, keep_unconscious=False)
        _remove_status(actor, "unconscious")
        _remove_status(actor, "stable")
        return {
            "changed": had_dying,
            "message": "Recovered above 0 HP." if had_dying else "",
        }
    return {"changed": False, "message": ""}


def _degree_of_success(total: int, dc: int, *, natural: int | None = None) -> str:
    return resolve_outcome(total, dc, natural_shift=natural_shift_from_roll(natural))


def run_recovery_check(actor: Any, *, source: str | None = "recovery_check") -> dict[str, Any]:
    current = dying_value(actor)
    if current <= 0 or is_dead(actor):
        return {"processed": False, "message": ""}
    if is_stable(actor):
        return {"processed": False, "message": ""}

    dc = recovery_dc(actor)
    raw_roll = prompt_for_roll(
        f"Recovery Check: Dying {current}, DC {dc}. Podaj wynik k20:",
        layout="test",
        answer_placeholder="Wynik k20",
    )
    try:
        natural = int(raw_roll or 0)
    except Exception:
        natural = 0
    total = natural
    outcome = _degree_of_success(total, dc, natural=natural)

    if outcome == "critical_success":
        next_val = max(0, current - 2)
    elif outcome == "success":
        next_val = max(0, current - 1)
    elif outcome == "critical_failure":
        next_val = current + 2
    else:
        next_val = current + 1

    if next_val <= 0:
        lose_dying(actor, source=source, keep_unconscious=True)
        return {
            "processed": True,
            "message": f"Recovery check {outcome}: Dying {current} -> stable, wounded {wounded_value(actor)}.",
            "outcome": outcome,
        }

    set_dying(actor, next_val, source=source)
    if next_val >= death_threshold(actor):
        mark_dead(actor, source=source, reason="recovery_check_failed")
        return {
            "processed": True,
            "message": f"Recovery check {outcome}: Dying {current} -> {next_val}. Actor dies.",
            "outcome": outcome,
        }

    return {
        "processed": True,
        "message": f"Recovery check {outcome}: Dying {current} -> {next_val}.",
        "outcome": outcome,
    }


__all__ = [
    "dying_value",
    "wounded_value",
    "is_dead",
    "is_unconscious",
    "is_stable",
    "death_threshold",
    "recovery_dc",
    "current_hp",
    "set_wounded",
    "increase_wounded",
    "clear_dying",
    "set_dying",
    "mark_dead",
    "lose_dying",
    "on_reduced_to_zero",
    "on_heal",
    "run_recovery_check",
]

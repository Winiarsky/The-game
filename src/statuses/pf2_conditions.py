from __future__ import annotations

from dataclasses import replace
from typing import Any, Iterable, Sequence

from bonuses import BonusEffect, BonusType
from skills import Skill

from .base import Status
from .clumsy import ClumsyStatus
from .speed_penalty import SpeedPenaltyStatus


_MENTAL_SKILLS = {
    Skill.ARCANA.value,
    Skill.NATURE.value,
    Skill.OCCULTISM.value,
    Skill.RELIGION.value,
    Skill.SOCIETY.value,
    Skill.DIPLOMACY.value,
    Skill.DECEPTION.value,
    Skill.INTIMIDATION.value,
    Skill.PERFORMANCE.value,
    Skill.WILL.value,
}


_DEFENSIVE_TAGS = (
    Skill.FORTITUDE.value,
    Skill.REFLEX.value,
    Skill.WILL.value,
)

_SCALED_CONDITION_RULES: dict[str, tuple[str, str]] = {
    "frightened": ("frightened_value", "Frightened"),
    "sickened": ("sickened_value", "Sickened"),
    "slowed": ("slowed_value", "Slowed"),
    "quickened": ("quickened_value", "Quickened"),
    "stupefied": ("stupefied_value", "Stupefied"),
    "drained": ("drained_value", "Drained"),
    "doomed": ("doomed_value", "Doomed"),
    "enfeebled": ("enfeebled_value", "Enfeebled"),
}

_PHASE_ALIASES = {
    "start": "turn_start",
    "start_turn": "turn_start",
    "turn_start": "turn_start",
    "end": "turn_end",
    "end_turn": "turn_end",
    "turn_end": "turn_end",
    "daily": "daily_preparation",
    "daily_preparation": "daily_preparation",
    "daily_prep": "daily_preparation",
}


def _iter_statuses(actor: Any) -> Iterable[Status]:
    statuses = getattr(actor, "statuses", None)
    if not isinstance(statuses, list):
        return []
    return [s for s in statuses if isinstance(s, Status)]


def _status_id(status: Status) -> str:
    return str(getattr(status, "id", "") or "").strip().lower()


def _status_int_value(status: Status, key: str, default: int = 0) -> int:
    data = getattr(status, "data", None) or {}
    try:
        return int(data.get(key, default) or default)
    except Exception:
        return int(default)


def _best_value(actor: Any, status_id: str, key: str, fallback: int = 0) -> int:
    best = 0
    wanted = str(status_id or "").strip().lower()
    for status in _iter_statuses(actor):
        if _status_id(status) != wanted:
            continue
        val = _status_int_value(status, key, fallback)
        if val > best:
            best = val
    return int(best)


def _phase_name(raw: str | None) -> str:
    key = str(raw or "").strip().lower()
    if not key:
        return "turn_start"
    return _PHASE_ALIASES.get(key, key)


def _status_tick_phase(status: Status) -> str:
    data = getattr(status, "data", None) or {}
    phase = data.get("duration_tick_phase", data.get("tick_phase", "turn_start"))
    return _phase_name(str(phase or "turn_start"))


def _actor_log(actor: Any, message: str) -> None:
    logger_fn = getattr(actor, "_ui_log", None)
    if callable(logger_fn):
        try:
            logger_fn(message)
            return
        except Exception:
            pass
    game = getattr(actor, "game", None)
    if game is not None:
        game_log = getattr(game, "ui_log", None)
        if callable(game_log):
            try:
                game_log(message)
            except Exception:
                pass


def _condition_components_label(components: list[tuple[str, int]]) -> str:
    if not components:
        return "conditions"
    parts = [f"{name} -{int(value)}" for name, value in components if int(value) > 0]
    if not parts:
        return "conditions"
    return f"conditions ({', '.join(parts)})"


def _pick_strongest_status(statuses: list[Status], key: str, fallback: int) -> Status | None:
    if not statuses:
        return None

    def _score(status: Status) -> tuple[int, int]:
        value = _status_int_value(status, key, fallback)
        duration = getattr(status, "duration", None)
        try:
            dur = int(duration) if duration is not None else -1
        except Exception:
            dur = -1
        return value, dur

    return max(statuses, key=_score)


# --- Status constructors ---

def OffGuardStatus(*, source: str | None = None, source_id: str | None = None, duration: int | None = None) -> Status:
    return Status(
        id="off_guard",
        label="Off-Guard",
        duration=duration,
        source=source,
        data={"ac_penalty": 2, "source_id": source_id, "effect_tags": ["off_guard", "flat_footed"]},
    )


def DazzledStatus(*, duration: int | None = None, source: str | None = None, source_id: str | None = None) -> Status:
    return Status(
        id="dazzled",
        label="Dazzled",
        duration=duration,
        source=source,
        data={"source_id": source_id, "effect_tags": ["dazzled", "visual"]},
    )


def FrightenedStatus(
    *,
    value: int,
    duration: int | None = None,
    source: str | None = None,
    source_id: str | None = None,
) -> Status:
    amount = max(1, int(value))
    return Status(
        id="frightened",
        label=f"Frightened {amount}",
        duration=duration,
        source=source,
        data={"frightened_value": amount, "source_id": source_id, "effect_tags": ["fear", "mental"]},
        stacks=True,
    )


def SickenedStatus(
    *,
    value: int,
    duration: int | None = None,
    source: str | None = None,
    source_id: str | None = None,
) -> Status:
    amount = max(1, int(value))
    return Status(
        id="sickened",
        label=f"Sickened {amount}",
        duration=duration,
        source=source,
        data={"sickened_value": amount, "source_id": source_id, "effect_tags": ["sickened", "status_penalty"]},
        stacks=True,
    )


def SlowedStatus(
    *,
    value: int,
    duration: int | None = None,
    source: str | None = None,
    source_id: str | None = None,
) -> Status:
    amount = max(1, int(value))
    return Status(
        id="slowed",
        label=f"Slowed {amount}",
        duration=duration,
        source=source,
        data={"slowed_value": amount, "source_id": source_id, "effect_tags": ["slowed"]},
        stacks=True,
    )


def QuickenedStatus(
    *,
    value: int = 1,
    duration: int | None = None,
    source: str | None = None,
    source_id: str | None = None,
    restricted_to_tags: Sequence[str] | None = None,
) -> Status:
    amount = max(1, int(value))
    return Status(
        id="quickened",
        label=f"Quickened {amount}",
        duration=duration,
        source=source,
        data={
            "quickened_value": amount,
            "source_id": source_id,
            "restricted_to_tags": list(restricted_to_tags or []),
            "effect_tags": ["quickened"],
        },
        stacks=True,
    )


def StupefiedStatus(
    *,
    value: int,
    duration: int | None = None,
    source: str | None = None,
    source_id: str | None = None,
) -> Status:
    amount = max(1, int(value))
    return Status(
        id="stupefied",
        label=f"Stupefied {amount}",
        duration=duration,
        source=source,
        data={"stupefied_value": amount, "source_id": source_id, "effect_tags": ["stupefied", "mental"]},
        stacks=True,
    )


def DrainedStatus(
    *,
    value: int,
    duration: int | None = None,
    source: str | None = None,
    source_id: str | None = None,
) -> Status:
    amount = max(1, int(value))
    return Status(
        id="drained",
        label=f"Drained {amount}",
        duration=duration,
        source=source,
        data={"drained_value": amount, "source_id": source_id, "effect_tags": ["drained"]},
        stacks=True,
    )


def DoomedStatus(
    *,
    value: int,
    duration: int | None = None,
    source: str | None = None,
    source_id: str | None = None,
) -> Status:
    amount = max(1, int(value))
    return Status(
        id="doomed",
        label=f"Doomed {amount}",
        duration=duration,
        source=source,
        data={"doomed_value": amount, "source_id": source_id, "effect_tags": ["doomed"]},
        stacks=True,
    )


def ConfusedStatus(*, duration: int | None = None, source: str | None = None, source_id: str | None = None) -> Status:
    return Status(
        id="confused",
        label="Confused",
        duration=duration,
        source=source,
        data={"source_id": source_id, "effect_tags": ["confused", "mental"]},
    )


def ControlledStatus(
    *,
    duration: int | None = None,
    source: str | None = None,
    source_id: str | None = None,
    controller_id: str | None = None,
) -> Status:
    return Status(
        id="controlled",
        label="Controlled",
        duration=duration,
        source=source,
        data={"source_id": source_id, "controller_id": controller_id, "effect_tags": ["controlled", "mental"]},
    )


def FascinatedStatus(
    *,
    duration: int | None = None,
    source: str | None = None,
    source_id: str | None = None,
    focus_target_id: str | None = None,
) -> Status:
    return Status(
        id="fascinated",
        label="Fascinated",
        duration=duration,
        source=source,
        data={"source_id": source_id, "focus_target_id": focus_target_id, "effect_tags": ["fascinated", "mental"]},
    )


def FatiguedStatus(*, duration: int | None = None, source: str | None = None, source_id: str | None = None) -> Status:
    return Status(
        id="fatigued",
        label="Fatigued",
        duration=duration,
        source=source,
        data={"source_id": source_id, "fatigued_value": 1, "effect_tags": ["fatigued"]},
    )


def FleeingStatus(
    *,
    duration: int | None = None,
    source: str | None = None,
    source_id: str | None = None,
    flee_from_id: str | None = None,
) -> Status:
    return Status(
        id="fleeing",
        label="Fleeing",
        duration=duration,
        source=source,
        data={"source_id": source_id, "flee_from_id": flee_from_id, "effect_tags": ["fleeing", "fear"]},
    )


def HiddenStatus(*, duration: int | None = None, source: str | None = None, source_id: str | None = None) -> Status:
    return Status(
        id="hidden",
        label="Hidden",
        duration=duration,
        source=source,
        data={"source_id": source_id, "flat_check_dc": 11, "effect_tags": ["hidden", "concealment"]},
    )


def UndetectedStatus(*, duration: int | None = None, source: str | None = None, source_id: str | None = None) -> Status:
    return Status(
        id="undetected",
        label="Undetected",
        duration=duration,
        source=source,
        data={"source_id": source_id, "flat_check_dc": 11, "effect_tags": ["undetected", "stealth"]},
    )


def UnnoticedStatus(*, duration: int | None = None, source: str | None = None, source_id: str | None = None) -> Status:
    return Status(
        id="unnoticed",
        label="Unnoticed",
        duration=duration,
        source=source,
        data={"source_id": source_id, "effect_tags": ["unnoticed", "stealth"]},
    )


def InvisibleStatus(*, duration: int | None = None, source: str | None = None, source_id: str | None = None) -> Status:
    return Status(
        id="invisible",
        label="Invisible",
        duration=duration,
        source=source,
        data={"source_id": source_id, "flat_check_dc": 11, "effect_tags": ["invisible", "concealment"]},
    )


def ParalyzedStatus(*, duration: int | None = None, source: str | None = None, source_id: str | None = None) -> Status:
    return Status(
        id="paralyzed",
        label="Paralyzed",
        duration=duration,
        source=source,
        data={"source_id": source_id, "effect_tags": ["paralyzed"]},
    )


def PetrifiedStatus(*, source: str | None = None, source_id: str | None = None) -> Status:
    return Status(id="petrified", label="Petrified", source=source, data={"source_id": source_id, "effect_tags": ["petrified"]})


def EncumberedStatus(*, duration: int | None = None, source: str | None = None, source_id: str | None = None) -> Status:
    return Status(
        id="encumbered",
        label="Encumbered",
        duration=duration,
        source=source,
        data={
            "source_id": source_id,
            "grants_statuses": [SpeedPenaltyStatus(penalty_feet=10, source=source or "encumbered"), ClumsyStatus(value=1, source=source or "encumbered")],
            "effect_tags": ["encumbered"],
        },
    )


def BrokenStatus(*, source: str | None = None, source_id: str | None = None) -> Status:
    return Status(id="broken", label="Broken", source=source, data={"source_id": source_id, "effect_tags": ["broken", "item"]})


def normalize_condition_stacks(actor: Any, *, log_changes: bool = False) -> int:
    statuses = getattr(actor, "statuses", None)
    if not isinstance(statuses, list) or not statuses:
        return 0

    removed = 0
    added = 0
    current = list(statuses)

    for status_id, (value_key, label_prefix) in _SCALED_CONDITION_RULES.items():
        same = [s for s in current if _status_id(s) == status_id]
        if len(same) <= 1:
            continue
        strongest = _pick_strongest_status(same, value_key, 1)
        if strongest is None:
            continue
        best_val = max(1, _status_int_value(strongest, value_key, 1))
        kept: list[Status] = []
        kept_one = False
        for status in current:
            if _status_id(status) != status_id:
                kept.append(status)
                continue
            if not kept_one and status is strongest:
                data = dict(getattr(status, "data", None) or {})
                data[value_key] = best_val
                kept.append(replace(status, label=f"{label_prefix} {best_val}", data=data))
                kept_one = True
                continue
            removed += 1
        current = kept
        if log_changes:
            _actor_log(actor, f"{label_prefix}: rozstrzygnięto stackowanie (pozostaje {best_val}).")

    ids = {_status_id(status) for status in current}
    if "unnoticed" in ids:
        next_list = [s for s in current if _status_id(s) not in {"hidden", "undetected"}]
        removed_hidden = len(current) - len(next_list)
        if removed_hidden > 0:
            removed += removed_hidden
            current = next_list
            if log_changes:
                _actor_log(actor, "Unnoticed: usunięto słabsze statusy skradania (hidden/undetected).")
    else:
        ids = {_status_id(status) for status in current}
        if "undetected" in ids and "hidden" in ids:
            next_list = [s for s in current if _status_id(s) != "hidden"]
            removed_hidden = len(current) - len(next_list)
            if removed_hidden > 0:
                removed += removed_hidden
                current = next_list
                if log_changes:
                    _actor_log(actor, "Undetected: usunięto słabszy status hidden.")

    try:
        from .death_dying import dying_value
    except Exception:
        dying_value = None  # type: ignore[assignment]

    ids = {_status_id(status) for status in current}
    if "dead" in ids:
        next_list = [s for s in current if _status_id(s) not in {"stable", "unconscious"} and not _status_id(s).startswith("dying")]
        removed_dead_conflicts = len(current) - len(next_list)
        if removed_dead_conflicts > 0:
            removed += removed_dead_conflicts
            current = next_list
    elif callable(dying_value):
        try:
            dying = int(dying_value(actor) or 0)
        except Exception:
            dying = 0
        if dying > 0:
            next_list = [s for s in current if _status_id(s) != "stable"]
            removed_stable = len(current) - len(next_list)
            if removed_stable > 0:
                removed += removed_stable
                current = next_list
                if log_changes:
                    _actor_log(actor, "Dying: status Stable usunięty (nie może współistnieć).")
            if not any(_status_id(s) == "unconscious" for s in current):
                current.append(Status(id="unconscious", label="Unconscious", data={"from_dying": True}))
                added += 1
                if log_changes:
                    _actor_log(actor, "Dying: dodano status Unconscious.")

    if removed > 0 or added > 0:
        try:
            actor.statuses = current
        except Exception:
            pass
    return int(removed + added)


def tick_condition_durations(actor: Any, *, phase: str = "turn_start", log_changes: bool = False) -> int:
    statuses = getattr(actor, "statuses", None)
    if not isinstance(statuses, list) or not statuses:
        return 0

    target_phase = _phase_name(phase)
    kept: list[Status] = []
    removed = 0
    changed = 0
    for status in statuses:
        duration = getattr(status, "duration", None)
        if duration is None:
            kept.append(status)
            continue
        if _status_tick_phase(status) != target_phase:
            kept.append(status)
            continue
        try:
            turns = int(duration) - 1
        except Exception:
            kept.append(status)
            continue
        if turns <= 0:
            removed += 1
            changed += 1
            clear_temp_hp = getattr(actor, "_clear_temp_hp_for_status", None)
            if callable(clear_temp_hp):
                try:
                    clear_temp_hp(status)
                except Exception:
                    pass
            if log_changes:
                label = str(getattr(status, "label", "") or getattr(status, "id", "status"))
                source = str(getattr(status, "source", "") or "")
                source_note = f", źródło: {source}" if source else ""
                _actor_log(actor, f"Wygasa status: {label} (faza: {target_phase}{source_note}).")
            continue
        kept.append(replace(status, duration=turns))
        changed += 1
    if changed > 0:
        try:
            actor.statuses = kept
        except Exception:
            pass
    return int(removed)


def apply_daily_preparation_conditions(actor: Any, *, log_changes: bool = False) -> int:
    statuses = getattr(actor, "statuses", None)
    if not isinstance(statuses, list) or not statuses:
        return 0

    changed = 0
    doomed = doomed_value(actor)
    if doomed > 0:
        strongest = _pick_strongest_status([s for s in statuses if _status_id(s) == "doomed"], "doomed_value", 1)
        if strongest is not None:
            next_val = max(0, doomed - 1)
            filtered = [s for s in statuses if _status_id(s) != "doomed"]
            if next_val > 0:
                data = dict(getattr(strongest, "data", None) or {})
                data["doomed_value"] = next_val
                filtered.append(replace(strongest, label=f"Doomed {next_val}", data=data))
            statuses = filtered
            changed += 1
            if log_changes:
                _actor_log(actor, f"Daily preparation: doomed {doomed} -> {next_val}.")

    drained = drained_value(actor)
    if drained > 0:
        recovery_bonus = 0
        for status in statuses:
            if _status_id(status) != "fast_recovery":
                continue
            data = getattr(status, "data", None) or {}
            try:
                recovery_bonus = max(recovery_bonus, int(data.get("drained_recovery_bonus", 0) or 0))
            except Exception:
                continue
        decrease = 1 + max(0, recovery_bonus)
        next_val = max(0, drained - decrease)
        strongest = _pick_strongest_status([s for s in statuses if _status_id(s) == "drained"], "drained_value", 1)
        if strongest is not None:
            filtered = [s for s in statuses if _status_id(s) != "drained"]
            if next_val > 0:
                data = dict(getattr(strongest, "data", None) or {})
                data["drained_value"] = next_val
                filtered.append(replace(strongest, label=f"Drained {next_val}", data=data))
            statuses = filtered
            changed += 1
            if log_changes:
                _actor_log(actor, f"Daily preparation: drained {drained} -> {next_val}.")

    filtered: list[Status] = []
    for status in statuses:
        data = getattr(status, "data", None) or {}
        expires_daily = bool(data.get("expires_on_daily_preparation", False))
        expires_phase = {str(x).strip().lower() for x in list(data.get("expires_on_phase", []) or [])}
        if expires_daily or "daily_preparation" in expires_phase:
            changed += 1
            if log_changes:
                label = str(getattr(status, "label", "") or getattr(status, "id", "status"))
                _actor_log(actor, f"Daily preparation: wygasa status {label}.")
            continue
        filtered.append(status)
    if changed > 0:
        try:
            actor.statuses = filtered
        except Exception:
            pass
    normalize_condition_stacks(actor, log_changes=log_changes)
    return int(changed)


# --- Value helpers ---

def frightened_value(actor: Any) -> int:
    return _best_value(actor, "frightened", "frightened_value", 1)


def sickened_value(actor: Any) -> int:
    return _best_value(actor, "sickened", "sickened_value", 1)


def slowed_value(actor: Any) -> int:
    return _best_value(actor, "slowed", "slowed_value", 1)


def quickened_value(actor: Any) -> int:
    return _best_value(actor, "quickened", "quickened_value", 1)


def stupefied_value(actor: Any) -> int:
    return _best_value(actor, "stupefied", "stupefied_value", 1)


def drained_value(actor: Any) -> int:
    return _best_value(actor, "drained", "drained_value", 1)


def doomed_value(actor: Any) -> int:
    return _best_value(actor, "doomed", "doomed_value", 1)


def fatigued_value(actor: Any) -> int:
    return 1 if any(_status_id(s) == "fatigued" for s in _iter_statuses(actor)) else 0


# --- Combat / action helpers ---

def attack_penalty_components(actor: Any, *, action_tag: str) -> list[tuple[str, int]]:
    components: list[tuple[str, int]] = []
    frightened = frightened_value(actor)
    if frightened > 0:
        components.append(("frightened", frightened))
    sickened = sickened_value(actor)
    if sickened > 0:
        components.append(("sickened", sickened))
    fatigued = fatigued_value(actor)
    if fatigued > 0:
        components.append(("fatigued", fatigued))
    if action_tag == "magic":
        stupefied = stupefied_value(actor)
        if stupefied > 0:
            components.append(("stupefied", stupefied))
    return components


def action_limit_modifier(actor: Any) -> int:
    return int(max(-3, min(2, quickened_value(actor) - slowed_value(actor))))


def attack_penalty_value(actor: Any, *, action_tag: str) -> int:
    penalty = sum(int(value) for _name, value in attack_penalty_components(actor, action_tag=action_tag))
    return int(max(0, penalty))


def ac_penalty_components(actor: Any) -> list[tuple[str, int]]:
    components: list[tuple[str, int]] = []
    frightened = frightened_value(actor)
    if frightened > 0:
        components.append(("frightened", frightened))
    sickened = sickened_value(actor)
    if sickened > 0:
        components.append(("sickened", sickened))
    fatigued = fatigued_value(actor)
    if fatigued > 0:
        components.append(("fatigued", fatigued))
    return components


def ac_penalty_value(actor: Any) -> int:
    return int(max(0, sum(int(value) for _name, value in ac_penalty_components(actor))))


def attack_penalty_effects(actor: Any, *, action_tag: str) -> list[BonusEffect]:
    penalty = attack_penalty_value(actor, action_tag=action_tag)
    if penalty <= 0:
        return []
    label = _condition_components_label(attack_penalty_components(actor, action_tag=action_tag))
    return [
        BonusEffect(
            type=BonusType.STATUS,
            value=penalty,
            tag=action_tag,
            source="status:pf2_condition_penalty",
            label=label,
            is_penalty=True,
        )
    ]


def ac_penalty_effect(actor: Any) -> BonusEffect | None:
    penalty = ac_penalty_value(actor)
    if penalty <= 0:
        return None
    return BonusEffect(
        type=BonusType.STATUS,
        value=penalty,
        tag="ac",
        source="status:pf2_condition_penalty",
        label=_condition_components_label(ac_penalty_components(actor)),
        is_penalty=True,
    )


def skill_penalty_components(actor: Any, *, skill_id: str, tags: Sequence[str]) -> list[tuple[str, int]]:
    _ = tags
    skill = str(skill_id or "").strip().lower()
    components: list[tuple[str, int]] = []

    frightened = frightened_value(actor)
    if frightened > 0:
        components.append(("frightened", frightened))
    sickened = sickened_value(actor)
    if sickened > 0:
        components.append(("sickened", sickened))
    fatigued = fatigued_value(actor)
    if fatigued > 0:
        components.append(("fatigued", fatigued))

    if skill in _MENTAL_SKILLS:
        stupefied = stupefied_value(actor)
        if stupefied > 0:
            components.append(("stupefied", stupefied))

    if skill == Skill.FORTITUDE.value:
        drained = drained_value(actor)
        if drained > 0:
            components.append(("drained", drained))

    if skill in (Skill.ATHLETICS.value,):
        try:
            from .enfeebled import enfeebled_value as _enf

            enfeebled = int(_enf(actor) or 0)
            if enfeebled > 0:
                components.append(("enfeebled", enfeebled))
        except Exception:
            pass

    if skill in (Skill.ACROBATICS.value, Skill.STEALTH.value, Skill.THIEVERY.value):
        try:
            from .clumsy import clumsy_stealth_penalty as _clumsy_stealth

            if skill == Skill.STEALTH.value:
                clumsy = int(_clumsy_stealth(actor) or 0)
                if clumsy > 0:
                    components.append(("clumsy", clumsy))
        except Exception:
            pass

    return components


def skill_penalty_value(actor: Any, *, skill_id: str, tags: Sequence[str]) -> int:
    penalty = sum(int(value) for _name, value in skill_penalty_components(actor, skill_id=skill_id, tags=tags))
    return int(max(0, penalty))


def skill_penalty_breakdown_label(actor: Any, *, skill_id: str, tags: Sequence[str]) -> str:
    return _condition_components_label(skill_penalty_components(actor, skill_id=skill_id, tags=tags))


def forced_skill_outcome(actor: Any, *, tags: Sequence[str]) -> tuple[str | None, str | None]:
    tags_set = {str(t).strip().lower() for t in tags}
    if "auditory" in tags_set and any(_status_id(s) == "deafened" for s in _iter_statuses(actor)):
        return "critical_failure", "Deafened: automatyczna porażka testu auditory."
    if "visual" in tags_set and any(_status_id(s) == "blinded" for s in _iter_statuses(actor)):
        return "critical_failure", "Blinded: automatyczna porażka testu visual."
    return None, None


def action_block_reason(actor: Any, *, action_tags: Sequence[str], action_name: str | None = None, target: Any | None = None) -> str | None:
    tags = {str(t).strip().lower() for t in action_tags}
    ids = {_status_id(s) for s in _iter_statuses(actor)}
    if "step" in tags or str(action_name or "").strip().lower() == "step":
        for status in _iter_statuses(actor):
            if _status_id(status) != "animal_companion_badger_step_locked":
                continue
            data = getattr(status, "data", None) or {}
            raw_pos = data.get("locked_position")
            locked_position = None
            if isinstance(raw_pos, (list, tuple)) and len(raw_pos) == 2:
                try:
                    locked_position = (int(raw_pos[0]), int(raw_pos[1]))
                except Exception:
                    locked_position = None
            if locked_position is None or getattr(actor, "position", None) == locked_position:
                return "Badger Support: nie możesz użyć Step, dopóki nie zmienisz pozycji."
    if "dead" in ids:
        return "Nie możesz działać będąc martwy."
    if "unconscious" in ids:
        return "Nie możesz działać będąc nieprzytomny."
    if "paralyzed" in ids:
        return "Nie możesz działać będąc sparaliżowany."
    if "petrified" in ids:
        return "Nie możesz działać będąc skamieniały."
    if "controlled" in ids:
        return "Jesteś controlled - nie możesz wybierać własnych akcji."
    if "confused" in ids:
        return "Jesteś confused - tracisz kontrolę nad akcjami."
    if "immobilized" in ids and "move" in tags:
        return "Immobilized: nie możesz wykonywać akcji ruchu."
    if "fleeing" in ids and "move" not in tags and str(action_name or "") not in {"end", "delay"}:
        return "Fleeing: możesz wykonywać tylko akcje ruchu oddalające od zagrożenia."
    if "fascinated" in ids and ("concentrate" in tags or "mental" in tags):
        target_id = getattr(target, "object_id", None) or getattr(target, "name", None)
        focus_id = None
        for status in _iter_statuses(actor):
            if _status_id(status) == "fascinated":
                focus_id = (getattr(status, "data", None) or {}).get("focus_target_id")
                break
        if focus_id and target_id and str(target_id) == str(focus_id):
            return None
        return "Fascinated: nie możesz wykonywać akcji wymagających koncentracji poza obiektem fascynacji."
    return None


def visibility_block_reason(attacker: Any, target: Any) -> str | None:
    target_ids = {_status_id(s) for s in _iter_statuses(target)}
    if "unnoticed" in target_ids:
        return "Cel jest unnoticed - nie możesz go namierzyć."
    return None


def visibility_flat_check_dc(attacker: Any, target: Any, *, ignore_target_concealed: bool = False) -> int:
    dc = 0
    attacker_ids = {_status_id(s) for s in _iter_statuses(attacker)}
    target_ids = {_status_id(s) for s in _iter_statuses(target)}

    if "blinded" in attacker_ids:
        dc = max(dc, 11)
    if "dazzled" in attacker_ids:
        dc = max(dc, 5)

    if not ignore_target_concealed and "concealed" in target_ids:
        dc = max(dc, 5)
    if "hidden" in target_ids:
        dc = max(dc, 11)
    if "undetected" in target_ids:
        dc = max(dc, 11)
    if "invisible" in target_ids:
        dc = max(dc, 11)

    return int(dc)


def decrement_end_of_turn_conditions(actor: Any) -> int:
    statuses = getattr(actor, "statuses", None)
    if not isinstance(statuses, list) or not statuses:
        return 0

    def _replace_scaled(status_id: str, key: str, label_prefix: str) -> int:
        current_statuses = list(getattr(actor, "statuses", []) or [])
        pool = [s for s in current_statuses if _status_id(s) == status_id]
        picked = _pick_strongest_status(pool, key, 1)
        if picked is None:
            return 0
        old_val = max(1, _status_int_value(picked, key, 1))
        new_val = max(0, old_val - 1)
        filtered = [s for s in current_statuses if _status_id(s) != status_id]
        if new_val > 0:
            data = dict(getattr(picked, "data", None) or {})
            data[key] = new_val
            filtered.append(replace(picked, label=f"{label_prefix} {new_val}", data=data))
        try:
            actor.statuses = filtered
        except Exception:
            return 0
        return 1

    changed = 0
    changed += _replace_scaled("frightened", "frightened_value", "Frightened")

    dynamic_rules: list[tuple[str, str, str]] = []
    for status in list(getattr(actor, "statuses", []) or []):
        data = getattr(status, "data", None) or {}
        if not bool(data.get("decrement_end_of_turn", False)):
            continue
        key = str(data.get("decrement_value_key", "") or "").strip()
        if not key:
            continue
        sid = _status_id(status)
        label_prefix = str(data.get("decrement_label_prefix", getattr(status, "label", sid) or sid)).split()[0]
        dynamic_rules.append((sid, key, label_prefix))
    for sid, key, label_prefix in dynamic_rules:
        changed += _replace_scaled(sid, key, label_prefix)

    changed += normalize_condition_stacks(actor, log_changes=False)
    return int(changed)


__all__ = [
    "OffGuardStatus",
    "DazzledStatus",
    "FrightenedStatus",
    "SickenedStatus",
    "SlowedStatus",
    "QuickenedStatus",
    "StupefiedStatus",
    "DrainedStatus",
    "DoomedStatus",
    "ConfusedStatus",
    "ControlledStatus",
    "FascinatedStatus",
    "FatiguedStatus",
    "FleeingStatus",
    "HiddenStatus",
    "UndetectedStatus",
    "UnnoticedStatus",
    "InvisibleStatus",
    "ParalyzedStatus",
    "PetrifiedStatus",
    "EncumberedStatus",
    "BrokenStatus",
    "frightened_value",
    "sickened_value",
    "slowed_value",
    "quickened_value",
    "stupefied_value",
    "drained_value",
    "doomed_value",
    "fatigued_value",
    "normalize_condition_stacks",
    "tick_condition_durations",
    "apply_daily_preparation_conditions",
    "action_limit_modifier",
    "attack_penalty_components",
    "attack_penalty_value",
    "ac_penalty_components",
    "ac_penalty_value",
    "attack_penalty_effects",
    "ac_penalty_effect",
    "skill_penalty_components",
    "skill_penalty_value",
    "skill_penalty_breakdown_label",
    "forced_skill_outcome",
    "action_block_reason",
    "visibility_block_reason",
    "visibility_flat_check_dc",
    "decrement_end_of_turn_conditions",
]

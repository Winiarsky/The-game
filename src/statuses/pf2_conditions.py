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

def action_limit_modifier(actor: Any) -> int:
    return int(max(-3, min(2, quickened_value(actor) - slowed_value(actor))))


def attack_penalty_value(actor: Any, *, action_tag: str) -> int:
    penalty = 0
    penalty += frightened_value(actor)
    penalty += sickened_value(actor)
    penalty += fatigued_value(actor)
    if action_tag == "magic":
        penalty += stupefied_value(actor)
    return int(max(0, penalty))


def ac_penalty_value(actor: Any) -> int:
    return int(max(0, frightened_value(actor) + sickened_value(actor) + fatigued_value(actor)))


def attack_penalty_effects(actor: Any, *, action_tag: str) -> list[BonusEffect]:
    penalty = attack_penalty_value(actor, action_tag=action_tag)
    if penalty <= 0:
        return []
    return [
        BonusEffect(
            type=BonusType.STATUS,
            value=penalty,
            tag=action_tag,
            source="status:pf2_condition_penalty",
            label="conditions",
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
        label="conditions",
        is_penalty=True,
    )


def skill_penalty_value(actor: Any, *, skill_id: str, tags: Sequence[str]) -> int:
    tags_set = {str(t).strip().lower() for t in tags}
    skill = str(skill_id or "").strip().lower()
    penalty = 0
    penalty += frightened_value(actor)
    penalty += sickened_value(actor)
    penalty += fatigued_value(actor)

    if skill in _MENTAL_SKILLS:
        penalty += stupefied_value(actor)

    if skill == Skill.FORTITUDE.value:
        penalty += drained_value(actor)

    if skill in (Skill.ATHLETICS.value,):
        try:
            from .enfeebled import enfeebled_value as _enf

            penalty += int(_enf(actor) or 0)
        except Exception:
            pass

    if skill in (Skill.ACROBATICS.value, Skill.STEALTH.value, Skill.THIEVERY.value):
        try:
            from .clumsy import clumsy_stealth_penalty as _clumsy_stealth

            if skill == Skill.STEALTH.value:
                penalty += int(_clumsy_stealth(actor) or 0)
        except Exception:
            pass

    return int(max(0, penalty))


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

    def _replace_scaled(status_id: str, key: str) -> int:
        picked = None
        for status in statuses:
            if _status_id(status) != status_id:
                continue
            val = _status_int_value(status, key, 1)
            if picked is None or val > _status_int_value(picked, key, 1):
                picked = status
        if picked is None:
            return 0
        new_val = max(0, _status_int_value(picked, key, 1) - 1)
        removed = 0
        kept: list[Status] = []
        for status in statuses:
            if _status_id(status) == status_id:
                removed += 1
                continue
            kept.append(status)
        if new_val > 0:
            data = dict(getattr(picked, "data", None) or {})
            data[key] = new_val
            base_label = str(getattr(picked, "label", "") or status_id).split()[0]
            kept.append(replace(picked, label=f"{base_label} {new_val}", data=data))
        actor.statuses = kept
        return removed

    changed = 0
    changed += _replace_scaled("frightened", "frightened_value")
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
    "action_limit_modifier",
    "attack_penalty_value",
    "ac_penalty_value",
    "attack_penalty_effects",
    "ac_penalty_effect",
    "skill_penalty_value",
    "forced_skill_outcome",
    "action_block_reason",
    "visibility_block_reason",
    "visibility_flat_check_dc",
    "decrement_end_of_turn_conditions",
]

from __future__ import annotations

from bonuses import BonusEffect, BonusType
from skills import Skill
from statuses.base import Status
from statuses.check_effects import CheckEffect


def ClumsyStatus(
    *,
    ac_penalty: int = 0,
    reflex_penalty: int = 0,
    ranged_penalty: int = 0,
    finesse_penalty: int = 0,
    stealth_penalty: int = 0,
    duration: int | None = None,
    source: str | None = None,
    label: str | None = None,
) -> Status:
    """Status clumsy: kary do AC/Reflex/ataków dystansowych/finesse/Stealth."""
    data = {
        "clumsy_ac_penalty": int(ac_penalty),
        "clumsy_reflex_penalty": int(reflex_penalty),
        "clumsy_ranged_penalty": int(ranged_penalty),
        "clumsy_finesse_penalty": int(finesse_penalty),
        "clumsy_stealth_penalty": int(stealth_penalty),
        "effect_tags": ["clumsy"],
    }
    effects = []
    if stealth_penalty:
        effects.append(
            CheckEffect(
                applies_to="source",
                skills=[Skill.STEALTH.value],
                tags_required=[Skill.STEALTH.value],
                bonus_effects=[
                    BonusEffect(
                        type=BonusType.STATUS,
                        value=int(stealth_penalty),
                        tag=Skill.STEALTH.value,
                        source="status:clumsy",
                        label="clumsy",
                        is_penalty=True,
                    )
                ],
            )
        )
    return Status(
        id="clumsy",
        label=label or "Clumsy",
        duration=duration,
        source=source,
        data=data,
        check_effects=effects or None,
        stacks=True,
    )


def _is_hero(obj) -> bool:
    try:
        from hero import Hero

        return isinstance(obj, Hero)
    except Exception:
        return False


def _best_clumsy_value(target, key: str) -> int:
    statuses = getattr(target, "statuses", None)
    if not isinstance(statuses, list):
        return 0
    best = 0
    for status in statuses:
        if getattr(status, "id", None) != "clumsy":
            continue
        data = getattr(status, "data", None) or {}
        val = data.get(key)
        try:
            val = int(val)
        except Exception:
            val = 0
        if val > best:
            best = val
    return int(best)


def clumsy_ac_penalty(target) -> int:
    return _best_clumsy_value(target, "clumsy_ac_penalty")


def clumsy_reflex_penalty(target) -> int:
    return _best_clumsy_value(target, "clumsy_reflex_penalty")


def clumsy_ranged_penalty(target) -> int:
    return _best_clumsy_value(target, "clumsy_ranged_penalty")


def clumsy_finesse_penalty(target) -> int:
    return _best_clumsy_value(target, "clumsy_finesse_penalty")


def clumsy_stealth_penalty(target) -> int:
    return _best_clumsy_value(target, "clumsy_stealth_penalty")


def clumsy_ac_penalty_effect(target) -> BonusEffect | None:
    penalty = clumsy_ac_penalty(target)
    if penalty <= 0:
        return None
    if _is_hero(target):
        return None
    return BonusEffect(
        type=BonusType.STATUS,
        value=int(penalty),
        tag="ac",
        source="status:clumsy",
        label="clumsy",
        is_penalty=True,
    )


def clumsy_ac_prompt_note(target) -> str | None:
    penalty = clumsy_ac_penalty(target)
    if penalty <= 0 or not _is_hero(target):
        return None
    return f"Clumsy: -{int(penalty)} status do AC (uwzględnij ręcznie)."


def clumsy_attack_penalty_effects(
    attacker,
    *,
    action_tag: str,
    is_ranged: bool,
    is_finesse: bool,
) -> list[BonusEffect]:
    effects: list[BonusEffect] = []
    ranged_pen = clumsy_ranged_penalty(attacker) if is_ranged else 0
    finesse_pen = clumsy_finesse_penalty(attacker) if is_finesse else 0
    for value, label in ((ranged_pen, "clumsy:ranged"), (finesse_pen, "clumsy:finesse")):
        if value > 0:
            effects.append(
                BonusEffect(
                    type=BonusType.STATUS,
                    value=int(value),
                    tag=action_tag,
                    source="status:clumsy",
                    label=label,
                    is_penalty=True,
                )
            )
    return effects


__all__ = [
    "ClumsyStatus",
    "clumsy_ac_penalty",
    "clumsy_reflex_penalty",
    "clumsy_ranged_penalty",
    "clumsy_finesse_penalty",
    "clumsy_stealth_penalty",
    "clumsy_ac_penalty_effect",
    "clumsy_ac_prompt_note",
    "clumsy_attack_penalty_effects",
]

from __future__ import annotations

from bonuses import BonusEffect, BonusType
from .base import Status


def EnfeebledStatus(
    *,
    value: int,
    duration: int | None = None,
    source: str | None = None,
    source_id: str | None = None,
    source_turns_left: int | None = None,
) -> Status:
    penalty = max(1, int(value))
    data = {
        "enfeebled_value": penalty,
        "source_id": source_id,
        "source_turns_left": source_turns_left,
        "effect_tags": ["enfeebled"],
    }
    return Status(
        id="enfeebled",
        label=f"Enfeebled {penalty}",
        duration=duration,
        source=source,
        data=data,
        stacks=True,
    )


def enfeebled_value(actor) -> int:
    statuses = getattr(actor, "statuses", None)
    if not isinstance(statuses, list):
        return 0
    best = 0
    for status in statuses:
        if getattr(status, "id", None) != "enfeebled":
            continue
        data = getattr(status, "data", None) or {}
        try:
            val = int(data.get("enfeebled_value", 0))
        except Exception:
            val = 0
        if val > best:
            best = val
    return int(best)


def enfeebled_attack_penalty_effects(actor, action_tag: str) -> list[BonusEffect]:
    penalty = enfeebled_value(actor)
    if penalty <= 0:
        return []
    return [
        BonusEffect(
            type=BonusType.STATUS,
            value=penalty,
            tag=action_tag,
            source="status:enfeebled",
            label="enfeebled",
            is_penalty=True,
        )
    ]


def enfeebled_damage_penalty(actor) -> int:
    return max(0, int(enfeebled_value(actor) or 0))


__all__ = [
    "EnfeebledStatus",
    "enfeebled_value",
    "enfeebled_attack_penalty_effects",
    "enfeebled_damage_penalty",
]


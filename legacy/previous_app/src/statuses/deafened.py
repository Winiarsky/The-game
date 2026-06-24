from __future__ import annotations

from bonuses import BonusEffect, BonusType
from .base import Status
from .check_effects import CheckEffect


def DeafenedStatus(*, duration: int | None = None, source: str | None = None, source_id: str | None = None, source_turns_left: int | None = None) -> Status:
    """Status deafened: -2 do Perception (w tym inicjatywa)."""
    data = {
        "initiative_penalty": 2,
        "initiative_penalty_applied": False,
        "source_id": source_id,
        "source_turns_left": source_turns_left,
        "effect_tags": ["deafened"],
    }
    return Status(
        id="deafened",
        label="deafened",
        duration=duration,
        source=source,
        data=data,
        check_effects=[
            CheckEffect(
                applies_to="source",
                skills=["perception"],
                bonus_effects=[
                    BonusEffect(
                        type=BonusType.STATUS,
                        value=2,
                        tag="perception",
                        source="deafened",
                        is_penalty=True,
                    )
                ],
            )
        ],
    )


DEAFENED_STATUS = DeafenedStatus()


def deafened_initiative_penalty(actor, *, only_unapplied: bool = False) -> int:
    statuses = getattr(actor, "statuses", None)
    if not isinstance(statuses, list):
        return 0
    best = 0
    for status in statuses:
        if getattr(status, "id", None) != "deafened":
            continue
        data = getattr(status, "data", None) or {}
        if only_unapplied and data.get("initiative_penalty_applied"):
            continue
        val = data.get("initiative_penalty", 2)
        try:
            val = int(val)
        except Exception:
            val = 0
        if val > best:
            best = val
    return int(best)


def mark_deafened_initiative_applied(actor) -> None:
    statuses = getattr(actor, "statuses", None)
    if not isinstance(statuses, list):
        return
    for status in statuses:
        if getattr(status, "id", None) != "deafened":
            continue
        data = getattr(status, "data", None)
        if isinstance(data, dict):
            data["initiative_penalty_applied"] = True

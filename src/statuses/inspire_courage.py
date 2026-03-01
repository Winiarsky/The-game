from __future__ import annotations

from .base import Status


def InspireCourageStatus(
    *,
    source_id: str | None,
    source_turns_left: int | None = 1,
    source: str | None = None,
) -> Status:
    return Status(
        id="inspire_courage",
        label="Inspire Courage",
        source=source,
        stacks=True,
        data={
            "source_id": source_id,
            "source_turns_left": source_turns_left,
            "effect_tags": ["focus", "cantrip", "inspire", "courage"],
        },
    )


def inspire_courage_damage_bonus(actor) -> int:
    if actor is None:
        return 0
    has_status = getattr(actor, "has_status", None)
    if callable(has_status):
        try:
            return 1 if has_status("inspire_courage") else 0
        except Exception:
            return 0
    statuses = getattr(actor, "statuses", None)
    if not isinstance(statuses, list):
        return 0
    for status in statuses:
        if getattr(status, "id", None) == "inspire_courage":
            return 1
    return 0


__all__ = ["InspireCourageStatus", "inspire_courage_damage_bonus"]


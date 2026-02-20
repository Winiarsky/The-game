from __future__ import annotations

from .base import Status


def SpeedBonusStatus(
    *,
    bonus_feet: int,
    duration: int | None = None,
    source: str | None = None,
    label: str | None = None,
) -> Status:
    """Status zwiekszajacy predkosc (dla wrogow i info dla bohaterow)."""
    data = {
        "speed_bonus_feet": int(bonus_feet),
        "effect_tags": ["speed_bonus"],
    }
    return Status(
        id="speed_bonus",
        label=label or f"speed +{int(bonus_feet)}ft",
        duration=duration,
        source=source,
        data=data,
        stacks=True,
    )


def speed_bonus_value(target) -> int:
    """Zwróć najwyższy bonus do speed w stopach."""
    statuses = getattr(target, "statuses", None)
    if not isinstance(statuses, list):
        return 0
    best = 0
    for status in statuses:
        if getattr(status, "id", None) != "speed_bonus":
            continue
        data = getattr(status, "data", None) or {}
        val = data.get("speed_bonus_feet")
        try:
            val = int(val)
        except Exception:
            val = 0
        if val > best:
            best = val
    return int(best)


__all__ = ["SpeedBonusStatus", "speed_bonus_value"]

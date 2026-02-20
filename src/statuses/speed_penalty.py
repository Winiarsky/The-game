from __future__ import annotations

from .base import Status


def SpeedPenaltyStatus(
    *,
    penalty_feet: int,
    duration: int | None = None,
    source: str | None = None,
    source_id: str | None = None,
    source_turns_left: int | None = None,
    label: str | None = None,
    escape_dc: int | None = None,
) -> Status:
    """Status redukujący prędkość (dla wrogów)."""
    data = {
        "speed_penalty_feet": int(penalty_feet),
        "source_id": source_id,
        "source_turns_left": source_turns_left,
        "escape_dc": escape_dc,
        "effect_tags": ["speed_penalty"],
    }
    return Status(
        id="speed_penalty",
        label=label or f"speed -{int(penalty_feet)}ft",
        duration=duration,
        source=source,
        data=data,
        stacks=True,
    )


def speed_penalty_value(target) -> int:
    """Zwróć najwyższą karę do speed w stopach."""
    statuses = getattr(target, "statuses", None)
    if not isinstance(statuses, list):
        return 0
    best = 0
    for status in statuses:
        if getattr(status, "id", None) != "speed_penalty":
            continue
        data = getattr(status, "data", None) or {}
        val = data.get("speed_penalty_feet")
        try:
            val = int(val)
        except Exception:
            val = 0
        if val > best:
            best = val
    return int(best)

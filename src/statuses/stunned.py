from __future__ import annotations

from .base import Status


def StunnedStatus(
    *,
    value: int,
    duration: int | None = None,
    source: str | None = None,
    source_id: str | None = None,
    source_turns_left: int | None = None,
) -> Status:
    amount = max(1, int(value))
    data = {
        "stunned_value": amount,
        "source_id": source_id,
        "source_turns_left": source_turns_left,
        "effect_tags": ["stunned"],
    }
    return Status(
        id="stunned",
        label=f"Stunned {amount}",
        duration=duration,
        source=source,
        data=data,
        stacks=True,
    )


def consume_stunned_actions(actor) -> int:
    statuses = getattr(actor, "statuses", None)
    if not isinstance(statuses, list) or not statuses:
        return 0
    remaining = []
    consumed = 0
    for status in statuses:
        if getattr(status, "id", None) != "stunned":
            remaining.append(status)
            continue
        data = getattr(status, "data", None) or {}
        try:
            consumed += max(0, int(data.get("stunned_value", 0)))
        except Exception:
            pass
    try:
        actor.statuses = remaining
    except Exception:
        pass
    return int(consumed)


__all__ = ["StunnedStatus", "consume_stunned_actions"]


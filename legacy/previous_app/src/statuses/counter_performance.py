from __future__ import annotations

from .base import Status


def CounterPerformanceStatus(
    *,
    performance_total: int,
    source_id: str | None,
    source_turns_left: int | None = 1,
    source: str | None = None,
) -> Status:
    total = max(0, int(performance_total))
    return Status(
        id="counter_performance",
        label=f"Counter Performance ({total})",
        source=source,
        stacks=True,
        data={
            "performance_total": total,
            "source_id": source_id,
            "source_turns_left": source_turns_left,
            "effect_tags": ["focus", "performance", "save"],
        },
    )


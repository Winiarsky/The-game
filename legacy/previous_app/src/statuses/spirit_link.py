from __future__ import annotations

from .base import Status


def SpiritLinkCasterStatus(
    *,
    target_id: str | None,
    duration: int | None = 1,
    source: str | None = None,
) -> Status:
    return Status(
        id="spirit_link_caster",
        label="Spirit Link (caster)",
        duration=duration,
        source=source,
        data={"target_id": target_id, "effect_tags": ["spirit_link"]},
    )


def SpiritLinkTargetStatus(
    *,
    source_id: str | None,
    duration: int | None = 1,
    source: str | None = None,
) -> Status:
    return Status(
        id="spirit_link_target",
        label="Spirit Link",
        duration=duration,
        source=source,
        data={"source_id": source_id, "effect_tags": ["spirit_link"]},
    )


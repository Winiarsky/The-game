from __future__ import annotations

from .base import Status


def IllusoryDisguiseStatus(
    *,
    persona: str = "masked",
    duration: int | None = 10,
    source: str | None = None,
) -> Status:
    style = str(persona or "masked")
    return Status(
        id="illusory_disguise",
        label=f"Illusory Disguise ({style})",
        duration=duration,
        source=source,
        data={"persona": style, "effect_tags": ["illusion"]},
    )


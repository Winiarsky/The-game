from __future__ import annotations

from statuses.base import Status

CUTE_VISION_PROMPT = "Cute Vision: podczas Rage zyskujesz darkvision."


def CuteVisionStatus() -> Status:
    """Feat: Cute Vision."""
    return Status(
        id="cute_vision",
        label="Cute Vision",
        data={"ui_prompt": CUTE_VISION_PROMPT},
    )


CUTE_VISION_STATUS = CuteVisionStatus()

__all__ = ["CuteVisionStatus", "CUTE_VISION_STATUS", "CUTE_VISION_PROMPT"]

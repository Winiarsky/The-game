from __future__ import annotations

from statuses.base import Status
from statuses.check_effects import CheckEffect
from skills import Skill


def LowLightVisionStatus() -> Status:
    """Status: widzenie w polmroku."""
    return Status(
        id="low_light_vision",
        label="Widzenie w slabym swietle",
        check_effects=[
            CheckEffect(
                applies_to="source",
                skills=[Skill.PERCEPTION.value],
                prompt_notes=["Ignorujesz efekty polmroku."],
            )
        ],
    )


LOW_LIGHT_VISION_STATUS = LowLightVisionStatus()

__all__ = ["LowLightVisionStatus", "LOW_LIGHT_VISION_STATUS"]

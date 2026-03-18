from __future__ import annotations

from statuses.base import Status
from statuses.check_effects import CheckEffect
from skills import Skill


def DimLightVisionStatus() -> Status:
    """Status: widzenie w polmroku."""
    return Status(
        id="dim_light_vision",
        label="Widzenie w polmroku",
        check_effects=[
            CheckEffect(
                applies_to="source",
                skills=[Skill.PERCEPTION.value],
                prompt_notes=["Ignorujesz efekty polmroku."],
            )
        ],
    )


DIM_LIGHT_VISION_STATUS = DimLightVisionStatus()

__all__ = ["DimLightVisionStatus", "DIM_LIGHT_VISION_STATUS"]

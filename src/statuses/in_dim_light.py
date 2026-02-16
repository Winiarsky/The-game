from __future__ import annotations

from skills import Skill
from statuses.base import Status
from statuses.check_effects import CheckEffect


def InDimLightStatus() -> Status:
    """Status półmroku – informacja o +2 circumstance do Stealth (manualnie)."""
    return Status(
        id="in_dim_light",
        label="In Dim Light",
        check_effects=[
            CheckEffect(
                applies_to="source",
                skills=[Skill.STEALTH.value],
                tags_required=["try_stealth"],
                prompt_notes=["Półmrok: +2 circumstance do Stealth (dolicz ręcznie)."],
            )
        ],
    )


IN_DIM_LIGHT_STATUS = InDimLightStatus()

__all__ = ["InDimLightStatus", "IN_DIM_LIGHT_STATUS"]

from __future__ import annotations

from bonuses import BonusEffect, BonusType
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
                bonus_effects=[
                    BonusEffect(
                        type=BonusType.CIRCUMSTANCE,
                        value=2,
                        tag=Skill.STEALTH.value,
                        source="status:in_dim_light",
                        label="półmrok +2",
                    )
                ],
                prompt_notes=["Półmrok: +2 circumstance do Stealth."],
            )
        ],
    )


IN_DIM_LIGHT_STATUS = InDimLightStatus()

__all__ = ["InDimLightStatus", "IN_DIM_LIGHT_STATUS"]

from __future__ import annotations

from skills import Skill
from statuses.base import Status
from statuses.check_effects import CheckEffect

ALCHEMICAL_SAVANT_DESCRIPTION = (
    "Crafting z tagiem alchemic: wynik podniesiony o 1 stopien."
)


def AlchemicalSavantStatus() -> Status:
    """Feat: Alchemical Savant."""
    return Status(
        id="alchemical_savant",
        label="Alchemical Savant",
        data={"ui_description": ALCHEMICAL_SAVANT_DESCRIPTION},
        check_effects=[
            CheckEffect(
                applies_to="source",
                skills=[Skill.CRAFTING.value],
                tags_required=["alchemic"],
                promote=1,
                prompt_notes=["Alchemical Savant: Crafting (alchemic) +1 stopien sukcesu."],
            )
        ],
    )


ALCHEMICAL_SAVANT_STATUS = AlchemicalSavantStatus()

__all__ = [
    "ALCHEMICAL_SAVANT_DESCRIPTION",
    "AlchemicalSavantStatus",
    "ALCHEMICAL_SAVANT_STATUS",
]

from __future__ import annotations

from bonuses import BonusEffect, BonusType
from skills import Skill
from statuses.base import Status
from statuses.check_effects import CheckEffect

INCREDIBLE_INITIATIVE_DESCRIPTION = "+2 circumstance do rzutow inicjatywy."


def IncredibleInitiativeStatus() -> Status:
    """Feat: Incredible Initiative."""
    return Status(
        id="incredible_initiative",
        label="Incredible Initiative",
        data={"ui_description": INCREDIBLE_INITIATIVE_DESCRIPTION},
        check_effects=[
            CheckEffect(
                applies_to="source",
                skills=[Skill.PERCEPTION.value],
                tags_required=["initiative"],
                bonus_effects=[
                    BonusEffect(
                        type=BonusType.CIRCUMSTANCE,
                        value=2,
                        tag=Skill.PERCEPTION.value,
                        source="status:incredible_initiative",
                        label="incredible init +2",
                    )
                ],
                prompt_notes=["Incredible Initiative: +2 do inicjatywy."],
            )
        ],
    )


INCREDIBLE_INITIATIVE_STATUS = IncredibleInitiativeStatus()

__all__ = [
    "IncredibleInitiativeStatus",
    "INCREDIBLE_INITIATIVE_STATUS",
    "INCREDIBLE_INITIATIVE_DESCRIPTION",
]

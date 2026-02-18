from __future__ import annotations

from bonuses import BonusEffect, BonusType
from skills import Skill
from statuses.base import Status
from statuses.check_effects import CheckEffect

IRONGUT_GOBLIN_DESCRIPTION = (
    "+2 circumstance do Fortitude przeciwko ingested; "
    "sukces staje się krytycznym sukcesem (tylko dla tagu ingested)."
)


def IrongutGoblinStatus() -> Status:
    """Heritage: Irongut Goblin."""
    return Status(
        id="irongut_goblin",
        label="Irongut Goblin",
        data={
            "ui_description": IRONGUT_GOBLIN_DESCRIPTION,
        },
        check_effects=[
            CheckEffect(
                applies_to="source",
                skills=[Skill.FORTITUDE.value],
                tags_required=["ingested"],
                bonus_effects=[
                    BonusEffect(
                        type=BonusType.CIRCUMSTANCE,
                        value=2,
                        tag=Skill.FORTITUDE.value,
                        source="status:irongut_goblin",
                        label="irongut",
                    )
                ],
                promote=1,
                promote_on=["success"],
                prompt_notes=["Irongut Goblin"],
            )
        ],
    )


IRONGUT_GOBLIN_STATUS = IrongutGoblinStatus()

__all__ = [
    "IrongutGoblinStatus",
    "IRONGUT_GOBLIN_STATUS",
    "IRONGUT_GOBLIN_DESCRIPTION",
]

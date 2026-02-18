from __future__ import annotations

from bonuses import BonusEffect, BonusType
from skills import Skill
from statuses.base import Status
from statuses.check_effects import CheckEffect

GUTSY_HALFLING_DESCRIPTION = (
    "Na sukces w rzucie obronnym przeciwko efektom emocji otrzymujesz krytyczny sukces."
)


def GutsyHalflingStatus() -> Status:
    """Heritage: Gutsy Halfling."""
    return Status(
        id="gutsy_halfling",
        label="Gutsy Halfling",
        data={"ui_description": GUTSY_HALFLING_DESCRIPTION},
        check_effects=[
            CheckEffect(
                applies_to="source",
                skills=[Skill.FORTITUDE.value, Skill.REFLEX.value, Skill.WILL.value],
                tags_required=["emotion"],
                promote=1,
                promote_on=["success"],
                prompt_notes=["Gutsy Halfling: sukces vs emotion -> krytyczny sukces."],
            )
        ],
    )


GUTSY_HALFLING_STATUS = GutsyHalflingStatus()

__all__ = ["GutsyHalflingStatus", "GUTSY_HALFLING_STATUS", "GUTSY_HALFLING_DESCRIPTION"]

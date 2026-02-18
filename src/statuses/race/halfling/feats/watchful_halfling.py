from __future__ import annotations

from bonuses import BonusEffect, BonusType
from skills import Skill
from statuses.base import Status
from statuses.check_effects import CheckEffect

WATCHFUL_HALFLING_DESCRIPTION = (
    "+2 circumstance do Perception podczas Sense Motive (tag sense_motive)."
)


def WatchfulHalflingStatus() -> Status:
    """Feat: Watchful Halfling."""
    return Status(
        id="watchful_halfling",
        label="Watchful Halfling",
        data={"ui_description": WATCHFUL_HALFLING_DESCRIPTION},
        check_effects=[
            CheckEffect(
                applies_to="source",
                skills=[Skill.PERCEPTION.value],
                tags_required=["sense_motive"],
                bonus_effects=[
                    BonusEffect(
                        type=BonusType.CIRCUMSTANCE,
                        value=2,
                        tag=Skill.PERCEPTION.value,
                        source="status:watchful_halfling",
                        label="watchful +2",
                    )
                ],
                prompt_notes=["Watchful Halfling: +2 do Sense Motive."],
            )
        ],
    )


WATCHFUL_HALFLING_STATUS = WatchfulHalflingStatus()

__all__ = ["WatchfulHalflingStatus", "WATCHFUL_HALFLING_STATUS", "WATCHFUL_HALFLING_DESCRIPTION"]

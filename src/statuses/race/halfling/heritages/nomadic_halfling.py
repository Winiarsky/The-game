from __future__ import annotations

from bonuses import BonusEffect, BonusType
from skills import Skill
from statuses.base import Status
from statuses.check_effects import CheckEffect

NOMADIC_HALFLING_DESCRIPTION = "+2 circumstance do testów Diplomacy."


def NomadicHalflingStatus() -> Status:
    """Heritage: Nomadic Halfling."""
    return Status(
        id="nomadic_halfling",
        label="Nomadic Halfling",
        data={"ui_description": NOMADIC_HALFLING_DESCRIPTION},
        check_effects=[
            CheckEffect(
                applies_to="source",
                skills=[Skill.DIPLOMACY.value],
                bonus_effects=[
                    BonusEffect(
                        type=BonusType.CIRCUMSTANCE,
                        value=2,
                        tag=Skill.DIPLOMACY.value,
                        source="status:nomadic_halfling",
                        label="nomadic +2",
                    )
                ],
                prompt_notes=["Nomadic Halfling: +2 circumstance do Diplomacy."],
            )
        ],
    )


NOMADIC_HALFLING_STATUS = NomadicHalflingStatus()

__all__ = ["NomadicHalflingStatus", "NOMADIC_HALFLING_STATUS", "NOMADIC_HALFLING_DESCRIPTION"]

from __future__ import annotations

from bonuses import BonusEffect, BonusType
from skills import Skill
from statuses.base import Status
from statuses.check_effects import CheckEffect

WATCHFUL_HALFLING_DESCRIPTION = (
    "Masz +2 circumstance do Perception checks podczas Sense Motive, by zauważyć "
    "enchantment/possession.\n"
    "Jeśli nie używasz aktywnie Sense Motive, GM może wykonać secret check z karą -2.\n"
    "Możesz też użyć Aid, by pomóc sojusznikowi przeciw enchantment/possession."
)


def WatchfulHalflingStatus() -> Status:
    """Feat: Watchful Halfling."""
    return Status(
        id="watchful_halfling",
        label="Watchful Halfling",
        data={
            "ui_description": WATCHFUL_HALFLING_DESCRIPTION,
            "watchful_halfling_passive_secret_check_penalty": -2,
            "watchful_halfling_aid_vs_enchantment_or_possession": True,
        },
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

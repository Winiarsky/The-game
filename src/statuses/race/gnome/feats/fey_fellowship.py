from __future__ import annotations

from bonuses import BonusEffect, BonusType
from skills import Skill
from statuses.base import Status
from statuses.check_effects import CheckEffect

FEY_FELLOWSHIP_DESCRIPTION = (
    "Masz +2 circumstance do Perception checks i saving throws przeciw fey.\n"
    "W social encounter z fey możesz natychmiast wykonać Make an Impression "
    "(zwykle z karą -5), zamiast wymaganej 1 minuty rozmowy.\n"
    "Jeśli posiadasz Glad-Hand, kara nie obowiązuje."
)


def FeyFellowshipStatus() -> Status:
    """Feat: Fey Fellowship."""
    bonus_effects = [
        BonusEffect(
            type=BonusType.CIRCUMSTANCE,
            value=2,
            tag=Skill.PERCEPTION.value,
            source="status:fey_fellowship",
            label="fey fellowship +2",
        ),
        BonusEffect(
            type=BonusType.CIRCUMSTANCE,
            value=2,
            tag=Skill.WILL.value,
            source="status:fey_fellowship",
            label="fey fellowship +2",
        ),
        BonusEffect(
            type=BonusType.CIRCUMSTANCE,
            value=2,
            tag=Skill.FORTITUDE.value,
            source="status:fey_fellowship",
            label="fey fellowship +2",
        ),
        BonusEffect(
            type=BonusType.CIRCUMSTANCE,
            value=2,
            tag=Skill.REFLEX.value,
            source="status:fey_fellowship",
            label="fey fellowship +2",
        ),
    ]
    return Status(
        id="fey_fellowship",
        label="Fey Fellowship",
        data={
            "ui_description": FEY_FELLOWSHIP_DESCRIPTION,
            "fey_fellowship_quick_impression_penalty": -5,
            "fey_fellowship_ignore_penalty_with_glad_hand": True,
        },
        check_effects=[
            CheckEffect(
                applies_to="source",
                skills=[
                    Skill.PERCEPTION.value,
                    Skill.WILL.value,
                    Skill.FORTITUDE.value,
                    Skill.REFLEX.value,
                ],
                tags_required=["fey"],
                bonus_effects=bonus_effects,
                prompt_notes=["Fey Fellowship: +2 do Perception/save vs fey."],
            )
        ],
    )


FEY_FELLOWSHIP_STATUS = FeyFellowshipStatus()

__all__ = ["FeyFellowshipStatus", "FEY_FELLOWSHIP_STATUS", "FEY_FELLOWSHIP_DESCRIPTION"]

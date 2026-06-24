from __future__ import annotations

from bonuses import BonusEffect, BonusType
from skills import Skill
from statuses.base import Status
from statuses.check_effects import CheckEffect

STONECUNNING_DESCRIPTION = (
    "+2 circumstance do Perception przy wykrywaniu kamieniarki/trapów w kamieniu.\n"
    "Przykład: Seek z tagiem stone dostaje +2."
)


def StonecunningStatus() -> Status:
    """Feat: Stonecunning."""
    return Status(
        id="stonecunning",
        label="Stonecunning",
        data={"ui_description": STONECUNNING_DESCRIPTION},
        check_effects=[
            CheckEffect(
                applies_to="source",
                skills=[Skill.PERCEPTION.value],
                tags_required=["stone"],
                bonus_effects=[
                    BonusEffect(
                        type=BonusType.CIRCUMSTANCE,
                        value=2,
                        tag=Skill.PERCEPTION.value,
                        source="status:stonecunning",
                        label="stonecunning",
                    )
                ],
                prompt_notes=["Stonecunning"],
            )
        ],
    )


STONECUNNING_STATUS = StonecunningStatus()

__all__ = ["StonecunningStatus", "STONECUNNING_STATUS", "STONECUNNING_DESCRIPTION"]

from __future__ import annotations

from bonuses import BonusEffect, BonusType
from skills import Skill
from statuses.base import Status
from statuses.check_effects import CheckEffect

ILLUSION_SENSE_DESCRIPTION = (
    "Masz +1 circumstance do Perception checks i Will saves przeciw iluzjom.\n"
    "Dodatkowo gdy wejdziesz w 10 stóp od iluzji, która może być disbelief, "
    "GM wykonuje secret check na disbelief nawet bez akcji Interact.\n"
    "W tym silniku automatyczny secret disbelief jest oznaczony danymi statusu."
)


def IllusionSenseStatus() -> Status:
    """Feat: Illusion Sense (opis do UI)."""
    return Status(
        id="illusion_sense",
        label="Illusion Sense",
        data={
            "ui_description": ILLUSION_SENSE_DESCRIPTION,
            "illusion_sense_auto_disbelieve_within_feet": 10,
        },
        check_effects=[
            CheckEffect(
                applies_to="source",
                skills=[Skill.WILL.value, Skill.PERCEPTION.value],
                tags_required=["illusion"],
                bonus_effects=[
                    BonusEffect(
                        type=BonusType.CIRCUMSTANCE,
                        value=1,
                        tag=Skill.WILL.value,
                        source="status:illusion_sense",
                        label="illusion sense +1",
                    ),
                    BonusEffect(
                        type=BonusType.CIRCUMSTANCE,
                        value=1,
                        tag=Skill.PERCEPTION.value,
                        source="status:illusion_sense",
                        label="illusion sense +1",
                    ),
                ],
                prompt_notes=[
                    "Illusion Sense: +1 circumstance do Will/Perception vs iluzje.",
                ],
            )
        ],
    )


ILLUSION_SENSE_STATUS = IllusionSenseStatus()

__all__ = [
    "IllusionSenseStatus",
    "ILLUSION_SENSE_STATUS",
    "ILLUSION_SENSE_DESCRIPTION",
]

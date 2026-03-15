from __future__ import annotations

from bonuses import BonusEffect, BonusType
from skills import Skill
from statuses.base import Status
from statuses.check_effects import CheckEffect

ILLUSION_SENSE_DESCRIPTION = (
    "Twoje zmysly sa wyczulone na zaburzenia rzeczywistosci wywolane iluzja.\n"
    "Kiedy: wykonujesz Will save lub Perception check przeciw efektowi z tagiem illusion.\n"
    "Efekt: +1 circumstance bonus do tych testow; dodatkowo przy wejsciu w zasieg "
    "10 stop od iluzji do disbelief mozliwy jest automatyczny secret disbelief "
    "(w silniku sygnalizowane przez illusion_sense_auto_disbelieve_within_feet)."
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

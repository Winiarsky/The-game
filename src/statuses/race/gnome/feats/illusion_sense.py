from __future__ import annotations

from bonuses import BonusEffect, BonusType
from skills import Skill
from statuses.base import Status
from statuses.check_effects import CheckEffect

ILLUSION_SENSE_DESCRIPTION = (
    "otrzymujesz premie +1 circumstance do rzutu obronnego na will lub perception na "
    "efekty iluzji, ponadto efekt jest zwiekszany o jeden stopien"
)


def IllusionSenseStatus() -> Status:
    """Feat: Illusion Sense (opis do UI)."""
    return Status(
        id="illusion_sense",
        label="Illusion Sense",
        data={"ui_description": ILLUSION_SENSE_DESCRIPTION},
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
                promote=1,
                prompt_notes=[
                    "Illusion Sense: +1 circumstance do Will/Perception vs iluzje.",
                    "Illusion Sense: wynik testu podbity o 1 stopien.",
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

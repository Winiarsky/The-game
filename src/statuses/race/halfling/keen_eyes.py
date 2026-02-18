from __future__ import annotations

from bonuses import BonusEffect, BonusType
from skills import Skill
from statuses.base import Status
from statuses.check_effects import CheckEffect

KEEN_EYES_DESCRIPTION = (
    "+2 circumstance do Perception podczas akcji Seek. "
    "Dodatkowo obniża DC flat check przy ataku w concealed (5 -> 3)."
)


def KeenEyesStatus() -> Status:
    """Cecha: Keen Eyes."""
    return Status(
        id="keen_eyes",
        label="Keen Eyes",
        data={"ui_description": KEEN_EYES_DESCRIPTION},
        check_effects=[
            CheckEffect(
                applies_to="source",
                skills=[Skill.PERCEPTION.value],
                tags_required=["seek"],
                bonus_effects=[
                    BonusEffect(
                        type=BonusType.CIRCUMSTANCE,
                        value=2,
                        tag=Skill.PERCEPTION.value,
                        source="status:keen_eyes",
                        label="keen eyes +2",
                    )
                ],
                prompt_notes=["Keen Eyes: +2 circumstance do Seek (Perception)."],
            )
        ],
    )


KEEN_EYES_STATUS = KeenEyesStatus()

__all__ = ["KeenEyesStatus", "KEEN_EYES_STATUS", "KEEN_EYES_DESCRIPTION"]

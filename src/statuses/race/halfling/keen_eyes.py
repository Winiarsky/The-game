from __future__ import annotations

from bonuses import BonusEffect, BonusType
from skills import Skill
from statuses.base import Status
from statuses.check_effects import CheckEffect

KEEN_EYES_DESCRIPTION = (
    "Masz +2 circumstance do Seek, gdy próbujesz znaleźć hidden lub undetected "
    "creatures w obrębie 30 stóp.\n"
    "Przy ataku na concealed target DC flat check spada z 5 do 3.\n"
    "Przy ataku na hidden target DC flat check spada z 11 do 9."
)


def KeenEyesStatus() -> Status:
    """Cecha: Keen Eyes."""
    return Status(
        id="keen_eyes",
        label="Keen Eyes",
        data={
            "ui_description": KEEN_EYES_DESCRIPTION,
            "seek_hidden_undetected_bonus_feet": 30,
            "concealed_flat_check_dc_override": 3,
            "hidden_flat_check_dc_override": 9,
        },
        check_effects=[
            CheckEffect(
                applies_to="source",
                skills=[Skill.PERCEPTION.value],
                tags_required=["seek", "undetected", "within_30_feet"],
                bonus_effects=[
                    BonusEffect(
                        type=BonusType.CIRCUMSTANCE,
                        value=2,
                        tag=Skill.PERCEPTION.value,
                        source="status:keen_eyes",
                        label="keen eyes +2",
                    )
                ],
                prompt_notes=["Keen Eyes: +2 do Seek vs hidden/undetected w 30 stóp."],
            )
        ],
    )


KEEN_EYES_STATUS = KeenEyesStatus()

__all__ = ["KeenEyesStatus", "KEEN_EYES_STATUS", "KEEN_EYES_DESCRIPTION"]
